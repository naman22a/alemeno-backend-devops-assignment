from sqlmodel import Session
import logging

from workers.celery_app import celery_app
from services.job_repository import mark_job_failed
from db.database import engine
from services.pipeline import run_pipeline_for_job

@celery_app.task(name="process_job")
def process_job(job_id: str, file_path: str):
    """
    Background task that processes uploaded CSV.
    """

    with Session(engine) as db:
        print(f"Processing job {job_id}")

        try:
            run_pipeline_for_job(db, job_id, file_path)
        except Exception as exc:
            logging.exception("Job %s failed", job_id)
            mark_job_failed(db, job_id, str(exc))
