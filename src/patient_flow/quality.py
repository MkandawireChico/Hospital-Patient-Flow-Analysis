from __future__ import annotations

import pandas as pd


def quality_summary(df: pd.DataFrame) -> dict[str, int | float]:
    """Return a concise summary of key data-quality flags."""
    summary = {"rows": int(len(df))}
    for field in ["Department_Data_Error", "Impossible_Timestamp_Flag", "Negative_Wait_Flag", "LOS_Outlier_Flag"]:
        if field in df.columns:
            summary[field] = int(df[field].sum())
    return summary
