import time
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.queue import create_redis

router = APIRouter(tags=["system"])
started_at = time.monotonic()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    uptime_seconds: float


class ReadyDependencies(BaseModel):
    postgres: Literal["up", "down"]
    redis: Literal["up", "down"]
    worker: Literal["up", "down"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: ReadyDependencies


def health_payload() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        uptime_seconds=round(time.monotonic() - started_at, 3),
    )


@router.get("/health", response_model=HealthResponse, summary="API liveness")
async def health() -> HealthResponse:
    return health_payload()


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="API liveness (MVP compatibility path)",
)
async def api_health() -> HealthResponse:
    return health_payload()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
    summary="PostgreSQL, Redis, and worker readiness",
)
async def ready(response: Response) -> ReadyResponse:
    postgres_state: Literal["up", "down"] = "down"
    redis_state: Literal["up", "down"] = "down"
    worker_state: Literal["up", "down"] = "down"

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        postgres_state = "up"
    except Exception:
        pass

    redis = create_redis()
    try:
        await redis.ping()
        redis_state = "up"
        if await redis.exists(settings.worker_heartbeat_key):
            worker_state = "up"
    except Exception:
        pass
    finally:
        await redis.aclose()

    is_ready = postgres_state == redis_state == worker_state == "up"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        dependencies=ReadyDependencies(
            postgres=postgres_state,
            redis=redis_state,
            worker=worker_state,
        ),
    )
