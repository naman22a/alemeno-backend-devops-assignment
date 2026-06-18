from fastapi import FastAPI
import logging
from sqlmodel import SQLModel
from db.database import engine
from routes.jobs import jobs_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description="Upload a dirty transactions CSV, process it asynchronously, get back a structured report.",
)

@app.on_event("startup")
def on_startup():
    logging.log(logging.INFO, 'DB tables created')
    SQLModel.metadata.create_all(engine)


@app.get("/health")
def check_health():
    return { "status": "healthy" }

app.include_router(jobs_router, prefix='/jobs')
