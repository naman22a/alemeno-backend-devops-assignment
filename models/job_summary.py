import uuid
from typing import Any, TYPE_CHECKING, Optional
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .job import Job


class JobSummary(SQLModel, table=True):
    __tablename__ = "job_summaries"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    job_id: uuid.UUID = Field(
        foreign_key="jobs.id",
        unique=True,
    )

    total_spend_inr: Decimal = Field(
        default=0,
        max_digits=12,
        decimal_places=2,
    )

    total_spend_usd: Decimal = Field(
        default=0,
        max_digits=12,
        decimal_places=2,
    )

    top_merchants: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
    )

    anomaly_count: int = Field(default=0)

    narrative: str | None = Field(default=None)

    risk_level: str | None = Field(
        default=None,
        max_length=50,
    )

    job: Optional["Job"] = Relationship(
        back_populates="summary"
    )
