"""Create all Parallax tables in a SQLite database (fastest local demo).

Alembic migrations are PostgreSQL-only (gen_random_uuid, ALTER TYPE).
For a SQLite demo database, use this script instead of alembic upgrade head:

    DATABASE_URL=sqlite+aiosqlite:///./parallax.db python create_demo_db.py
"""

import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base


async def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "sqlite+aiosqlite:///./parallax.db"
    )
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
    print(f"Created all Parallax tables in {database_url}")


if __name__ == "__main__":
    asyncio.run(main())
