import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.contracts import AgentContextRequest, AgentEvidence
from app.agent.gateway import AgentGateway
from app.config import settings
from app.database import session_factory
from app.logging import configure_logging
from app.models import (
    AgentAssessment,
    AgentRun,
    ContextPack,
    EvidenceItem,
    KnowledgeFactKind,
    KnowledgeSource,
    Mission,
    MissionStatus,
    MissionStep,
    OutboxJob,
)
from app.services.context import collect_context
from app.services.execution import execute_mission
from app.services.knowledge import build_mission_context, knowledge_source_for, record_fact
from app.services.missions import record_mission_event, transition_mission
from app.services.mission_runtime import recover_expired_missions

configure_logging()
logger = structlog.get_logger()


async def _heartbeat(ctx: dict[str, Any]) -> None:
    redis = ctx["redis"]
    interval = max(3, settings.worker_heartbeat_ttl_seconds // 3)
    while True:
        await redis.set(
            settings.worker_heartbeat_key,
            "up",
            ex=settings.worker_heartbeat_ttl_seconds,
        )
        await asyncio.sleep(interval)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["session_factory"] = session_factory
    ctx["heartbeat_task"] = asyncio.create_task(_heartbeat(ctx))
    # K4.1: crash recovery at worker startup. Missions whose lease expired
    # while a worker was down are requeued; the claiming worker resumes
    # from the persisted safe point without repeating verified work.
    recovered: list[uuid.UUID] = []
    async with session_factory() as session:
        recovered = await recover_expired_missions(session)
        await session.commit()
    for mission_id in recovered:
        await ctx["redis"].enqueue_job("execute_mission", str(mission_id))
    logger.info("worker_started", recovered_missions=len(recovered))


async def shutdown(ctx: dict[str, Any]) -> None:
    task: asyncio.Task[None] = ctx["heartbeat_task"]
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await ctx["redis"].delete(settings.worker_heartbeat_key)
    logger.info("worker_stopped")


async def phase_one_noop(_: dict[str, Any]) -> str:
    """Queue smoke-test job; mission jobs are added in the mission phase."""
    return "ok"


async def dispatch_outbox(ctx: dict[str, Any]) -> int:
    """Reliably transfer committed PostgreSQL job intents to ARQ."""
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    redis: ArqRedis = ctx["redis"]
    dispatched = 0
    async with factory() as session:
        jobs = (
            await session.execute(
                select(OutboxJob)
                .where(OutboxJob.status == "pending")
                .order_by(OutboxJob.created_at)
                .limit(50)
                .with_for_update(skip_locked=True)
            )
        ).scalars()
        for job in jobs:
            try:
                await redis.enqueue_job(
                    job.job_type,
                    str(job.mission_id),
                    _job_id=f"outbox:{job.id}",
                )
                job.status = "dispatched"
                job.dispatched_at = datetime.now(UTC)
                dispatched += 1
            except Exception as exc:
                job.attempts += 1
                job.last_error = str(exc)[:1000]
        await session.commit()
    return dispatched


async def prepare_mission(ctx: dict[str, Any], mission_id: str) -> str:
    """Collect evidence and persist a validated Agent assessment without executing actions."""
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    async with factory() as session:
        mission = (
            await session.execute(
                select(Mission).where(Mission.id == uuid.UUID(mission_id)).with_for_update()
            )
        ).scalar_one_or_none()
        if mission is None:
            return "missing"
        if mission.status not in {MissionStatus.QUEUED, MissionStatus.PLANNING}:
            return str(mission.status.value)
        if mission.status == MissionStatus.QUEUED:
            transition_mission(
                session,
                mission,
                MissionStatus.PLANNING,
                "Worker accepted mission for context collection",
                None,
            )
            mission.progress_current = 1
            session.add(
                MissionStep(
                    workspace_id=mission.workspace_id,
                    mission_id=mission.id,
                    sequence=1,
                    name="Mission accepted",
                    status="completed",
                    detail="Validated and handed to the durable worker",
                )
            )
            record_mission_event(
                session,
                mission,
                "mission.planning_started",
                "Mission planning started",
                "The worker accepted the mission",
                None,
            )
        mission.progress_total = 3
        await session.commit()

    collected = await collect_context(mission)
    async with factory() as session:
        current = (
            await session.execute(select(Mission).where(Mission.id == mission.id).with_for_update())
        ).scalar_one()
        if current.status != MissionStatus.PLANNING:
            return str(current.status.value)
        context_pack = ContextPack(
            workspace_id=current.workspace_id,
            mission_id=current.id,
            version=1,
            summary=collected.summary,
            content=collected.content,
            content_hash=collected.content_hash,
        )
        session.add(context_pack)
        await session.flush()
        session.add_all(
            [
                EvidenceItem(
                    workspace_id=current.workspace_id,
                    context_pack_id=context_pack.id,
                    key=item.key,
                    provider=item.provider,
                    external_id=item.external_id,
                    title=item.title,
                    url=item.url,
                    excerpt=item.excerpt,
                    data=item.data,
                )
                for item in collected.evidence
            ]
        )
        # K1.5: mirror collected evidence into the append-only knowledge base
        # and assemble the bounded context pack for the next agent call.
        for item in collected.evidence:
            await record_fact(
                session,
                current,
                kind=KnowledgeFactKind.SOURCE_FACT,
                source=knowledge_source_for(item.provider),
                source_ref=item.external_id,
                fact=f"{item.title}: {item.excerpt}",
                data={"key": item.key, "url": item.url},
            )
        knowledge_pack = await build_mission_context(session, current)
        transition_mission(
            session,
            current,
            MissionStatus.CONTEXT_COLLECTED,
            "Cross-tool context and evidence persisted",
            None,
        )
        current.progress_current = 2
        session.add(
            MissionStep(
                workspace_id=current.workspace_id,
                mission_id=current.id,
                sequence=2,
                name="Context collected",
                status="completed",
                detail=collected.summary,
            )
        )
        record_mission_event(
            session,
            current,
            "mission.context_collected",
            "Context Pack ready",
            collected.summary,
            None,
        )
        await session.commit()
        context_pack_id = context_pack.id

    request = AgentContextRequest(
        mission_id=mission.id,
        prompt=mission.prompt,
        project=mission.project_name,
        context_summary=collected.summary,
        knowledge_base=knowledge_pack,
        evidence=[
            AgentEvidence(
                key=item.key,
                provider=item.provider,
                external_id=item.external_id,
                title=item.title,
                url=item.url,
                excerpt=item.excerpt,
            )
            for item in collected.evidence
        ],
    )
    async with factory() as session:
        agent_run = AgentRun(
            workspace_id=mission.workspace_id,
            mission_id=mission.id,
            context_pack_id=context_pack_id,
            mode=settings.agent_mode,
            status="running",
            request_payload=request.model_dump(mode="json"),
            response_payload=None,
            error=None,
        )
        session.add(agent_run)
        await session.commit()
        agent_run_id = agent_run.id

    gateway = AgentGateway()
    try:
        result = await gateway.analyze(request)
    except RuntimeError as exc:
        async with factory() as session:
            failed_run = await session.get(AgentRun, agent_run_id)
            failed_mission = await session.get(Mission, mission.id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.error = str(exc)
                failed_run.completed_at = datetime.now(UTC)
            if (
                failed_mission is not None
                and failed_mission.status == MissionStatus.CONTEXT_COLLECTED
            ):
                transition_mission(
                    session,
                    failed_mission,
                    MissionStatus.BLOCKED,
                    "Agent service failed and fallback is disabled",
                    None,
                )
            await session.commit()
        return "blocked"
    finally:
        await gateway.close()

    response = result.response
    async with factory() as session:
        completed_run = await session.get(AgentRun, agent_run_id)
        completed_mission = await session.get(Mission, mission.id)
        if completed_run is None or completed_mission is None:
            return "missing"
        completed_run.mode = result.mode
        completed_run.status = "completed"
        completed_run.response_payload = response.model_dump(mode="json")
        completed_run.error = result.fallback_reason
        completed_run.completed_at = datetime.now(UTC)
        session.add(
            AgentAssessment(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                agent_run_id=completed_run.id,
                context_summary=response.context_summary,
                risk_level=response.risk.level,
                risk_factors=response.risk.factors,
                review_effort_minutes=response.effort.minutes,
                effort_rationale=response.effort.rationale,
                confidence=response.confidence,
                explanation=response.explanation,
                reviewer_candidates=[
                    item.model_dump(mode="json") for item in response.reviewer_candidates
                ],
                citations=response.citations,
                proposals=[item.model_dump(mode="json") for item in response.proposals],
            )
        )
        completed_mission.progress_current = 3
        completed_mission.result_summary = response.context_summary
        session.add(
            MissionStep(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                sequence=3,
                name="Agent assessment validated",
                status="completed",
                detail=f"{response.risk.level.title()} risk; {result.mode} mode",
            )
        )
        record_mission_event(
            session,
            completed_mission,
            "mission.agent_assessment_validated",
            "Agent assessment ready",
            "Validated evidence, risk, effort, reviewers, confidence, and proposals",
            None,
        )
        # K1.6: the agent's validated assessment is derived knowledge —
        # recorded as a DECISION fact, never as source truth.
        await record_fact(
            session,
            completed_mission,
            kind=KnowledgeFactKind.DECISION,
            source=KnowledgeSource.AGENT,
            source_ref=f"agent-run:{completed_run.id}",
            fact=response.explanation,
            data={
                "context_summary": response.context_summary,
                "risk_level": response.risk.level,
                "proposals": [
                    f"{item.provider.value}:{item.operation}" for item in response.proposals
                ],
            },
            agent_run_id=completed_run.id,
            confidence=response.confidence,
        )
        await session.commit()
    return "context_collected"


class WorkerSettings:
    functions = [phase_one_noop, prepare_mission, execute_mission]
    cron_jobs = [cron(dispatch_outbox, second=set(range(0, 60, 5)), run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    health_check_interval = 10
