"""Step (b) of the pipeline: anomaly detection.

Two independent checks, each appends to the same reasons list so a
transaction can be flagged for more than one cause without losing
either signal.
"""

import pandas as pd


def detect_anomalies(df: pd.DataFrame, domestic_brands: list[str]) -> pd.DataFrame:
    df = df.copy()

    medians = df.groupby("account_id")["amount"].median()

    def reasons_for(row) -> list[str]:
        reasons = []

        median = medians.get(row["account_id"])
        amount = row["amount"]
        if median is not None and median > 0 and amount is not None and amount > 3 * median:
            reasons.append(f"amount {amount:g} exceeds 3x account median ({median:g})")

        merchant = (row["merchant"] or "").strip().lower()
        if row["currency"] == "USD" and merchant in domestic_brands:
            reasons.append(f"USD transaction on domestic-only merchant '{row['merchant']}'")

        return reasons

    reason_lists = df.apply(reasons_for, axis=1)
    df["is_anomaly"] = reason_lists.apply(bool)
    df["anomaly_reason"] = reason_lists.apply(lambda r: "; ".join(r) if r else None)

    return df