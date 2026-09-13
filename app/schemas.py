import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import IntegrationProvider, MissionStatus, WorkspaceRole


class ErrorResponse(BaseModel):
    detail: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    workspace_name: str = Field(min_length=2, max_length=120)
    workspace_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    workspace_id: uuid.UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    workspace_id: uuid.UUID


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    role: WorkspaceRole


class MeResponse(BaseModel):
    user: UserRead
    current_workspace: WorkspaceRead
    workspaces: list[WorkspaceRead]


class WorkspaceSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: WorkspaceRole


class MemberRead(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    display_name: str
    role: WorkspaceRole


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class MissionCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    project: str = Field(default="General", min_length=1, max_length=120)

    @field_validator("prompt", "project")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank")
        return stripped


class MissionStepRead(BaseModel):
    id: uuid.UUID
    sequence: int
    name: str
    status: str
    detail: str
    created_at: datetime


class MissionRead(BaseModel):
    id: uuid.UUID
    prompt: str
    project: str
    status: MissionStatus
    progress_current: int
    progress_total: int
    result_summary: str | None
    steps: list[MissionStepRead]
    created_at: datetime
    updated_at: datetime


class EvidenceRead(BaseModel):
    key: str
    provider: IntegrationProvider
    external_id: str
    title: str
    url: str | None
    excerpt: str
    created_at: datetime


class ContextPackRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    version: int
    summary: str
    content: dict[str, Any]
    content_hash: str
    evidence: list[EvidenceRead]
    created_at: datetime


class ReviewerCandidateRead(BaseModel):
    identity: str
    score: float
    reason: str
    citations: list[str]


class AgentProposalRead(BaseModel):
    provider: IntegrationProvider
    operation: str
    rationale: str
    payload: dict[str, Any]
    citations: list[str]


class AgentAssessmentRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    mode: Literal["service", "fallback"]
    context_summary: str
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_factors: list[str]
    review_effort_minutes: int
    effort_rationale: str
    confidence: float
    explanation: str
    reviewer_candidates: list[ReviewerCandidateRead]
    citations: list[str]
    proposals: list[AgentProposalRead]
    created_at: datetime


class ActionProposalInput(BaseModel):
    provider: IntegrationProvider
    operation: str = Field(min_length=3, max_length=120)
    rationale: str = Field(min_length=3, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)
    citations: list[str] = Field(min_length=1)


class ActionProposalRead(ActionProposalInput):
    id: uuid.UUID
    sequence: int
    status: str


class PolicyResultRead(BaseModel):
    allowed: bool
    approval_required: bool
    reasons: list[str]


class ApprovalBundleRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    version: int
    status: str
    policy: PolicyResultRead
    actions: list[ActionProposalRead]
    decided_by_user_id: uuid.UUID | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ApprovalEditRequest(BaseModel):
    actions: list[ActionProposalInput] = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=2000)


class VerificationRead(BaseModel):
    status: str
    evidence: dict[str, Any]
    checked_at: datetime


class ExecutionRead(BaseModel):
    id: uuid.UUID
    action_proposal_id: uuid.UUID
    provider: IntegrationProvider
    operation: str
    status: str
    attempts: int
    external_id: str | None
    result: dict[str, Any] | None
    last_error: str | None
    verification: VerificationRead | None
    created_at: datetime
    completed_at: datetime | None


class ActivityRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID | None
    icon: str
    title: str
    detail: str
    created_at: datetime


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    icon: str
    health_pct: int


class IntegrationStatusRead(BaseModel):
    name: Literal["GitHub", "Jira", "Notion", "Slack"]
    connected: bool
    detail: str


class IntegrationCapabilityRead(BaseModel):
    operation: str
    access: Literal["read", "write"]
    description: str


class IntegrationCapabilitiesRead(BaseModel):
    name: Literal["GitHub", "Jira", "Notion", "Slack"]
    mode: Literal["mock", "real"]
    capabilities: list[IntegrationCapabilityRead]


class DashboardStatsRead(BaseModel):
    active_tasks: int
    completed_this_week: int
    blocked: int
    awaiting_approval: int
    project_health_pct: int


class TimelineEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    from_status: MissionStatus | None = None
    to_status: MissionStatus | None = None
    title: str
    detail: str
    actor_user_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    created_at: datetime


class AuditEventRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    event_type: str
    correlation_id: uuid.UUID
    payload: dict[str, Any]
    created_at: datetime


class MissionSLARead(BaseModel):
    mission_id: uuid.UUID
    status: MissionStatus
    age_seconds: int
    target_seconds: int
    remaining_seconds: int
    breached: bool


class StatusCountRead(BaseModel):
    status: MissionStatus
    count: int


class ProviderExecutionRead(BaseModel):
    provider: IntegrationProvider
    verified: int
    failed: int


class AnalyticsOverviewRead(BaseModel):
    total_missions: int
    completion_rate_pct: float
    verification_rate_pct: float
    average_completion_seconds: float | None
    missions_by_status: list[StatusCountRead]
    executions_by_provider: list[ProviderExecutionRead]


class IntegrationHealthRead(BaseModel):
    name: Literal["GitHub", "Jira", "Notion", "Slack"]
    status: str
    mode: Literal["mock", "real"]
    last_checked_at: datetime | None
    detail: str
