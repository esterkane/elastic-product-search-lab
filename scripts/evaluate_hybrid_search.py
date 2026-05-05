"""Compare lexical and hybrid retrieval strategies with offline metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
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
from src.search.rerank import PlaceholderTextSimilarityReranker, SearchResult, rerank_window  # noqa: E402
from src.search.hybrid_search import hybrid_rrf_search, lexical_search, timed_strategy  # noqa: E402
from scripts.evaluate_relevance import enriched_profile_query  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS = PROJECT_ROOT / "data" / "sample" / "judgments.jsonl"
DEFAULT_JSON_REPORT = PROJECT_ROOT / "reports" / "retrieval-strategy-report.json"
DEFAULT_MARKDOWN_REPORT = PROJECT_ROOT / "reports" / "retrieval-strategy-report.md"
STRATEGIES = ("baseline_lexical", "boosted_lexical", "enriched_profile", "hybrid_rrf", "reranked")


@dataclass(frozen=True)
class RetrievalEvaluationRow:
    query: str
    strategy: str
    latency_ms: float
    precision_at_10: float
    mrr: float
    ndcg_at_10: float
    ranked_product_ids: list[str]


def score_ranking(ranking: list[str], judgments: dict[str, int], k: int) -> dict[str, float]:
    return {
        "precision_at_10": precision_at_k(ranking, judgments, k),
        "mrr": reciprocal_rank(ranking, judgments),
        "ndcg_at_10": ndcg_at_k(ranking, judgments, k),
    }


def enriched_profile_search(client: Any, index_name: str, query: str, size: int) -> list[str]:
    return [str(hit["_id"]) for hit in client.search(index=index_name, **enriched_profile_query(query, size)).get("hits", {}).get("hits", [])]


def fetch_candidates(client: Any, index_name: str, product_ids: list[str]) -> list[SearchResult]:
    if not product_ids:
        return []
    response = client.mget(index=index_name, ids=product_ids)
    docs_by_id = {str(doc.get("_id")): doc for doc in response.get("docs", []) if doc.get("found", False)}
    candidates: list[SearchResult] = []
    for position, product_id in enumerate(product_ids):
        doc = docs_by_id.get(product_id)
        if not doc:
            continue
        source = doc.get("_source", {}) or {}
        candidates.append(
            SearchResult(
                product_id=product_id,
                score=1.0 / (position + 1),
                title=str(source.get("title", "")),
                brand=str(source.get("brand", "")),
                category=str(source.get("category", "")),
                description=str(source.get("description", "")),
                catalog_text=str(source.get("catalog_text", "")),
                source=source,
            )
        )
    return candidates


def reranked_search(client: Any, index_name: str, query: str, embedder: Any, size: int) -> list[str]:
    first_stage_ids = hybrid_rrf_search(client, index_name, query, embedder, max(size, 20))
    candidates = fetch_candidates(client, index_name, first_stage_ids)
    reranked = rerank_window(query, candidates, PlaceholderTextSimilarityReranker(), min(len(candidates), 20))
    return [candidate.product_id for candidate in reranked[:size]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate lexical and hybrid product search strategies.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    parser.add_argument("--provider", choices=["auto", "sentence-transformers", "hash"], default="auto")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--rerank", action="store_true", help="Include deterministic local reranking on top of hybrid candidates.")
    return parser.parse_args()


def write_reports(rows: list[RetrievalEvaluationRow], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    summary = []
    for strategy in sorted({row.strategy for row in rows}):
        strategy_rows = [row for row in rows if row.strategy == strategy]
        summary.append(
            {
                "strategy": strategy,
                "query_count": len(strategy_rows),
                "precision_at_10": mean(row.precision_at_10 for row in strategy_rows),
                "mrr": mean(row.mrr for row in strategy_rows),
                "ndcg_at_10": mean(row.ndcg_at_10 for row in strategy_rows),
                "latency_ms": mean(row.latency_ms for row in strategy_rows),
            }
        )
    report = {
        "generated_at_unix": time.time(),
        "strategies": [row["strategy"] for row in summary],
        "summary": summary,
        "rows": [asdict(row) for row in rows],
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Retrieval Strategy Report",
        "",
        "Offline comparison of lexical, enriched, hybrid RRF, and optional reranked retrieval. Latency values are measured at the client script.",
        "",
        "| Strategy | Queries | Precision@10 | MRR | nDCG@10 | Avg Latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['strategy']} | {row['query_count']} | {row['precision_at_10']:.3f} | "
            f"{row['mrr']:.3f} | {row['ndcg_at_10']:.3f} | {row['latency_ms']:.1f} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
                timed_strategy("enriched_profile", query, lambda q=query: enriched_profile_search(client, args.index, q, args.k)),
                timed_strategy("hybrid_rrf", query, lambda q=query: hybrid_rrf_search(client, args.index, q, embedder, args.k)),
            ]
            if args.rerank:
                results.append(timed_strategy("reranked", query, lambda q=query: reranked_search(client, args.index, q, embedder, args.k)))
            for result in results:
                metrics = score_ranking(result.ranked_product_ids, judgments, args.k)
                row = RetrievalEvaluationRow(
                    query=query,
                    strategy=result.strategy,
                    latency_ms=result.latency_ms,
                    ranked_product_ids=result.ranked_product_ids,
                    **metrics,
                )
                rows.append(row)
                print(
                    f"{query} [{result.strategy}]: Precision@10={row.precision_at_10:.3f} "
                    f"MRR={row.mrr:.3f} nDCG@10={row.ndcg_at_10:.3f} "
                    f"latency_ms={result.latency_ms:.1f}"
                )
        print("aggregate:")
        for strategy in [strategy for strategy in STRATEGIES if any(row.strategy == strategy for row in rows)]:
            strategy_rows = [row for row in rows if row.strategy == strategy]
            print(
                f"  {strategy}: Precision@10={mean(row.precision_at_10 for row in strategy_rows):.3f} "
                f"MRR={mean(row.mrr for row in strategy_rows):.3f} "
                f"nDCG@10={mean(row.ndcg_at_10 for row in strategy_rows):.3f} "
                f"latency_ms={mean(row.latency_ms for row in strategy_rows):.1f}"
            )
        write_reports(rows, args.json_report, args.markdown_report)
        print(f"Wrote {args.json_report}")
        print(f"Wrote {args.markdown_report}")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly.
        print(f"Hybrid evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
