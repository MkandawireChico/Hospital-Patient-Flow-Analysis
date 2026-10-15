from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"


def load_default_config() -> dict[str, Any]:
    """Load the default configuration as a dictionary."""
    if not DEFAULT_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Default config not found at {DEFAULT_CONFIG_PATH}")

    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
