from __future__ import annotations
import json
import os
import uuid

import redis

from infra.pal.interfaces.queue import QueueProvider


class RedisQueueProvider(QueueProvider):
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)

    @classmethod
    def from_env(cls) -> "RedisQueueProvider":
        return cls(redis_url=os.environ["REDIS_URL"])

    def enqueue(self, queue_name: str, payload: dict) -> str:
        message_id = str(uuid.uuid4())
        body = json.dumps({"id": message_id, "payload": payload})
        self._redis.lpush(queue_name, body)
        return message_id

    def ping(self) -> bool:
        try:
            return self._redis.ping()
        except redis.RedisError:
            return False
