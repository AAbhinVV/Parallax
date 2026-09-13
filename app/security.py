import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
ALGORITHM = "HS256"


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: uuid.UUID


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: uuid.UUID, workspace_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[str, int]:
    lifetime = timedelta(minutes=settings.jwt_access_token_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "wid": str(workspace_id),
        "sid": str(session_id),
        "type": "access",
        "iat": now,
        "exp": now + lifetime,
    }
    encoded = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)
    return encoded, int(lifetime.total_seconds())


def decode_access_token(token: str) -> AccessClaims:
    payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    return AccessClaims(
        user_id=uuid.UUID(payload["sub"]),
        workspace_id=uuid.UUID(payload["wid"]),
        session_id=uuid.UUID(payload["sid"]),
    )


def refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_days)
