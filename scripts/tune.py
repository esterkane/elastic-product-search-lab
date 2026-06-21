"""Runner for the learning loop: load experiments, propose, evaluate, decide, persist.

Offline-capable: pass ``--offline`` to evaluate the proposed config against a
deterministic fake search backed by the checked-in judgments (no live ES). The
real path builds a live Elasticsearch client and runs the proposed query body.

Tuning is inert unless ``MEMORY_ENABLED`` is set (default off), so the lab's
existing eval/gate behaviour stays reproducible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.relevance_report import (  # noqa: E402
    QueryJudgment,
    load_product_search_judgments,
)
from src.learning.config import StrategyConfig, build_query  # noqa: E402
from src.learning.experiments import (  # noqa: E402
    DEFAULT_EXPERIMENTS_PATH,
    FileExperimentStore,
)
from src.learning.tuner import SearchFn, memory_enabled, tune  # noqa: E402
from src.search.hybrid_search import extract_ids  # noqa: E402

DEFAULT_JUDGMENTS_PATH = PROJECT_ROOT / "data" / "judgments" / "product_search_judgments.json"
DEFAULT_GATE_PATH = PROJECT_ROOT / "config" / "relevance-gate.json"


def make_offline_search_fn(judgments: list[QueryJudgment]) -> SearchFn:
    """A deterministic, offline search fn for run-without-ES dry runs.

    It does not interpret the query body; instead, for the query embedded in the
    body it returns the judged product ids ordered by descending grade. This makes
    the offline run reproduce the "ideal" ranking implied by the judgments -- a
    sanity baseline, not a real retrieval. Real tuning needs live ES (integration).
    """

    by_query: dict[str, list[str]] = {}
    for judgment in judgments:
        ranked = sorted(judgment.judgments.items(), key=lambda kv: (-kv[1], kv[0]))
        by_query[judgment.query] = [product_id for product_id, _ in ranked]

    def search_fn(body: dict[str, Any]) -> list[str]:
        query = str(body["query"]["multi_match"]["query"])
        return by_query.get(query, [])

    return search_fn


def make_live_search_fn(index_name: str) -> SearchFn:
    from scripts.create_index import build_client, ensure_reachable

    client = build_client()
    ensure_reachable(client)

    def search_fn(body: dict[str, Any]) -> list[str]:
        return extract_ids(client.search(index=index_name, **body))

    return search_fn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Propose, evaluate, and stage a tuned strategy config.")
    parser.add_argument("--strategy", default="enriched_profile")
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS_PATH)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE_PATH)
    parser.add_argument("--store", type=Path, default=DEFAULT_EXPERIMENTS_PATH)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", "products-v1"))
    parser.add_argument("--offline", action="store_true", help="Use the deterministic offline search fn (no live ES).")
    return parser.parse_args()


def _print_config(label: str, config: StrategyConfig | None) -> None:
    if config is None:
        print(f"{label}: (none)")
        return
    boosts = ", ".join(f"{k}^{v:g}" for k, v in sorted(config.field_boosts.items()))
    print(f"{label}: {config.strategy} [{boosts}]")


def main() -> int:
    args = parse_args()

    if not memory_enabled():
        print("MEMORY_ENABLED is off (default). Tuner is inert; no experiment proposed or persisted.")
        return 0

    judgments = load_product_search_judgments(args.judgments)
    gate_config = json.loads(args.gate.read_text(encoding="utf-8"))
    store = FileExperimentStore(args.store)

    if args.offline:
        search_fn = make_offline_search_fn(judgments)
        print("Running OFFLINE (deterministic judgment-backed search; not real retrieval).")
    else:
        search_fn = make_live_search_fn(args.index)
        print(f"Running against live Elasticsearch index '{args.index}'.")

    decision = tune(
        strategy=args.strategy,
        judgments=judgments,
        search_fn=search_fn,
        store=store,
        gate_config=gate_config,
        size=args.size,
    )

    print("\n=== Tuning decision ===")
    _print_config("Proposed", decision.proposed)
    print(f"Kept: {decision.kept}")
    print(f"Reason: {decision.reason}")
    if decision.proposed_metrics is not None and decision.best_metrics is not None:
        for metric in ("precision_at_5", "mrr_at_10", "ndcg_at_10"):
            best = decision.best_metrics.get(metric, 0.0)
            proposed = decision.proposed_metrics.get(metric, 0.0)
            print(f"  {metric}: best={best:.3f} proposed={proposed:.3f} delta={proposed - best:+.3f}")
    if decision.record is not None:
        print(f"Experiment persisted: id={decision.record.id} gate_passed={decision.record.gate_passed}")
    print(f"Store: {store.path}")
    print("\nNote: a kept proposal is STAGED in the experiment store. Promoting it to the")
    print("live strategy config is a separate, explicit step -- the tuner never mutates it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
