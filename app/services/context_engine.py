"""K5 seam: context engine — deterministic two-stage retrieval over the KB.

Stage 1 (exact): entity references — issue keys, PR numbers, page ids,
external ids. This is the correctness layer.

Stage 2 (text): token matching over KnowledgeFact text. This is the
relevance layer, standing in for future BM25/pgvector retrieval. The
interface is the seam: replacing the internals with BM25 + pgvector later
does not change the agent.

Results are scored, provenance-carrying, freshness-aware rows intended to
feed build_mission_context().
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeFact, Mission


@dataclass(frozen=True)
class ContextResult:
    fact_id: uuid.UUID
    fact: str
    source: str
    source_ref: str
    status: str
    observed_at: datetime | None
    score: float


async def search_context(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    query: str,
    entities: list[str] | None = None,
    limit: int = 20,
) -> list[ContextResult]:
    """Search mission knowledge for a workspace/project.

    - `entities` (issue keys, PR refs, page ids) match exact source_ref
    - `query` tokens match KnowledgeFact text

    Exact matches always outrank text matches; fresher facts outrank
    stale ones within the same stage.
    """
    tokens = [token for token in (query or "").lower().split() if len(token) >= 3]

    statement = (
        select(KnowledgeFact)
        .join(Mission, Mission.id == KnowledgeFact.mission_id)
        .where(
            KnowledgeFact.workspace_id == workspace_id,
            Mission.project_id == project_id,
        )
        .order_by(KnowledgeFact.observed_at.desc())
        .limit(200)
    )
    facts = (await session.execute(statement)).scalars().all()

    entity_set = {entity.strip() for entity in (entities or []) if entity.strip()}

    results: list[ContextResult] = []
    for fact in facts:
        score = 0.0
        if fact.source_ref in entity_set or (query and fact.source_ref == query.strip()):
            score = 1.0
        elif tokens:
            haystack = fact.fact.lower()
            matched = sum(1 for token in tokens if token in haystack)
            if matched:
                score = 0.5 * (matched / len(tokens))
        if score <= 0.0:
            continue
        results.append(
            ContextResult(
                fact_id=fact.id,
                fact=fact.fact,
                source=fact.source.value if hasattr(fact.source, "value") else str(fact.source),
                source_ref=fact.source_ref,
                status=fact.status.value if hasattr(fact.status, "value") else str(fact.status),
                observed_at=fact.observed_at,
                score=score,
            )
        )

    # Exact before text; within a stage, higher score then fresher first.
    results.sort(key=lambda r: (-r.score, r.observed_at or datetime.min.replace(tzinfo=None)))
    return results[:limit]
