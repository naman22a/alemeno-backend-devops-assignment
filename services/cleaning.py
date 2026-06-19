"""Step (a) of the pipeline: data cleaning.

Every function here is a pure transformation on a pandas DataFrame -
no DB session, no HTTP calls. That's deliberate: it's what makes
cleaning.py possible without spinning up Postgres or a worker.
"""

import pandas as pd
from dateutil import parser as dateutil_parser

REQUIRED_COLUMNS = [
    "txn_id",
    "date",
    "merchant",
    "amount",
    "currency",
    "status",
    "category",
    "account_id",
    "notes",
]

KNOWN_DATE_FORMATS = ("%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d")


def _parse_date(value) -> pd.Timestamp | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in KNOWN_DATE_FORMATS:
        try:
            return pd.Timestamp(pd.to_datetime(text, format=fmt))
        except (ValueError, TypeError):
            continue

    try:
        return pd.Timestamp(dateutil_parser.parse(text, dayfirst=True))
    except (ValueError, TypeError, OverflowError):
        return None


def _clean_amount(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_text(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise raw CSV rows per assignment section 5(a).

    Returns a new DataFrame with:
      - date normalised to ISO 8601 (date objects)
      - amount as a float, currency symbols stripped
      - status upper-cased
      - currency upper-cased
      - category filled with 'Uncategorised' when missing, but the
        original "was this missing" fact is preserved in
        `needs_classification` so step (c) knows which rows to send
        to the LLM, rather than re-classifying a transaction that was
        already genuinely categorised as 'Uncategorised' by the source.
      - txn_id/merchant/account_id/notes stripped of whitespace,
        blank strings normalised to None
      - exact duplicate rows removed
    """
    df = df.copy()

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["date"] = df["date"].apply(_parse_date)
    df["date"] = df["date"].apply(lambda d: d.date() if d is not None else None)

    df["amount"] = df["amount"].apply(_clean_amount)

    df["currency"] = df["currency"].apply(_clean_text)
    df["currency"] = df["currency"].apply(lambda v: v.upper() if v else None)

    df["status"] = df["status"].apply(_clean_text)
    df["status"] = df["status"].apply(lambda v: v.upper() if v else None)

    df["merchant"] = df["merchant"].apply(_clean_text)
    df["account_id"] = df["account_id"].apply(_clean_text)
    df["notes"] = df["notes"].apply(_clean_text)
    df["txn_id"] = df["txn_id"].apply(_clean_text)

    raw_category = df["category"].apply(_clean_text)
    df["needs_classification"] = raw_category.isna()
    df["category"] = raw_category.apply(lambda v: v.title() if v else "Uncategorised")

    df = df.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first").reset_index(drop=True)

    return df