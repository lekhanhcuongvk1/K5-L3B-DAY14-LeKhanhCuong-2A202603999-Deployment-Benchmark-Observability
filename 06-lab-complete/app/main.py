"""Production agent with Redis policy state and graceful lifecycle."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from redis.exceptions import RedisError

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost, refund, MAX_OUTPUT_TOKENS
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                           "level": record.levelname, "event": record.getMessage(),
                           **getattr(record, "fields", {})}, ensure_ascii=False)


logger = logging.getLogger("production_agent")
logger.setLevel(settings.log_level)
logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = True
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    # Uvicorn handles SIGTERM and drains requests before lifespan cleanup.
    # Never replace the server's signal handler.
    app.state.ready = False
    r.close()
    logger.info("shutdown_complete")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("question must contain text")
        return value


@app.middleware("http")
async def observe(request: Request, call_next):
    started = time.monotonic()
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request", extra={"fields": {
        "request_id": request_id, "method": request.method,
        "path": request.url.path, "status": response.status_code,
        "ms": round((time.monotonic() - started) * 1000, 2),
    }})
    return response


@app.exception_handler(RedisError)
async def redis_error(request: Request, exc: RedisError):
    logger.warning("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "State service unavailable"},
                        headers={"Retry-After": "1"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not getattr(app.state, "ready", False) or not redis_healthy():
        raise HTTPException(503, "Agent not ready")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    input_tokens = len(body.question.split()) * 2
    reservation = check_budget(input_tokens)
    try:
        answer = llm_ask(body.question)
        # Bound usage to the reserved maximum like provider max_tokens.
        answer = " ".join(answer.split()[:MAX_OUTPUT_TOKENS // 2])
    except Exception:
        refund(reservation)
        logger.error("llm_failed")
        raise HTTPException(502, "LLM service unavailable") from None
    output_tokens = len(answer.split()) * 2
    cost = record_cost(input_tokens, output_tokens, reservation)
    logger.info("llm_complete", extra={"fields": {
        "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost,
    }})
    return {"question": body.question, "answer": answer,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost}}
