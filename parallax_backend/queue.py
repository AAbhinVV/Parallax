from typing import cast

from redis.asyncio import Redis

from parallax_backend.config import settings


def create_redis() -> Redis:
    return cast(Redis, Redis.from_url(settings.redis_url, decode_responses=True))
