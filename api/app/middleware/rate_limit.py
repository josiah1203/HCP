from __future__ import annotations
import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-org rate limiting with Redis fallback to in-memory counters."""

    _memory: dict[str, list[float]] = defaultdict(list)
    _lock = Lock()

    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit_per_minute or settings.rate_limit_per_minute
        self._redis = None
        if redis is not None:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    def _org_key(self, request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return None
        token = auth[7:]
        if token.startswith("hcp_"):
            return f"apikey:{token[:24]}"
        try:
            from app.auth.jwt import safe_decode

            claims = safe_decode(token)
            if claims:
                return f"org:{claims.get('org_id', 'unknown')}"
        except Exception:
            pass
        return None

    def _check_memory(self, key: str) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - 60
        with self._lock:
            hits = [t for t in self._memory[key] if t > window_start]
            if len(hits) >= self.limit:
                remaining = 0
                return False, remaining, self.limit
            hits.append(now)
            self._memory[key] = hits
            remaining = max(0, self.limit - len(hits))
        return True, remaining, self.limit

    def _check_redis(self, key: str) -> tuple[bool, int, int]:
        assert self._redis is not None
        bucket = f"hcp:ratelimit:{key}:{int(time.time()) // 60}"
        count = self._redis.incr(bucket)
        if count == 1:
            self._redis.expire(bucket, 120)
        remaining = max(0, self.limit - count)
        return count <= self.limit, remaining, self.limit

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)

        org_key = self._org_key(request)
        if org_key is None:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(self.limit)
            return response

        if self._redis is not None:
            allowed, remaining, limit = self._check_redis(org_key)
        else:
            allowed, remaining, limit = self._check_memory(org_key)

        if not allowed:
            request_id = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded for organization",
                        "request_id": request_id,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
