import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .job import Job


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    txn_id: Optional[str] = Field(default=None, max_length=255)

    transaction_date: Optional[date] = Field(default=None)

    merchant: Optional[str] = Field(default=None, max_length=255)

    amount: Optional[float] = Field(default=None)

    currency: Optional[str] = Field(default=None, max_length=10)

    status: Optional[str] = Field(default=None, max_length=50)

    category: Optional[str] = Field(default=None, max_length=100)

    account_id: Optional[str] = Field(
        default=None,
        max_length=255,
        index=True,
    )

    notes: Optional[str] = Field(default=None)

    is_anomaly: bool = Field(
        default=False,
        index=True,
    )

    anomaly_reason: Optional[str] = Field(default=None)

    llm_category: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    llm_raw_response: Optional[str] = Field(default=None)

    llm_failed: bool = Field(default=False)

    job_id: uuid.UUID = Field(foreign_key="jobs.id")

    job: Optional["Job"] = Relationship(
        back_populates="transactions"
    )
