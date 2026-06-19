"""Step (c) of the pipeline: LLM classification for rows missing a category.

Batched by design (assignment explicitly forbids one call per row).
Chunked into groups of `settings.llm_classification_batch_size` so a
500-row CSV doesn't produce one enormous prompt - this is the kind of
thing that's invisible at 90 rows and obvious at 10,000.
"""

import json
import logging

import pandas as pd

from config import settings
from services.llm_client import LLMCallError, OllamaClient

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = [
    "Food",
    "Shopping",
    "Travel",
    "Transport",
    "Utilities",
    "Cash Withdrawal",
    "Entertainment",
    "Other",
]

PROMPT_TEMPLATE = """You are classifying financial transactions for a spending report.
Assign each transaction exactly one category from this fixed list:
{categories}

Respond with ONLY a JSON array, no other text, in this exact shape:
[{{"index": 0, "category": "Food"}}, {{"index": 1, "category": "Travel"}}]

Transactions:
{transactions}
"""


def _build_prompt(batch: list[dict]) -> str:
    lines = []
    for item in batch:
        lines.append(
            f'{{"index": {item["index"]}, "merchant": "{item["merchant"]}", '
            f'"amount": {item["amount"]}, "currency": "{item["currency"]}", '
            f'"notes": "{item["notes"] or ""}"}}'
        )
    return PROMPT_TEMPLATE.format(
        categories=", ".join(ALLOWED_CATEGORIES),
        transactions="\n".join(lines),
    )


def classify_uncategorized(df: pd.DataFrame, llm_client: OllamaClient | None = None) -> pd.DataFrame:
    df = df.copy()
    df["llm_category"] = None
    df["llm_raw_response"] = None
    df["llm_failed"] = False

    client = llm_client or OllamaClient()

    pending_idx = df.index[df["needs_classification"]].tolist()
    if not pending_idx:
        return df

    batch_size = settings.llm_classification_batch_size
    for start in range(0, len(pending_idx), batch_size):
        chunk_idx = pending_idx[start : start + batch_size]
        batch = [
            {
                "index": idx,
                "merchant": df.at[idx, "merchant"] or "Unknown",
                "amount": df.at[idx, "amount"] if df.at[idx, "amount"] is not None else 0,
                "currency": df.at[idx, "currency"] or "INR",
                "notes": df.at[idx, "notes"],
            }
            for idx in chunk_idx
        ]
        prompt = _build_prompt(batch)

        try:
            result = client.generate_json(prompt)
            assignments = result if isinstance(result, list) else result.get("results", [])
            by_index = {int(item["index"]): item["category"] for item in assignments}

            for idx in chunk_idx:
                category = by_index.get(idx)
                if category not in ALLOWED_CATEGORIES:
                    category = "Other"
                df.at[idx, "category"] = category
                df.at[idx, "llm_category"] = category
                df.at[idx, "llm_raw_response"] = json.dumps(assignments)
        except LLMCallError as exc:
            logger.error("Classification batch failed after retries: %s", exc)
            for idx in chunk_idx:
                df.at[idx, "llm_failed"] = True
                # category stays 'Uncategorised' - we do not fail the job (5e)

    return df
