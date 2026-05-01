"""Evaluate local Elasticsearch product search against graded judgments."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.evaluation.judgments import load_judgments  # noqa: E402
from src.evaluation.metrics import ndcg_at_k, precision_at_k, reciprocal_rank  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS_PATH = PROJECT_ROOT / "data" / "sample" / "judgments.jsonl"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "data" / "generated" / "relevance_report.json"
DEFAULT_MD_REPORT_PATH = PROJECT_ROOT / "examples" / "relevance_report.md"


def build_eval_query(query: str, size: int) -> dict[str, Any]:
    return {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^4", "brand^2", "category^1.5", "description^0.8", "catalog_text^0.5"],
                            "type": "best_fields",
                            "operator": "and",
                        }
                    }
                ],
                "filter": [],
            }
        },
        "sort": ["_score"],
    }


def ranked_product_ids(client: Any, index_name: str, query: str, size: int) -> list[str]:
    response = client.search(index=index_name, **build_eval_query(query, size))
    return [str(hit["_id"]) for hit in response.get("hits", {}).get("hits", [])]


def evaluate(client: Any, index_name: str, judgments: dict[str, dict[str, int]], k: int) -> dict[str, Any]:
    per_query: list[dict[str, Any]] = []

    for query in sorted(judgments):
        ranking = ranked_product_ids(client, index_name, query, k)
        query_judgments = judgments[query]
        per_query.append(
            {
                "query": query,
                "precision_at_10": precision_at_k(ranking, query_judgments, k),
                "mrr": reciprocal_rank(ranking, query_judgments),
                "ndcg_at_10": ndcg_at_k(ranking, query_judgments, k),
                "ranked_product_ids": ranking,
            }
        )

    aggregate = {
        "precision_at_10": mean(row["precision_at_10"] for row in per_query) if per_query else 0.0,
        "mrr": mean(row["mrr"] for row in per_query) if per_query else 0.0,
        "ndcg_at_10": mean(row["ndcg_at_10"] for row in per_query) if per_query else 0.0,
    }
    return {"k": k, "per_query": per_query, "aggregate": aggregate}


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Relevance Report",
        "",
        "Offline evaluation for the local sample product catalog using graded relevance judgments.",
        "",
        "## Why This Matters",
        "",
        "This report gives a hiring reviewer a quick view of how search quality is measured. It shows per-query behavior, not just an aggregate score, because product search changes often help one query class while hurting another.",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value | What It Indicates |",
        "| --- | ---: | --- |",
        f"| Precision@10 | {report['aggregate']['precision_at_10']:.3f} | Share of returned top-10 products judged relevant. |",
        f"| MRR | {report['aggregate']['mrr']:.3f} | How quickly the first relevant product appears. |",
        f"| nDCG@10 | {report['aggregate']['ndcg_at_10']:.3f} | Ranking quality with graded relevance. |",
        "",
        "## Per-Query Metrics",
        "",
        "| Query | Precision@10 | MRR | nDCG@10 | Top Results |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["per_query"]:
        top_results = ", ".join(row["ranked_product_ids"][:5]) or "none"
        lines.append(
            f"| {row['query']} | {row['precision_at_10']:.3f} | {row['mrr']:.3f} | "
            f"{row['ndcg_at_10']:.3f} | {top_results} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "Precision@10 counts relevant products in the top results but does not care where they appear. MRR rewards the first relevant product appearing early. nDCG@10 uses graded relevance, so exact matches are worth more than substitutes or complements.",
            "",
            "The zero-result rows are useful, not embarrassing: they show where the sample catalog or query strategy needs more coverage.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate local product search relevance.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS_PATH)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MD_REPORT_PATH)
    parser.add_argument("--k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()

    try:
        ensure_reachable(client)
        judgments = load_judgments(args.judgments)
        report = evaluate(client, args.index, judgments, args.k)
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        write_markdown_report(report, args.markdown_report)

        for row in report["per_query"]:
            print(
                f"{row['query']}: Precision@10={row['precision_at_10']:.3f} "
                f"MRR={row['mrr']:.3f} nDCG@10={row['ndcg_at_10']:.3f}"
            )
        print(
            "aggregate: "
            f"Precision@10={report['aggregate']['precision_at_10']:.3f} "
            f"MRR={report['aggregate']['mrr']:.3f} "
            f"nDCG@10={report['aggregate']['ndcg_at_10']:.3f}"
        )
    except Exception as exc:  # noqa: BLE001 - script should fail clearly for local use.
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
