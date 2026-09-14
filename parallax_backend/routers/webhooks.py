from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from parallax_backend.config import settings
from parallax_backend.database import get_session
from parallax_backend.services.event_router import route_event

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookPayload(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    external_id: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/{provider}",
    summary="Receive an external event and wake affected missions",
)
async def receive_webhook(
    provider: str,
    event: WebhookPayload,
    session: AsyncSession = Depends(get_session),
    webhook_secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
) -> dict[str, Any]:
    """External events (GitHub/Jira/Slack/Notion) wake affected missions.

    Open when no webhook secret is configured (local/demo); enforced when
    WEBHOOK_SECRET is set.
    """
    expected = settings.webhook_secret
    if expected and webhook_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    woken = await route_event(
        session,
        provider=provider,
        event_type=event.event_type,
        external_id=event.external_id,
        payload=event.payload,
    )
    await session.commit()
    return {
        "status": "routed",
        "woken_missions": [str(mission_id) for mission_id in woken],
        "woken_count": len(woken),
    }
