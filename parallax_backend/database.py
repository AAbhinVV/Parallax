from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from parallax_backend.config import settings
from parallax_backend.models import Base

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def close_database() -> None:
    await engine.dispose()


async def create_schema_for_tests() -> None:
    """Create imported metadata; production uses Alembic instead."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
