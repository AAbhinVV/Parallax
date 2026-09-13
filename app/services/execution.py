import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.config import settings
from app.integrations.contracts import AdapterError, ApprovedWriteContext, ExternalRecord
from app.integrations.registry import build_jira_adapter, build_notion_adapter, build_slack_adapter
from app.models import (
    ActionProposal,
    ApprovalBundle,
    ExecutionRecord,
    IntegrationProvider,
    KnowledgeFactKind,
    Mission,
    MissionStatus,
    VerificationRecord,
)
from app.services.completion import build_completion_proof
from app.services.knowledge import knowledge_source_for, record_fact
from app.services.missions import record_mission_event, transition_mission
from app.services.mission_runtime import (
    claim_mission,
    get_runnable_actions,
    mark_step_started,
    release_lease,
    renew_lease,
    sync_step_from_execution,
    upsert_action_step,
)


async def _execute(action: ActionProposal, approval: ApprovedWriteContext) -> ExternalRecord:
    if action.provider == IntegrationProvider.JIRA:
        jira_adapter = build_jira_adapter()
        try:
            fields = action.payload.get("fields", action.payload)
            if action.operation == "issue.create":
                return await jira_adapter.create_issue(fields, approval)
            return await jira_adapter.update_issue(str(action.payload["key"]), fields, approval)
        finally:
            await jira_adapter.close()
    if action.provider == IntegrationProvider.NOTION:
        notion_adapter = build_notion_adapter()
        try:
            return await notion_adapter.append_blocks(
                str(action.payload["page_id"]), list(action.payload["children"]), approval
            )
        finally:
            await notion_adapter.close()
    if action.provider == IntegrationProvider.SLACK:
        slack_adapter = build_slack_adapter()
        try:
            channel = str(action.payload.get("channel", settings.slack_default_channel))
            text = str(action.payload["text"])
            if action.operation == "message.update":
                return await slack_adapter.update_message(
                    channel, str(action.payload["timestamp"]), text, approval
                )
            return await slack_adapter.post_message(channel, text, approval)
        finally:
            await slack_adapter.close()
    raise ValueError("GitHub writes are not permitted")


async def _verify(action: ActionProposal, external: ExternalRecord) -> dict[str, Any]:
    if action.provider == IntegrationProvider.JIRA:
        jira_adapter = build_jira_adapter()
        try:
            record = await jira_adapter.get_issue(external.external_id)
            return {"external_id": record.external_id, "title": record.title}
        finally:
            await jira_adapter.close()
    if action.provider == IntegrationProvider.NOTION:
        notion_adapter = build_notion_adapter()
        try:
            record = await notion_adapter.get_page(external.external_id)
            return {"external_id": record.external_id, "title": record.title}
        finally:
            await notion_adapter.close()
    if action.provider == IntegrationProvider.SLACK:
        slack_adapter = build_slack_adapter()
        try:
            channel = str(action.payload.get("channel", settings.slack_default_channel))
            messages = await slack_adapter.channel_history(channel)
            if not any(str(item.get("ts")) == external.external_id for item in messages):
                raise AdapterError(IntegrationProvider.SLACK, "Slack message was not found")
            return {"external_id": external.external_id, "channel": channel}
        finally:
            await slack_adapter.close()
    raise ValueError("Unsupported verification provider")


async def execute_mission(ctx: dict[str, Any], mission_id: str) -> str:
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    redis = ctx["redis"]
    lock_key = f"parallax:mission:{mission_id}:execution"
    lock_token = str(uuid.uuid4())
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    acquired = await redis.set(
        lock_key, lock_token, nx=True, ex=settings.execution_lock_ttl_seconds
    )
    if not acquired:
        return "locked"
    try:
        # K4.1: claim the durable DB lease. If another worker holds a live
        # lease, do not execute; recovery will requeue this mission.
        async with factory() as session:
            claimed = await claim_mission(session, uuid.UUID(mission_id), worker_id)
            await session.commit()
        if not claimed:
            return "locked"
        async with factory() as session:
            mission = await session.get(Mission, uuid.UUID(mission_id))
            bundle = (
                await session.execute(
                    select(ApprovalBundle)
                    .options(selectinload(ApprovalBundle.actions))
                    .where(
                        ApprovalBundle.mission_id == uuid.UUID(mission_id),
                        ApprovalBundle.status == "approved",
                    )
                    .order_by(ApprovalBundle.version.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if mission is None or bundle is None:
                return "missing"
            approval = ApprovedWriteContext(
                approval_id=bundle.id,
                mission_id=mission.id,
                approved_at=bundle.decided_at or datetime.now(UTC),
            )
            # K4.1: the runtime decides which actions still need work —
            # verified actions are skipped, maxed-out failures wait for an
            # explicit retry, everything else runs.
            action_ids = [
                action.id for action in await get_runnable_actions(session, mission)
            ]

        for action_id in action_ids:
            async with factory() as session:
                # K4.1: renew the lease before each mutation so a slow
                # worker cannot lose ownership mid-step.
                renewed = await renew_lease(session, uuid.UUID(mission_id), worker_id)
                await session.commit()
                if not renewed:
                    return "lease_lost"
                action = await session.get(ActionProposal, action_id)
                if action is None:
                    continue
                execution = (
                    await session.execute(
                        select(ExecutionRecord).where(
                            ExecutionRecord.action_proposal_id == action.id
                        )
                    )
                ).scalar_one_or_none()
                if execution is not None and execution.status == "verified":
                    continue
                if execution is None:
                    execution = ExecutionRecord(
                        workspace_id=action.workspace_id,
                        mission_id=action.mission_id,
                        action_proposal_id=action.id,
                        idempotency_key=f"action:{action.id}",
                        status="pending",
                    )
                    session.add(execution)
                    await session.flush()
                execution.started_at = datetime.now(UTC)
                # K4.1: durable step state — the step row mirrors the
                # execution record for the timeline and crash recovery.
                step = await upsert_action_step(session, action)
                mark_step_started(step)
                last_error: str | None = None
                external: ExternalRecord | None = None
                for attempt in range(execution.attempts, settings.execution_max_attempts):
                    execution.attempts = attempt + 1
                    try:
                        external = await _execute(action, approval)
                        verification = await _verify(action, external)
                        execution.status = "verified"
                        execution.external_id = external.external_id
                        execution.result = external.model_dump(mode="json")
                        execution.last_error = None
                        execution.completed_at = datetime.now(UTC)
                        action.status = "verified"
                        session.add(
                            VerificationRecord(
                                workspace_id=action.workspace_id,
                                mission_id=action.mission_id,
                                execution_id=execution.id,
                                status="verified",
                                evidence=verification,
                                checked_at=datetime.now(UTC),
                            )
                        )
                        # K1.6: verified outcomes enter the knowledge base as
                        # VERIFIED source facts (read-after-write confirmation).
                        outcome_mission = await session.get(Mission, action.mission_id)
                        assert outcome_mission is not None
                        await record_fact(
                            session,
                            outcome_mission,
                            kind=KnowledgeFactKind.SOURCE_FACT,
                            source=knowledge_source_for(action.provider),
                            source_ref=external.external_id,
                            fact=(
                                f"{action.provider.value} {action.operation} completed and "
                                f"verified: {verification.get('title', external.external_id)}"
                            ),
                            data={
                                "execution_id": str(execution.id),
                                "action_id": str(action.id),
                                "verification": verification,
                            },
                            verified=True,
                        )
                        break
                    except (AdapterError, KeyError, ValueError) as exc:
                        last_error = str(exc)[:1000]
                        if isinstance(exc, AdapterError) and exc.retryable:
                            await asyncio.sleep(0)
                            continue
                        break
                if external is None or execution.status != "verified":
                    execution.status = "failed"
                    execution.last_error = last_error or "Execution failed"
                    execution.completed_at = datetime.now(UTC)
                    action.status = "failed"
                    # K1.6: failures are observed knowledge too — recorded so the
                    # agent sees them in the next context pack.
                    outcome_mission = await session.get(Mission, action.mission_id)
                    assert outcome_mission is not None
                    await record_fact(
                        session,
                        outcome_mission,
                        kind=KnowledgeFactKind.SOURCE_FACT,
                        source=knowledge_source_for(action.provider),
                        source_ref=f"action:{action.id}",
                        fact=(
                            f"{action.provider.value} {action.operation} execution failed: "
                            f"{execution.last_error}"
                        ),
                        data={"execution_id": str(execution.id), "action_id": str(action.id)},
                    )
                sync_step_from_execution(step, execution)
                await session.commit()

        async with factory() as session:
            mission = (
                await session.execute(
                    select(Mission).where(Mission.id == uuid.UUID(mission_id)).with_for_update()
                )
            ).scalar_one()
            statuses = list(
                await session.scalars(
                    select(ExecutionRecord.status).where(ExecutionRecord.mission_id == mission.id)
                )
            )
            verified = statuses.count("verified")
            failed = statuses.count("failed")
            if verified and not failed:
                target = MissionStatus.COMPLETED
            elif verified:
                target = MissionStatus.PARTIALLY_COMPLETE
            else:
                target = MissionStatus.FAILED
            if mission.status == MissionStatus.RUNNING:
                transition_mission(
                    session,
                    mission,
                    target,
                    f"Execution finished: {verified} verified, {failed} failed",
                    None,
                )
                mission.result_summary = f"{verified} action(s) verified; {failed} failed"
                if target is MissionStatus.COMPLETED:
                    # K3.2: the database now owns the completion proof, built
                    # from verified execution records.
                    await build_completion_proof(session, mission)
                record_mission_event(
                    session,
                    mission,
                    "execution.finished",
                    "Mission execution finished",
                    mission.result_summary,
                    None,
                )
            await session.commit()
            return str(target.value)
    finally:
        await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            lock_key,
            lock_token,
        )
        # K4.1: release the durable lease; recovery will requeue the
        # mission if this worker dies before reaching this point.
        try:
            async with factory() as session:
                await release_lease(session, uuid.UUID(mission_id), worker_id)
                await session.commit()
        except Exception:  # lease release must not mask the result
            pass
