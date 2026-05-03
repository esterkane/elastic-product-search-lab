"""Evaluate product search strategies against a checked-in judgment list."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.evaluation.relevance_report import (  # noqa: E402
    build_report,
    evaluate_ranking,
    load_product_search_judgments,
    write_json_report,
    write_markdown_report,
)
from src.search.hybrid_search import baseline_lexical_query, extract_ids  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS_PATH = PROJECT_ROOT / "data" / "judgments" / "product_search_judgments.json"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "reports" / "relevance-report.json"
DEFAULT_MD_REPORT_PATH = PROJECT_ROOT / "reports" / "relevance-report.md"


def boosted_bm25_evaluation_query(query: str, size: int) -> dict[str, Any]:
    """More forgiving BM25 variant for offline comparison."""

    return {
        "size": size,
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^4", "brand^2", "category^1.5", "description", "catalog_text^0.8"],
                        "type": "best_fields",
                        "operator": "or",
                        "minimum_should_match": "2<75%",
                        "fuzziness": "AUTO",
                    }
                },
                "score_mode": "sum",
                "boost_mode": "sum",
                "functions": [
                    {"field_value_factor": {"field": "popularity_score", "factor": 0.01, "modifier": "sqrt", "missing": 0}},
                    {"gauss": {"updated_at": {"origin": "now", "scale": "30d", "offset": "7d", "decay": 0.5}}, "weight": 0.1},
                ],
            }
        },
        "sort": ["_score"],
    }


def enriched_profile_query(query: str, size: int) -> dict[str, Any]:
    """Readable strategy that searches ingestion-time enriched product profiles."""

    return {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["search_profile^3", "title^2", "category^1.5", "brand", "description^0.5"],
                "type": "best_fields",
                "operator": "or",
                "minimum_should_match": "2<70%",
                "fuzziness": "AUTO",
            }
        },
        "sort": ["_score"],
    }


def run_search(client: Any, index_name: str, query: str, strategy: str, size: int) -> list[str]:
    if strategy == "baseline_bm25":
        body = baseline_lexical_query(query, size)
    elif strategy == "boosted_bm25":
        body = boosted_bm25_evaluation_query(query, size)
    elif strategy == "enriched_profile":
        body = enriched_profile_query(query, size)
    else:
        raise ValueError(f"Unsupported executable strategy: {strategy}")
    return extract_ids(client.search(index=index_name, **body))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate product search relevance using checked-in judgments.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS_PATH)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MD_REPORT_PATH)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--max-queries", type=int, help="Evaluate only the first N deterministic judgment queries.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        judgments = load_product_search_judgments(args.judgments)
        if args.max_queries is not None:
            judgments = judgments[: args.max_queries]
        rows = []
        for query_judgment in judgments:
            for strategy in ("baseline_bm25", "boosted_bm25", "enriched_profile"):
                ranked_product_ids = run_search(client, args.index, query_judgment.query, strategy, args.size)
                rows.append(evaluate_ranking(strategy, query_judgment.query, query_judgment.judgments, ranked_product_ids))

        report = build_report(rows, query_count=len(judgments), baseline_strategy="baseline_bm25")
        write_json_report(report, args.json_report)
        write_markdown_report(report, args.markdown_report)

        print(f"Evaluated queries: {report['query_count']}")
        for row in report["summary"]:
            print(
                f"{row['strategy']}: status={row['status']} evaluated={row['evaluated_queries']} "
                f"Precision@5={row['precision_at_5']:.3f} Recall@5={row['recall_at_5']:.3f} "
                f"MRR@10={row['mrr_at_10']:.3f} nDCG@10={row['ndcg_at_10']:.3f} "
                f"Delta nDCG@10={row['delta_ndcg_at_10']:+.3f}"
            )
        print(f"Wrote {args.json_report}")
        print(f"Wrote {args.markdown_report}")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly for local use.
        print(f"Relevance evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
