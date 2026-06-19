from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from sqlmodel import SQLModel, Session
from db.database import engine
from routes.jobs import jobs_router
from typing import Literal
import redis as redis_lib
from sqlalchemy import text
from config import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description="Upload a dirty transactions CSV, process it asynchronously, get back a structured report.",
)

@app.on_event("startup")
def on_startup():
    logging.log(logging.INFO, 'DB tables created')
    SQLModel.metadata.create_all(engine)

def _check_postgres() -> tuple[Literal["ok", "error"], str]:
    try:
        with Session(engine) as db:
            db.exec(text("SELECT 1"))
        return "ok", ""
    except Exception as exc:
        return "error", str(exc)


def _check_redis() -> tuple[Literal["ok", "error"], str]:
    try:
        client = redis_lib.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        client.ping()
        client.close()
        return "ok", ""
    except Exception as exc:
        return "error", str(exc)

@app.get("/health")
def health():
    pg_status, pg_error = _check_postgres()
    redis_status, redis_error = _check_redis()

    overall = "ok" if pg_status == "ok" and redis_status == "ok" else "degraded"
    http_status = 200 if overall == "ok" else 503

    body = {
        "status": overall,
        "checks": {
            "postgres": {"status": pg_status, **({"error": pg_error} if pg_error else {})},
            "redis": {"status": redis_status, **({"error": redis_error} if redis_error else {})},
        },
    }
    return JSONResponse(content=body, status_code=http_status)

app.include_router(jobs_router, prefix='/jobs')
