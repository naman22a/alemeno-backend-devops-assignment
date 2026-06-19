import os
import pandas as pd
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlmodel import Session
from db.session import get_session
from services import job_repository
from workers.tasks import process_job
from schemas.job import (
    JobStatusResponse, 
    JobSummaryOut, 
    JobUploadResponse, 
    JobResultsResponse, 
    TransactionOut, 
    JobListResponse, 
    JobListItem
)
from models.job import Job, JobStatus
from config import settings

jobs_router = APIRouter()

@jobs_router.post("/upload", response_model=JobUploadResponse, status_code=202)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_session)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    os.makedirs(settings.upload_dir, exist_ok=True)
    job_uuid = uuid.uuid4()
    file_path = os.path.join(settings.upload_dir, f"{job_uuid}.csv")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        row_count_raw = len(pd.read_csv(file_path, dtype=str))
    except Exception as exc:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc

    job = Job(id=job_uuid, filename=file.filename, status=JobStatus.pending, row_count_raw=row_count_raw)
    db.add(job)
    db.commit()

    process_job.delay(str(job.id), file_path)

    return JobUploadResponse(job_id=str(job.id), status=job.status.value)

@jobs_router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_session)):
    job = job_repository.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
 
    summary_out = JobSummaryOut.model_validate(job.summary) if job.summary else None
 
    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status.value,
        filename=job.filename,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        summary=summary_out,
    )


@jobs_router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_session)):
    job = job_repository.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=409, detail=f"Job is '{job.status.value}', not completed yet")

    transactions = job_repository.get_transactions_for_job(db, job_id)
    transaction_out = [TransactionOut.model_validate(t) for t in transactions]
    anomalies_out = [t for t in transaction_out if t.is_anomaly]
    breakdown = job_repository.get_category_breakdown(db, job_id)
    summary_out = JobSummaryOut.model_validate(job.summary) if job.summary else None

    return JobResultsResponse(
        job_id=str(job.id),
        status=job.status.value,
        transactions=transaction_out,
        anomalies=anomalies_out,
        category_breakdown=breakdown,
        summary=summary_out,
    )

@jobs_router.get("/", response_model=JobListResponse)
def list_jobs(status: str | None = Query(default=None), db: Session = Depends(get_session)):
    jobs = job_repository.list_jobs(db, status=status)
    items = [
        JobListItem(
            job_id=str(j.id),
            status=j.status.value,
            filename=j.filename,
            row_count_raw=j.row_count_raw,
            created_at=j.created_at,
        )
        for j in jobs
    ]
    return JobListResponse(jobs=items)

