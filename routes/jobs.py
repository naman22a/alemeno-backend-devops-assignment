import pandas as pd
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlmodel import Session
from services.job_repository import list_jobs
from db.session import get_session
from services.job_repository import create_job
from workers.tasks import process_job

jobs_router = APIRouter()

@jobs_router.get('/')
def list_all_jobs(status: str | None = None, db: Session = Depends(get_session)):
    return list_jobs(db, status=status)

@jobs_router.post('/upload')
async def upload_job(
    file: UploadFile = File(...), 
    db: Session = Depends(get_session),
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV file."
        )

    job = create_job(db, filename=file.filename, row_count_raw=len(df))

    process_job.delay(
        str(job.id),
        contents.decode("utf-8"),
    )

    return {
        "job_id": str(job.id),
        "status": "pending",
    }
