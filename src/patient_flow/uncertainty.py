from __future__ import annotations

import numpy as np
import pandas as pd

from patient_flow.analysis import LONG_WAIT_THRESHOLD_MINUTES


def bootstrap_wait_confidence_intervals(
    waits: pd.Series,
    *,
    n_bootstrap: int = 500,
    confidence_level: float = 0.95,
    random_seed: int = 42,
    max_sample_size: int = 5_000,
) -> dict[str, float | int]:
    """Estimate percentile-bootstrap confidence intervals for median, P90 and long-wait share.

    For large filtered cohorts, a reproducible random sample is drawn before bootstrapping to
    keep dashboard response times predictable. Intervals quantify sampling uncertainty within
    the synthetic cohort; they do not account for simulation assumptions or model misspecification.
    """
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    if max_sample_size < 2:
        raise ValueError("max_sample_size must be at least 2")

    values = pd.to_numeric(waits, errors="coerce").dropna().to_numpy(dtype=float)
    if values.size < 2:
        raise ValueError("At least two valid wait observations are required")
    if not np.isfinite(values).all():
        raise ValueError("Wait values must be finite")

    rng = np.random.default_rng(random_seed)
    if values.size > max_sample_size:
        values = rng.choice(values, size=max_sample_size, replace=False)

    sample_size = values.size
    draws = rng.choice(values, size=(n_bootstrap, sample_size), replace=True)
    median_draws = np.median(draws, axis=1)
    p90_draws = np.quantile(draws, 0.90, axis=1)
    long_wait_draws = np.mean(draws > LONG_WAIT_THRESHOLD_MINUTES, axis=1) * 100

    alpha = (1.0 - confidence_level) / 2.0

    def interval(distribution: np.ndarray) -> tuple[float, float]:
        return (
            float(np.quantile(distribution, alpha)),
            float(np.quantile(distribution, 1.0 - alpha)),
        )

    median_low, median_high = interval(median_draws)
    p90_low, p90_high = interval(p90_draws)
    long_low, long_high = interval(long_wait_draws)
    return {
        "observations_used": int(sample_size),
        "bootstrap_replicates": int(n_bootstrap),
        "confidence_level": float(confidence_level),
        "median_ci_lower": median_low,
        "median_ci_upper": median_high,
        "p90_ci_lower": p90_low,
        "p90_ci_upper": p90_high,
        "long_wait_pct_ci_lower": long_low,
        "long_wait_pct_ci_upper": long_high,
    }
