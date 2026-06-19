"""Orchestrates assignment section 5 end to end. This is the only
module that knows the *order* of steps; each step itself stays
independently testable (see services/cleaning.py, anomaly.py, etc).
"""

import logging

import numpy as np
import pandas as pd

from config import settings
from services import job_repository
from services.anomaly import detect_anomalies
from services.classification import classify_uncategorized
from services.cleaning import clean_transactions
from services.llm_client import OllamaClient
from services.narrative import generate_narrative

logger = logging.getLogger(__name__)


def _compute_deterministic_stats(df: pd.DataFrame) -> dict:
    total_inr = df.loc[df["currency"] == "INR", "amount"].sum()
    total_usd = df.loc[df["currency"] == "USD", "amount"].sum()

    top_merchants = (
        df.groupby("merchant")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .reset_index()
        .rename(columns={"amount": "total_amount"})
        .to_dict(orient="records")
    )
    top_merchants = [
        {"merchant": m["merchant"], "total_amount": float(m["total_amount"])} for m in top_merchants
    ]

    return {
        "total_spend_inr": float(total_inr or 0),
        "total_spend_usd": float(total_usd or 0),
        "top_merchants": top_merchants,
        "anomaly_count": int(df["is_anomaly"].sum()),
        "total_count": int(len(df)),
    }


def _sanitize_row(row: dict) -> dict:
    """pandas/numpy scalar types (np.bool_, np.float64, NaN) don't play
    nicely with psycopg2 - convert everything to plain Python types
    before it reaches SQLAlchemy.
    """
    clean = {}
    for key, value in row.items():
        if value is None or (isinstance(value, float) and pd.isna(value)):
            clean[key] = None
        elif isinstance(value, np.bool_):
            clean[key] = bool(value)
        elif isinstance(value, np.integer):
            clean[key] = int(value)
        elif isinstance(value, np.floating):
            clean[key] = float(value)
        else:
            clean[key] = value
    return clean


def run_pipeline_for_job(db, job_id: str, file_path: str) -> None:
    job_repository.mark_job_processing(db, job_id)

    raw_df = pd.read_csv(file_path, dtype=str)
    row_count_raw = len(raw_df)

    cleaned = clean_transactions(raw_df)
    flagged = detect_anomalies(cleaned, settings.domestic_brand_list)

    llm_client = OllamaClient()
    classified = classify_uncategorized(flagged, llm_client)

    rows = classified.drop(columns=["needs_classification"]).to_dict(orient="records")
    rows = [_sanitize_row(row) for row in rows]
    job_repository.bulk_insert_transactions(db, job_id, rows)

    stats = _compute_deterministic_stats(classified)
    narrative_result = generate_narrative(stats, llm_client)

    job_repository.upsert_job_summary(
        db,
        job_id,
        {
            "total_spend_inr": stats["total_spend_inr"],
            "total_spend_usd": stats["total_spend_usd"],
            "top_merchants": stats["top_merchants"],
            "anomaly_count": stats["anomaly_count"],
            "narrative": narrative_result["narrative"],
            "risk_level": narrative_result["risk_level"],
        },
    )

    job_repository.mark_job_completed(db, job_id, row_count_clean=len(classified))
    logger.info("Job %s completed: %d raw rows -> %d clean rows", job_id, row_count_raw, len(classified))
