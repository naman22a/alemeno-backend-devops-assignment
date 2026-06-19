import uuid
from datetime import datetime

from sqlmodel import Session, select
from sqlalchemy import func, update

from models.job import Job, JobStatus
from models.job_summary import JobSummary
from models.transaction import Transaction


def create_job(db: Session, filename: str, row_count_raw: int) -> Job:
    job = Job(
        filename=filename,
        status=JobStatus.pending,
        row_count_raw=row_count_raw,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def get_job(db: Session, job_id: str) -> Job | None:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return None

    return db.get(Job, job_uuid)


def list_jobs(db: Session, status: str | None = None) -> list[Job]:
    statement = select(Job)

    if status:
        statement = statement.where(Job.status == status)

    statement = statement.order_by(Job.created_at.desc())

    return list(db.exec(statement).all())


def mark_job_processing(db: Session, job_id: str) -> None:
    statement = (
        update(Job)
        .where(Job.id == uuid.UUID(job_id))
        .values(status=JobStatus.processing)
    )

    db.exec(statement)
    db.commit()


def mark_job_completed(
    db: Session,
    job_id: str,
    row_count_clean: int,
) -> None:
    statement = (
        update(Job)
        .where(Job.id == uuid.UUID(job_id))
        .values(
            status=JobStatus.completed,
            row_count_clean=row_count_clean,
            completed_at=datetime.utcnow(),
        )
    )

    db.exec(statement)
    db.commit()


def mark_job_failed(
    db: Session,
    job_id: str,
    error_message: str,
) -> None:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return

    statement = (
        update(Job)
        .where(Job.id == job_uuid)
        .values(
            status=JobStatus.failed,
            error_message=error_message[:2000],
            completed_at=datetime.utcnow(),
        )
    )

    db.exec(statement)
    db.commit()


def bulk_insert_transactions(
    db: Session,
    job_id: str,
    rows: list[dict],
) -> None:
    job_uuid = uuid.UUID(job_id)

    transactions = [
        Transaction(
            job_id=job_uuid,
            **row,
        )
        for row in rows
    ]

    db.add_all(transactions)
    db.commit()


def get_transactions_for_job(
    db: Session,
    job_id: str,
) -> list[Transaction]:
    statement = (
        select(Transaction)
        .where(Transaction.job_id == uuid.UUID(job_id))
        .order_by(Transaction.transaction_date)
    )

    return list(db.exec(statement).all())


def get_category_breakdown(
    db: Session,
    job_id: str,
) -> list[dict]:
    statement = (
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.job_id == uuid.UUID(job_id))
        .group_by(Transaction.category)
    )

    rows = db.exec(statement).all()

    return [
        {
            "category": row.category or "Uncategorised",
            "total_amount": float(row.total_amount or 0),
            "count": row.count,
        }
        for row in rows
    ]


def upsert_job_summary(
    db: Session,
    job_id: str,
    summary_data: dict,
) -> JobSummary:
    job_uuid = uuid.UUID(job_id)

    statement = select(JobSummary).where(
        JobSummary.job_id == job_uuid
    )

    summary = db.exec(statement).first()

    if summary is None:
        summary = JobSummary(
            job_id=job_uuid,
            **summary_data,
        )
        db.add(summary)
    else:
        for key, value in summary_data.items():
            setattr(summary, key, value)

    db.commit()
    db.refresh(summary)

    return summary
