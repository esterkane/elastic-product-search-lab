"""Compare lexical and hybrid retrieval strategies with offline metrics."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.embeddings.embedder import get_embedder  # noqa: E402
from src.evaluation.judgments import load_judgments  # noqa: E402
from src.evaluation.metrics import ndcg_at_k, precision_at_k, reciprocal_rank  # noqa: E402
from src.search.hybrid_search import hybrid_rrf_search, lexical_search, timed_strategy  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS = PROJECT_ROOT / "data" / "sample" / "judgments.jsonl"
STRATEGIES = ("baseline_lexical", "boosted_lexical", "hybrid_rrf")


def score_ranking(ranking: list[str], judgments: dict[str, int], k: int) -> dict[str, float]:
    return {
        "precision_at_10": precision_at_k(ranking, judgments, k),
        "mrr": reciprocal_rank(ranking, judgments),
        "ndcg_at_10": ndcg_at_k(ranking, judgments, k),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate lexical and hybrid product search strategies.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    parser.add_argument("--provider", choices=["auto", "sentence-transformers", "hash"], default="auto")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        judgments_by_query = load_judgments(args.judgments)
        embedder = get_embedder(args.provider, args.model)
        rows: list[dict[str, Any]] = []
        for query, judgments in sorted(judgments_by_query.items()):
            results = [
                timed_strategy("baseline_lexical", query, lambda q=query: lexical_search(client, args.index, q, args.k, boosted=False)),
                timed_strategy("boosted_lexical", query, lambda q=query: lexical_search(client, args.index, q, args.k, boosted=True)),
                timed_strategy("hybrid_rrf", query, lambda q=query: hybrid_rrf_search(client, args.index, q, embedder, args.k)),
            ]
            for result in results:
                metrics = score_ranking(result.ranked_product_ids, judgments, args.k)
                row = {"query": query, "strategy": result.strategy, "latency_ms": result.latency_ms, **metrics}
                rows.append(row)
                print(
                    f"{query} [{result.strategy}]: Precision@10={metrics['precision_at_10']:.3f} "
                    f"MRR={metrics['mrr']:.3f} nDCG@10={metrics['ndcg_at_10']:.3f} "
                    f"latency_ms={result.latency_ms:.1f}"
                )
        print("aggregate:")
        for strategy in STRATEGIES:
            strategy_rows = [row for row in rows if row["strategy"] == strategy]
            print(
                f"  {strategy}: Precision@10={mean(row['precision_at_10'] for row in strategy_rows):.3f} "
                f"MRR={mean(row['mrr'] for row in strategy_rows):.3f} "
                f"nDCG@10={mean(row['ndcg_at_10'] for row in strategy_rows):.3f} "
                f"latency_ms={mean(row['latency_ms'] for row in strategy_rows):.1f}"
            )
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly.
        print(f"Hybrid evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())