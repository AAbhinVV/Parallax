from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "local"
    app_name: str = "parallax-api"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql+asyncpg://parallax:parallax@localhost:5432/parallax"
    redis_url: str = "redis://localhost:6379/0"
    worker_heartbeat_key: str = "parallax:worker:heartbeat"
    worker_heartbeat_ttl_seconds: int = Field(default=30, ge=10, le=300)

    jwt_secret: SecretStr = SecretStr("change-this-local-secret-before-sharing-123456")
    jwt_access_token_minutes: int = Field(default=15, ge=1, le=120)
    jwt_refresh_token_days: int = Field(default=7, ge=1, le=90)

    integration_mode: Literal["mock", "real"] = "mock"
    integration_timeout_seconds: float = Field(default=10.0, ge=1, le=60)
    github_token: SecretStr = SecretStr("")
    github_default_repo: str = ""
    slack_bot_token: SecretStr = SecretStr("")
    slack_default_channel: str = "#engineering"
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: SecretStr = SecretStr("")
    jira_default_project: str = ""
    notion_token: SecretStr = SecretStr("")
    notion_parent_page_id: str = ""

    agent_service_url: str = "http://localhost:8100"
    agent_service_api_key: SecretStr = SecretStr("")
    agent_mode: Literal["fallback", "service"] = "fallback"
    agent_timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    agent_fallback_enabled: bool = True

    execution_max_attempts: int = Field(default=3, ge=1, le=10)
    execution_lock_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    mission_sla_minutes: int = Field(default=60, ge=1, le=10_080)
    demo_failure_provider: Literal["", "github", "jira", "notion", "slack"] = ""

    demo_owner_email: str = ""
    demo_owner_password: SecretStr = SecretStr("")
    demo_owner_name: str = "Parallax Owner"
    demo_workspace_name: str = "Parallax Demo"
    demo_workspace_slug: str = "parallax-demo"

    @model_validator(mode="after")
    def protect_non_local_signing_key(self) -> "Settings":
        secret = self.jwt_secret.get_secret_value()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if self.app_env != "local" and secret.startswith("change-this-local-secret"):
            raise ValueError("JWT_SECRET must be changed outside the local environment")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
