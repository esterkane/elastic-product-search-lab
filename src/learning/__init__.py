"""Procedural-learning half of the memory loop: experiment store + tuner.

The experiment store *is* the memory here (there is no agent loop, so
episodic recall-before-acting is not applicable). The tuner proposes a new
strategy configuration, evaluates it against the existing search-quality gate,
and keeps it only if it beats that gate. Nothing here mutates the live strategy
configuration; a kept proposal is recorded/staged for an explicit promotion step.

All behaviour is inert unless ``MEMORY_ENABLED`` is truthy (default: off), so the
lab's existing evaluation and gate behaviour stays reproducible.
"""

from src.learning.config import (
    BASELINE_STRATEGY_CONFIGS,
    StrategyConfig,
    baseline_config,
    build_query,
)
from src.learning.experiments import (
    ExperimentRecord,
    ExperimentStore,
    FileExperimentStore,
    InMemoryExperimentStore,
)
from src.learning.tuner import (
    TuneDecision,
    memory_enabled,
    propose_configs,
    tune,
)

__all__ = [
    "BASELINE_STRATEGY_CONFIGS",
    "StrategyConfig",
    "baseline_config",
    "build_query",
    "ExperimentRecord",
    "ExperimentStore",
    "FileExperimentStore",
    "InMemoryExperimentStore",
    "TuneDecision",
    "memory_enabled",
    "propose_configs",
    "tune",
]
