from __future__ import annotations

import pandas as pd


def boolean_flag_column(df: pd.DataFrame, column: str) -> pd.Series:
    """Return a safe boolean mask for flags stored as bools, numbers, or CSV strings."""
    if column not in df.columns:
        return pd.Series(False, index=df.index, dtype=bool)
    values = df[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return (
        values.astype("string")
        .str.strip()
        .str.casefold()
        .isin({"true", "1", "1.0", "yes", "y"})
        .fillna(False)
        .astype(bool)
    )
