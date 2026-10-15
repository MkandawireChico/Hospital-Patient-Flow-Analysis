from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from patient_flow.config import PROJECT_ROOT

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "hospital_patient_flow_synthetic.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "hospital_patient_flow_clean.csv"


def ensure_data_files() -> tuple[Path, Path]:
    """Ensure the raw and processed data directories exist."""
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    return RAW_DATA_PATH, PROCESSED_DATA_PATH


def load_raw_data() -> pd.DataFrame:
    """Load the raw synthetic dataset."""
    ensure_data_files()
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")
    return pd.read_csv(RAW_DATA_PATH)


def load_processed_data() -> pd.DataFrame:
    """Load the processed and cleaned dataset."""
    ensure_data_files()
    if not PROCESSED_DATA_PATH.exists():
        raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_DATA_PATH}")
    return pd.read_csv(PROCESSED_DATA_PATH)


def save_processed_data(df: pd.DataFrame, path: Path | str | None = None) -> Path:
    """Persist a processed dataset to disk."""
    target = Path(path) if path is not None else PROCESSED_DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)
    return target


def summary_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Return headline wait metrics for a patient-flow dataset."""
    wait = df["Total_Waiting_Time_Valid"].dropna()
    return {
        "row_count": int(len(df)),
        "mean_wait_minutes": float(wait.mean()),
        "median_wait_minutes": float(wait.median()),
        "share_wait_over_60": float((wait > 60).mean()),
    }
