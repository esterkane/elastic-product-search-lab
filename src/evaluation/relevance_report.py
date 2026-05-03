"""Judgment-list relevance report helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from src.evaluation.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


@dataclass(frozen=True)
class QueryJudgment:
    query: str
    judgments: dict[str, int]


@dataclass(frozen=True)
class StrategyEvaluationRow:
    strategy: str
    query: str
    status: str
    precision_at_5: float
    recall_at_5: float
    mrr_at_10: float
    ndcg_at_10: float
    ranked_product_ids: list[str]
    note: str = ""


def load_product_search_judgments(path: Path) -> list[QueryJudgment]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    judgments: list[QueryJudgment] = []
    for index, row in enumerate(rows, start=1):
        query = str(row.get("query", "")).strip()
        if not query:
            raise ValueError(f"Judgment row {index} is missing query")
        raw_judgments = row.get("judgments")
        if not isinstance(raw_judgments, dict) or not raw_judgments:
            raise ValueError(f"Judgment row {index} must include non-empty judgments")
        judgments.append(QueryJudgment(query=query, judgments={str(product_id): int(grade) for product_id, grade in raw_judgments.items()}))
    return judgments


def evaluate_ranking(strategy: str, query: str, judgments: dict[str, int], ranked_product_ids: list[str]) -> StrategyEvaluationRow:
    return StrategyEvaluationRow(
        strategy=strategy,
        query=query,
        status="ok",
        precision_at_5=precision_at_k(ranked_product_ids, judgments, 5),
        recall_at_5=recall_at_k(ranked_product_ids, judgments, 5),
        mrr_at_10=reciprocal_rank(ranked_product_ids[:10], judgments),
        ndcg_at_10=ndcg_at_k(ranked_product_ids, judgments, 10),
        ranked_product_ids=ranked_product_ids,
    )


def aggregate_by_strategy(rows: list[StrategyEvaluationRow], baseline_strategy: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[StrategyEvaluationRow]] = defaultdict(list)
    for row in rows:
        grouped[row.strategy].append(row)

    raw_summary: dict[str, dict[str, Any]] = {}
    for strategy in sorted(grouped):
        strategy_rows = grouped[strategy]
        ok_rows = [row for row in strategy_rows if row.status == "ok"]
        raw_summary[strategy] = {
            "strategy": strategy,
            "status": "ok" if ok_rows else "pending",
            "evaluated_queries": len(ok_rows),
            "pending_queries": len(strategy_rows) - len(ok_rows),
            "precision_at_5": mean(row.precision_at_5 for row in ok_rows) if ok_rows else 0.0,
            "recall_at_5": mean(row.recall_at_5 for row in ok_rows) if ok_rows else 0.0,
            "mrr_at_10": mean(row.mrr_at_10 for row in ok_rows) if ok_rows else 0.0,
            "ndcg_at_10": mean(row.ndcg_at_10 for row in ok_rows) if ok_rows else 0.0,
        }

    baseline = raw_summary.get(baseline_strategy, {})
    for summary in raw_summary.values():
        summary["delta_precision_at_5"] = summary["precision_at_5"] - baseline.get("precision_at_5", 0.0)
        summary["delta_recall_at_5"] = summary["recall_at_5"] - baseline.get("recall_at_5", 0.0)
        summary["delta_mrr_at_10"] = summary["mrr_at_10"] - baseline.get("mrr_at_10", 0.0)
        summary["delta_ndcg_at_10"] = summary["ndcg_at_10"] - baseline.get("ndcg_at_10", 0.0)
    return [raw_summary[strategy] for strategy in sorted(raw_summary)]


def _score_tuple(row: StrategyEvaluationRow) -> tuple[float, float, float, float]:
    return (row.ndcg_at_10, row.mrr_at_10, row.recall_at_5, row.precision_at_5)


def winners_by_query(rows: list[StrategyEvaluationRow]) -> dict[str, list[str]]:
    grouped: dict[str, list[StrategyEvaluationRow]] = defaultdict(list)
    for row in rows:
        if row.status == "ok":
            grouped[row.query].append(row)
    winners: dict[str, list[str]] = {}
    for query, query_rows in grouped.items():
        best_score = max(_score_tuple(row) for row in query_rows)
        if best_score == (0.0, 0.0, 0.0, 0.0):
            winners[query] = []
            continue
        winners[query] = [row.strategy for row in query_rows if _score_tuple(row) == best_score]
    return winners


def build_report(rows: list[StrategyEvaluationRow], query_count: int, baseline_strategy: str = "baseline_bm25") -> dict[str, Any]:
    winners = winners_by_query(rows)
    return {
        "query_count": query_count,
        "baseline_strategy": baseline_strategy,
        "summary": aggregate_by_strategy(rows, baseline_strategy),
        "per_query": [{**asdict(row), "winners": winners.get(row.query, [])} for row in rows],
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Product Search Relevance Report",
        "",
        f"Evaluated queries: {report['query_count']}",
        f"Baseline strategy: `{report['baseline_strategy']}`",
        "",
        "## Strategy Summary",
        "",
        "| Strategy | Status | Evaluated Queries | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Delta nDCG@10 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["summary"]:
        lines.append(
            f"| {row['strategy']} | {row['status']} | {row['evaluated_queries']} | "
            f"{row['precision_at_5']:.3f} | {row['recall_at_5']:.3f} | {row['mrr_at_10']:.3f} | "
            f"{row['ndcg_at_10']:.3f} | {row['delta_ndcg_at_10']:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Per-Query Results",
            "",
            "| Query | Strategy | Winner | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Top Results |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["per_query"]:
        top_results = ", ".join(row["ranked_product_ids"][:5]) or "none"
        winner = "tie" if row["strategy"] in row["winners"] and len(row["winners"]) > 1 else ("yes" if row["strategy"] in row["winners"] else "")
        lines.append(
            f"| {row['query']} | {row['strategy']} | {winner} | {row['precision_at_5']:.3f} | "
            f"{row['recall_at_5']:.3f} | {row['mrr_at_10']:.3f} | {row['ndcg_at_10']:.3f} | {top_results} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "`search_profile` is deterministic ingestion-time text enrichment built from product fields. The `enriched_profile` strategy searches that field plus title/category/brand context.",
            "Metrics are deterministic and use the checked-in judgment list under `data/judgments/product_search_judgments.json`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
