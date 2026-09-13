import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parallax_backend.config import settings  # noqa: E402
from parallax_backend.database import session_factory  # noqa: E402
from parallax_backend.models import Workspace  # noqa: E402


async def reset(slug: str) -> None:
    async with session_factory() as session:
        result = await session.execute(delete(Workspace).where(Workspace.slug == slug))
        await session.commit()
    print(f"Removed {result.rowcount or 0} demo workspace(s) with slug {slug}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete one local demo workspace and its data")
    parser.add_argument("--workspace-slug", default=settings.demo_workspace_slug)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Refusing to reset without --confirm")
    asyncio.run(reset(str(args.workspace_slug)))


if __name__ == "__main__":
    main()
