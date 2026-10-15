from __future__ import annotations

import pandas as pd


def wait_summary(df: pd.DataFrame) -> pd.Series:
    """Compute basic wait-time summary statistics."""
    if "Total_Waiting_Time_Valid" not in df.columns:
        raise KeyError("Total_Waiting_Time_Valid is required")
    series = df["Total_Waiting_Time_Valid"].dropna()
    return series.describe()
