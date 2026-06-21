"""Experiment store: the procedural memory of the learning loop.

Each experiment records the config that was tried, the relevance metrics the
existing evaluation produced for it, and whether it passed the search-quality
gate. Storage reuses existing infra -- a committed JSON log under
``experiments/`` -- rather than introducing a new datastore. Access goes through
the ``ExperimentStore`` abstraction so tests can use an in-memory fake.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.learning.config import StrategyConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPERIMENTS_PATH = PROJECT_ROOT / "experiments" / "experiments.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ExperimentRecord:
    """One tried configuration and the result the evaluation produced for it."""

    id: str
    timestamp: str
    config: StrategyConfig
    # Headline relevance metrics from the existing evaluation, e.g.
    # {"precision_at_5": ..., "mrr_at_10": ..., "ndcg_at_10": ...}.
    metrics: dict[str, float]
    gate_passed: bool
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "config": self.config.to_dict(),
            "metrics": {k: float(v) for k, v in self.metrics.items()},
            "gate_passed": bool(self.gate_passed),
            "note": self.note,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRecord":
        return cls(
            id=str(data["id"]),
            timestamp=str(data["timestamp"]),
            config=StrategyConfig.from_dict(data["config"]),
            metrics={k: float(v) for k, v in dict(data.get("metrics", {})).items()},
            gate_passed=bool(data.get("gate_passed", False)),
            note=str(data.get("note", "")),
            extra=dict(data.get("extra", {})),
        )

    @classmethod
    def create(
        cls,
        config: StrategyConfig,
        metrics: dict[str, float],
        gate_passed: bool,
        note: str = "",
        extra: dict[str, Any] | None = None,
        timestamp: str | None = None,
        experiment_id: str | None = None,
    ) -> "ExperimentRecord":
        ts = timestamp or _utc_now_iso()
        return cls(
            id=experiment_id or _experiment_id(config, ts),
            timestamp=ts,
            config=config,
            metrics=dict(metrics),
            gate_passed=gate_passed,
            note=note,
            extra=dict(extra or {}),
        )


def _experiment_id(config: StrategyConfig, timestamp: str) -> str:
    """Deterministic id from the config identity and timestamp (no randomness)."""

    boosts = "_".join(f"{k}{v:g}" for k, v in sorted(config.field_boosts.items()))
    return f"{config.strategy}-{boosts}-{timestamp}".replace(":", "").replace(".", "")


class ExperimentStore(ABC):
    """Repository abstraction over persisted experiments."""

    @abstractmethod
    def append(self, record: ExperimentRecord) -> None:
        """Persist one experiment record."""

    @abstractmethod
    def all(self) -> list[ExperimentRecord]:
        """Return every persisted record, oldest first."""

    def best(self, metric: str) -> ExperimentRecord | None:
        """Return the gate-passing record with the highest ``metric`` (None if none)."""

        passing = [r for r in self.all() if r.gate_passed and metric in r.metrics]
        if not passing:
            return None
        return max(passing, key=lambda r: r.metrics[metric])


class InMemoryExperimentStore(ExperimentStore):
    """Fake store for tests; holds records in a list."""

    def __init__(self, records: list[ExperimentRecord] | None = None) -> None:
        self._records: list[ExperimentRecord] = list(records or [])

    def append(self, record: ExperimentRecord) -> None:
        self._records.append(record)

    def all(self) -> list[ExperimentRecord]:
        return list(self._records)


class FileExperimentStore(ExperimentStore):
    """JSON-lines store committed under ``experiments/``.

    One record per line keeps appends atomic-enough for a single-writer lab and
    makes the memory diffable in git. No new datastore is introduced.
    """

    def __init__(self, path: Path | str = DEFAULT_EXPERIMENTS_PATH) -> None:
        self.path = Path(path)

    def append(self, record: ExperimentRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def all(self) -> list[ExperimentRecord]:
        if not self.path.exists():
            return []
        records: list[ExperimentRecord] = []
        with self.path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if line.strip():
                    records.append(ExperimentRecord.from_dict(json.loads(line)))
        return records
