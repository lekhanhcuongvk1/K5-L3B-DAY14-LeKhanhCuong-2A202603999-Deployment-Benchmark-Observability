"""Atomic Redis reservation prevents concurrent workers overspending."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

# Mock tariff: USD per 1K estimated tokens.
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006
MAX_OUTPUT_TOKENS = 512

RESERVE = """
for i, key in ipairs(KEYS) do
    local used = tonumber(redis.call('GET', key) or '0')
    if used + tonumber(ARGV[1]) > tonumber(ARGV[i + 1]) then return 0 end
end
for i, key in ipairs(KEYS) do
    redis.call('INCRBYFLOAT', key, ARGV[1])
    redis.call('EXPIREAT', key, ARGV[i + 3])
end
return 1
"""


@dataclass(frozen=True)
class Reservation:
    keys: tuple[str, str]
    amount: float


def token_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000


def check_budget(input_tokens: int = 0) -> Reservation:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    next_month = (now.replace(day=28) + timedelta(days=4)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    # Retain old buckets one extra day for in-flight reconciliation at midnight.
    keys = (f"cost:day:{now:%Y-%m-%d}", f"cost:month:{now:%Y-%m}")
    amount = token_cost(input_tokens, MAX_OUTPUT_TOKENS)
    accepted = r.eval(RESERVE, 2, *keys, amount, settings.daily_budget_usd,
                      settings.monthly_budget_usd,
                      int(tomorrow.timestamp()) + 86400, int(next_month.timestamp()) + 86400)
    if not accepted:
        raise HTTPException(402, "LLM budget exhausted")
    return Reservation(keys, amount)


def record_cost(input_tokens: int, output_tokens: int, reservation: Reservation) -> float:
    cost = token_cost(input_tokens, output_tokens)
    with r.pipeline(transaction=True) as pipe:
        for key in reservation.keys:
            pipe.incrbyfloat(key, cost - reservation.amount)
        pipe.execute()
    return cost


def refund(reservation: Reservation) -> None:
    record_cost(0, 0, reservation)
