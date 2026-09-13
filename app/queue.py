from typing import cast

from redis.asyncio import Redis

from app.config import settings


def create_redis() -> Redis:
    return cast(Redis, Redis.from_url(settings.redis_url, decode_responses=True))
