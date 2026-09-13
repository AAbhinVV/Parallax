from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID, uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import RequestResponseEndpoint

from app.config import settings
from app.database import close_database
from app.logging import configure_logging
from app.metrics import HTTP_DURATION, HTTP_FAILURES, HTTP_REQUESTS
from app.routers.analytics import router as analytics_router
from app.routers.approvals import router as approvals_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.executions import router as executions_router
from app.routers.health import router as health_router
from app.routers.integrations import router as integrations_router
from app.routers.missions import router as missions_router
from app.routers.webhooks import router as webhooks_router
from app.routers.workspaces import router as workspaces_router

configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("api_started", environment=settings.app_env)
    yield
    await close_database()
    logger.info("api_stopped")


app = FastAPI(
    title="Parallax API",
    version="0.1.0",
    description=(
        "Backend API for manually submitted Parallax missions. External writes are proposed, "
        "approved, executed, verified, and audited by deterministic backend services."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    try:
        request.state.correlation_id = UUID(correlation_id)
    except ValueError:
        request.state.correlation_id = uuid4()
        correlation_id = str(request.state.correlation_id)
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        HTTP_FAILURES.labels(request.method, request.url.path).inc()
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )
        raise
    duration = perf_counter() - started
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Trace-ID"] = correlation_id
    HTTP_REQUESTS.labels(request.method, request.url.path, response.status_code).inc()
    HTTP_DURATION.labels(request.method, request.url.path).observe(duration)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
        correlation_id=correlation_id,
    )
    return response


app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(approvals_router)
app.include_router(executions_router)
app.include_router(missions_router)
app.include_router(dashboard_router)
app.include_router(integrations_router)
app.include_router(webhooks_router)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
