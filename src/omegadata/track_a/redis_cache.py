from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import redis

from omegadata.config import settings


class RedisCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def set_json(self, key: str, value: dict[str, Any], ttl: timedelta | None = None) -> None:
        self.client.set(key, json.dumps(value), ex=int(ttl.total_seconds()) if ttl else None)

    def get_json(self, key: str) -> dict[str, Any] | None:
        payload = self.client.get(key)
        if payload is None:
            return None
        decoded = json.loads(str(payload))
        return dict(decoded)
