"""Atomic sliding window shared by workers and retained across restarts."""
import hashlib
import uuid
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

SLIDING_WINDOW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.ceil(tonumber(oldest[2]) + 60 - now)
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 60)
return 0
"""


def check_rate_limit(key: str) -> None:
    digest = hashlib.sha256(key.encode()).hexdigest()
    retry_after = int(r.eval(SLIDING_WINDOW, 1, f"rate:{digest}",
                             settings.rate_limit_per_minute, uuid.uuid4().hex))
    if retry_after:
        raise HTTPException(429, "Rate limit exceeded",
                            headers={"Retry-After": str(max(1, retry_after))})
