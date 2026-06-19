"""Step (d) of the pipeline: the narrative summary.

Deliberate design choice: total spend by currency, top merchants, and
anomaly count are computed in plain Python/pandas - arithmetic the
LLM has no business doing. The LLM is only asked to turn those exact
numbers into a 2-3 sentence narrative and a risk_level verdict. This
keeps the one subjective part of the report (the narrative tone, the
risk call) LLM-generated, while every number in the report is exact
and reproducible.
"""

import logging

from services.llm_client import LLMCallError, OllamaClient

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a financial analyst writing a short internal note about a batch of transactions.

Stats:
- Total spend (INR): {total_inr}
- Total spend (USD): {total_usd}
- Top merchants by spend: {top_merchants}
- Anomalies detected: {anomaly_count} out of {total_count} transactions

Respond with ONLY this JSON shape, no other text:
{{"narrative": "2-3 sentence summary of the spending pattern", "risk_level": "low|medium|high"}}
"""


def generate_narrative(stats: dict, llm_client: OllamaClient | None = None) -> dict:
    client = llm_client or OllamaClient()

    prompt = PROMPT_TEMPLATE.format(
        total_inr=stats["total_spend_inr"],
        total_usd=stats["total_spend_usd"],
        top_merchants=stats["top_merchants"],
        anomaly_count=stats["anomaly_count"],
        total_count=stats["total_count"],
    )

    try:
        result = client.generate_json(prompt)
        narrative = result.get("narrative")
        risk_level = result.get("risk_level")
        if risk_level not in ("low", "medium", "high"):
            risk_level = "unknown"
        return {"narrative": narrative, "risk_level": risk_level}
    except LLMCallError as exc:
        logger.error("Narrative generation failed after retries: %s", exc)
        # Per 5(e): don't fail the job, just leave this part incomplete.
        return {"narrative": None, "risk_level": "unknown"}
