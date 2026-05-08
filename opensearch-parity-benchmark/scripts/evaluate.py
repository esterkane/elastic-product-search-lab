from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from embedding import embed_text
from ingest import INDEX_NAME, PIPELINE_NAME
from metrics import mean, mrr_at_k, ndcg_at_k, percentile, precision_at_k, recall_at_k
from opensearch_api import OpenSearchClient, read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate BM25 and OpenSearch hybrid RRF strategies.")
    parser.add_argument("--host", default="http://localhost:9201")
    parser.add_argument("--judgments", type=Path, default=Path("data/judgments.jsonl"))
    parser.add_argument("--report-json", type=Path, default=Path("reports/opensearch-parity-report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/opensearch-parity-report.md"))
    args = parser.parse_args()

    client = OpenSearchClient(args.host)
    client.wait_until_ready()
    judgments = load_judgments(args.judgments)
    strategies = {
        "bm25": search_bm25,
        "hybrid_rrf": search_hybrid_rrf,
    }
    runs = [evaluate_strategy(client, judgments, name, searcher) for name, searcher in strategies.items()]
    report = build_report(runs)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.report_md.write_text(markdown_report(report), encoding="utf-8")
    print(f"wrote {args.report_json} and {args.report_md}")
    return 0


def load_judgments(path: Path) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for row in read_jsonl(path):
        query_id = str(row["query_id"])
        entry = grouped.setdefault(query_id, {"query": row["query"], "judgments": {}})
        entry["judgments"][str(row["doc_id"])] = int(row["grade"])  # type: ignore[index]
    return grouped


def evaluate_strategy(client: OpenSearchClient, judgments: dict[str, dict[str, object]], name: str, searcher) -> dict[str, object]:
    query_rows = []
    latencies = []
    for query_id, case in judgments.items():
        started = time.perf_counter()
        hits = searcher(client, str(case["query"]))
        latencies.append((time.perf_counter() - started) * 1000)
        ranked_ids = [hit["_id"] for hit in hits]
        grades = case["judgments"]  # type: ignore[assignment]
        relevant_ids = {doc_id for doc_id, grade in grades.items() if grade > 0}
        query_rows.append(
            {
                "query_id": query_id,
                "query": case["query"],
                "top_result": ranked_ids[0] if ranked_ids else None,
                "ranked_ids": ranked_ids,
                "ndcg_at_10": ndcg_at_k(ranked_ids, grades, 10),
                "precision_at_5": precision_at_k(ranked_ids, relevant_ids, 5),
                "mrr_at_10": mrr_at_k(ranked_ids, relevant_ids, 10),
                "recall_at_10": recall_at_k(ranked_ids, relevant_ids, 10),
            }
        )
    return {
        "name": name,
        "queries": query_rows,
        "metrics": {
            "ndcg_at_10": mean([row["ndcg_at_10"] for row in query_rows]),
            "precision_at_5": mean([row["precision_at_5"] for row in query_rows]),
            "mrr_at_10": mean([row["mrr_at_10"] for row in query_rows]),
            "recall_at_10": mean([row["recall_at_10"] for row in query_rows]),
            "p50_latency_ms": percentile(latencies, 50),
            "p95_latency_ms": percentile(latencies, 95),
        },
    }


def search_bm25(client: OpenSearchClient, query: str) -> list[dict[str, object]]:
    response = client.request(
        "POST",
        f"/{INDEX_NAME}/_search",
        {
            "size": 10,
            "_source": ["title", "category"],
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "body"],
                    "operator": "or",
                }
            },
        },
    )
    return response["hits"]["hits"]  # type: ignore[index]


def search_hybrid_rrf(client: OpenSearchClient, query: str) -> list[dict[str, object]]:
    response = client.request(
        "POST",
        f"/{INDEX_NAME}/_search?search_pipeline={PIPELINE_NAME}",
        {
            "size": 10,
            "_source": ["title", "category"],
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "body"],
                                "operator": "or",
                            }
                        },
                        {
                            "knn": {
                                "embedding": {
                                    "vector": embed_text(query),
                                    "k": 10,
                                }
                            }
                        },
                    ]
                }
            },
        },
    )
    return response["hits"]["hits"]  # type: ignore[index]


def build_report(runs: list[dict[str, object]]) -> dict[str, object]:
    by_name = {run["name"]: run for run in runs}
    bm25 = by_name["bm25"]["metrics"]
    hybrid = by_name["hybrid_rrf"]["metrics"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "engine": "OpenSearch 2.19.1",
        "index": INDEX_NAME,
        "strategies": ["bm25", "hybrid_rrf"],
        "runs": runs,
        "comparison": {
            "baseline": "bm25",
            "candidate": "hybrid_rrf",
            "ndcg_at_10_delta": hybrid["ndcg_at_10"] - bm25["ndcg_at_10"],
            "recall_at_10_delta": hybrid["recall_at_10"] - bm25["recall_at_10"],
            "p95_latency_ms_delta": hybrid["p95_latency_ms"] - bm25["p95_latency_ms"],
        },
    }


def markdown_report(report: dict[str, object]) -> str:
    comparison = report["comparison"]
    lines = [
        "# OpenSearch Parity Benchmark Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Engine: `{report['engine']}`",
        f"Index: `{report['index']}`",
        "",
        "## Before/After",
        "",
        "| Baseline | Candidate | nDCG@10 delta | Recall@10 delta | p95 latency delta |",
        "| --- | --- | ---: | ---: | ---: |",
        f"| {comparison['baseline']} | {comparison['candidate']} | {comparison['ndcg_at_10_delta']:+.3f} | {comparison['recall_at_10_delta']:+.3f} | {comparison['p95_latency_ms_delta']:+.1f} ms |",
        "",
    ]
    for run in report["runs"]:
        metrics = run["metrics"]
        lines.extend(
            [
                f"## {run['name']}",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| nDCG@10 | {metrics['ndcg_at_10']:.3f} |",
                f"| Precision@5 | {metrics['precision_at_5']:.3f} |",
                f"| MRR@10 | {metrics['mrr_at_10']:.3f} |",
                f"| Recall@10 | {metrics['recall_at_10']:.3f} |",
                f"| p50 latency | {metrics['p50_latency_ms']:.1f} ms |",
                f"| p95 latency | {metrics['p95_latency_ms']:.1f} ms |",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
