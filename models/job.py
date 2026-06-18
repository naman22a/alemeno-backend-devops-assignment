import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .transaction import Transaction
    from .job_summary import JobSummary

class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    filename: str

    status: JobStatus = Field(
        default=JobStatus.pending,
        index=True,
    )

    row_count_raw: int = Field(default=0)
    row_count_clean: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )

    completed_at: Optional[datetime] = Field(default=None)

    error_message: Optional[str] = Field(default=None)

    transactions: list["Transaction"] = Relationship(
        back_populates="job"
    )

    summary: Optional["JobSummary"] = Relationship(
        back_populates="job"
    )
