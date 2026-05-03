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


def pending_rows(strategy: str, judgments: list[QueryJudgment], note: str) -> list[StrategyEvaluationRow]:
    return [
        StrategyEvaluationRow(
            strategy=strategy,
            query=row.query,
            status="pending",
            precision_at_5=0.0,
            recall_at_5=0.0,
            mrr_at_10=0.0,
            ndcg_at_10=0.0,
            ranked_product_ids=[],
            note=note,
        )
        for row in judgments
    ]


def aggregate_by_strategy(rows: list[StrategyEvaluationRow]) -> list[dict[str, Any]]:
    grouped: dict[str, list[StrategyEvaluationRow]] = defaultdict(list)
    for row in rows:
        grouped[row.strategy].append(row)

    summary: list[dict[str, Any]] = []
    for strategy in sorted(grouped):
        strategy_rows = grouped[strategy]
        ok_rows = [row for row in strategy_rows if row.status == "ok"]
        summary.append(
            {
                "strategy": strategy,
                "status": "ok" if ok_rows else "pending",
                "evaluated_queries": len(ok_rows),
                "pending_queries": len(strategy_rows) - len(ok_rows),
                "precision_at_5": mean(row.precision_at_5 for row in ok_rows) if ok_rows else 0.0,
                "recall_at_5": mean(row.recall_at_5 for row in ok_rows) if ok_rows else 0.0,
                "mrr_at_10": mean(row.mrr_at_10 for row in ok_rows) if ok_rows else 0.0,
                "ndcg_at_10": mean(row.ndcg_at_10 for row in ok_rows) if ok_rows else 0.0,
            }
        )
    return summary


def build_report(rows: list[StrategyEvaluationRow], query_count: int) -> dict[str, Any]:
    return {
        "query_count": query_count,
        "summary": aggregate_by_strategy(rows),
        "per_query": [asdict(row) for row in rows],
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
        "",
        "## Strategy Summary",
        "",
        "| Strategy | Status | Evaluated Queries | Pending Queries | Precision@5 | Recall@5 | MRR@10 | nDCG@10 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["summary"]:
        lines.append(
            f"| {row['strategy']} | {row['status']} | {row['evaluated_queries']} | {row['pending_queries']} | "
            f"{row['precision_at_5']:.3f} | {row['recall_at_5']:.3f} | {row['mrr_at_10']:.3f} | {row['ndcg_at_10']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Per-Query Results",
            "",
            "| Query | Strategy | Status | Precision@5 | Recall@5 | MRR@10 | nDCG@10 | Top Results | Note |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in report["per_query"]:
        top_results = ", ".join(row["ranked_product_ids"][:5]) or "none"
        lines.append(
            f"| {row['query']} | {row['strategy']} | {row['status']} | {row['precision_at_5']:.3f} | "
            f"{row['recall_at_5']:.3f} | {row['mrr_at_10']:.3f} | {row['ndcg_at_10']:.3f} | {top_results} | {row['note']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "`enriched_profile` is included as a pending strategy until enriched product-profile fields are added to the index.",
            "Metrics are deterministic and use the checked-in judgment list under `data/judgments/product_search_judgments.json`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
