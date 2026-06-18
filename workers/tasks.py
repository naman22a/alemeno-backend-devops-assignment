import io
import pandas as pd

from workers.celery_app import celery_app
from services.job_repository import mark_job_processing, mark_job_completed, mark_job_failed
from sqlmodel import Session
from fastapi import Depends
from db.session import get_session
from db.database import engine

@celery_app.task(name="process_job")
def process_job(job_id: str, csv_content: str, db: Session = Depends(get_session)):
    """
    Background task that processes uploaded CSV.
    """

    with Session(engine) as db:
        print(f"Processing job {job_id}")

        try:
            df = pd.read_csv(io.StringIO(csv_content))

            mark_job_processing(db, job_id=job_id)

            # TODO:
            # - Run analytics
            # - Calculate metrics
            # - Detect anomalies
            # - Generate summary

            row_count = len(df)

            print(
                f"Job {job_id} completed successfully. "
                f"Rows processed: {row_count}"
            )

            mark_job_completed(db, job_id, row_count_clean=row_count)

            return {
                "job_id": job_id,
                "rows_processed": row_count,
                "status": "completed",
            }

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            mark_job_failed(db, job_id, str(e))

            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
            }
