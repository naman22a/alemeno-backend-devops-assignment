import io
import pandas as pd

from workers.celery_app import celery_app


@celery_app.task(name="process_job")
def process_job(job_id: str, csv_content: str):
    """
    Background task that processes uploaded CSV.
    """

    print(f"Processing job {job_id}")

    try:
        df = pd.read_csv(io.StringIO(csv_content))

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

        return {
            "job_id": job_id,
            "rows_processed": row_count,
            "status": "completed",
        }

    except Exception as e:
        print(f"Job {job_id} failed: {e}")

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }
