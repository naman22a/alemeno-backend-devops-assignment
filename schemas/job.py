from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobUploadResponse(BaseModel):
    job_id: str
    status: str


class JobSummaryOut(BaseModel):
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: list[dict]
    anomaly_count: int
    narrative: Optional[str] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary: Optional[JobSummaryOut] = None


class TransactionOut(BaseModel):
    txn_id: Optional[str] = None
    date: date | None = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryBreakdownItem(BaseModel):
    category: str
    total_amount: float
    count: int


class JobResultsResponse(BaseModel):
    job_id: str
    status: str
    transactions: list[TransactionOut]
    anomalies: list[TransactionOut]
    category_breakdown: list[CategoryBreakdownItem]
    summary: Optional[JobSummaryOut] = None


class JobListItem(BaseModel):
    job_id: str
    status: str
    filename: str
    row_count_raw: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
