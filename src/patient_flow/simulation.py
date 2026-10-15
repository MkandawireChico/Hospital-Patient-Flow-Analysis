from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """Minimal simulation configuration placeholder for the package API."""
    random_seed: int = 42
    name: str = "default"


def build_default_simulation() -> SimulationConfig:
    """Return the default simulation configuration used in the repository."""
    return SimulationConfig(random_seed=42, name="Chilungamo District Hospital")
