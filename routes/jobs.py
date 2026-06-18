from fastapi import APIRouter
from fastapi import Depends
from sqlmodel import Session
from services.job_repository import list_jobs
from db.session import get_session

jobs_router = APIRouter()

@jobs_router.get('/')
def list_all_jobs(status: str | None = None, db: Session = Depends(get_session)):
    return list_jobs(db, status=status)
