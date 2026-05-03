"""Fail fast when latest local search reports do not meet configured thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "relevance-gate.json"
DEFAULT_RELEVANCE_REPORT = PROJECT_ROOT / "reports" / "relevance-report.json"
DEFAULT_LATENCY_REPORT = PROJECT_ROOT / "reports" / "latency-report.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required report/config file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_strategy_summary(report: dict[str, Any], strategy: str) -> dict[str, Any]:
    for row in report.get("summary", []):
        if row.get("strategy") == strategy:
            return row
    raise ValueError(f"Strategy '{strategy}' was not found in report summary")


def evaluate_gate(config: dict[str, Any], relevance_report: dict[str, Any], latency_report: dict[str, Any]) -> list[str]:
    strategy = str(config.get("strategy", "enriched_profile"))
    thresholds = config.get("thresholds", {})
    relevance = find_strategy_summary(relevance_report, strategy)
    latency = find_strategy_summary(latency_report, strategy)

    failures: list[str] = []
    min_precision = float(thresholds.get("minimum_average_precision_at_5", 0.0))
    min_mrr = float(thresholds.get("minimum_average_mrr_at_10", 0.0))
    max_p95 = float(thresholds.get("maximum_p95_latency_ms", float("inf")))

    precision = float(relevance.get("precision_at_5", 0.0))
    mrr = float(relevance.get("mrr_at_10", 0.0))
    p95 = float(latency.get("p95", 0.0))

    if precision < min_precision:
        failures.append(f"Precision@5 failed for {strategy}: {precision:.3f} < {min_precision:.3f}")
    if mrr < min_mrr:
        failures.append(f"MRR@10 failed for {strategy}: {mrr:.3f} < {min_mrr:.3f}")
    if p95 > max_p95:
        failures.append(f"p95 latency failed for {strategy}: {p95:.2f}ms > {max_p95:.2f}ms")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check latest search relevance and latency reports against local thresholds.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--relevance-report", type=Path, default=DEFAULT_RELEVANCE_REPORT)
    parser.add_argument("--latency-report", type=Path, default=DEFAULT_LATENCY_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_json(args.config)
        relevance_report = load_json(args.relevance_report)
        latency_report = load_json(args.latency_report)
        failures = evaluate_gate(config, relevance_report, latency_report)
    except Exception as exc:  # noqa: BLE001 - local gate should explain setup failures.
        print(f"Search quality gate failed to run: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("Search quality gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    strategy = config.get("strategy", "enriched_profile")
    print(f"Search quality gate passed for strategy '{strategy}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
