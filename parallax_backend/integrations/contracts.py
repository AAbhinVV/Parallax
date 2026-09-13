import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from parallax_backend.models import IntegrationProvider


class AdapterError(RuntimeError):
    def __init__(self, provider: IntegrationProvider, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class AdapterHealth(BaseModel):
    provider: IntegrationProvider
    connected: bool
    detail: str
    checked_at: datetime


class IntegrationCapability(BaseModel):
    operation: str
    access: Literal["read", "write"]
    description: str


class ExternalRecord(BaseModel):
    provider: IntegrationProvider
    external_id: str
    url: str | None = None
    title: str
    data: dict[str, Any] = Field(default_factory=dict)


class ApprovedWriteContext(BaseModel):
    """Proof passed only after the backend has validated a stored approval."""

    approval_id: uuid.UUID
    mission_id: uuid.UUID
    approved_at: datetime


def require_approval(context: ApprovedWriteContext | None) -> ApprovedWriteContext:
    if context is None:
        raise PermissionError("An approved backend action is required for integration writes")
    return context
