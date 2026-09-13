import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parallax_backend.config import settings  # noqa: E402
from parallax_backend.database import session_factory  # noqa: E402
from parallax_backend.models import (  # noqa: E402
    Integration,
    IntegrationProvider,
    IntegrationStatus,
    Project,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from parallax_backend.security import hash_password  # noqa: E402


async def seed() -> None:
    email = settings.demo_owner_email.strip().lower()
    password = settings.demo_owner_password.get_secret_value()
    if not email or len(password) < 12:
        raise SystemExit("Set DEMO_OWNER_EMAIL and a 12+ character DEMO_OWNER_PASSWORD first")

    async with session_factory() as session:
        if await session.scalar(select(User.id).where(User.email == email)):
            print("Demo owner already exists")
            return
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=settings.demo_owner_name,
        )
        workspace = Workspace(name=settings.demo_workspace_name, slug=settings.demo_workspace_slug)
        session.add_all([user, workspace])
        await session.flush()
        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )
        session.add_all(
            [
                Integration(
                    workspace_id=workspace.id,
                    provider=provider,
                    status=IntegrationStatus.DISCONNECTED,
                    display_name=provider.value.title(),
                    configuration={},
                )
                for provider in IntegrationProvider
            ]
        )
        session.add_all(
            [
                Project(
                    workspace_id=workspace.id,
                    name=name,
                    icon=icon,
                    health_pct=health,
                )
                for name, icon, health in (
                    ("General", "folder", 80),
                    ("Payments", "wallet", 78),
                    ("Platform", "layers", 62),
                    ("Core", "cpu", 91),
                    ("Mobile", "smartphone", 45),
                )
            ]
        )
        await session.commit()
        print(f"Seeded {email} in workspace {workspace.slug}")


if __name__ == "__main__":
    asyncio.run(seed())
