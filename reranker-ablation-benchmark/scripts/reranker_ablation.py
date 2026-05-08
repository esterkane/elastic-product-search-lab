from __future__ import annotations

import argparse
import json
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    doc_id: str
    title: str
    retrieval_score: float
    reranker_score: float
    grade: int


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    query: str
    candidates: list[Candidate]


def load_cases(path: Path) -> tuple[int, list[QueryCase], dict[str, list[float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        QueryCase(
            query_id=row["query_id"],
            query=row["query"],
            candidates=[Candidate(**candidate) for candidate in row["candidates"]],
        )
        for row in data["queries"]
    ]
    return int(data["top_k"]), cases, data["latency_ms"]


def evaluate_ablation(top_k: int, cases: Sequence[QueryCase], latency_ms: dict[str, list[float]]) -> dict[str, object]:
    baseline_rows = [evaluate_query(case, "baseline", top_k) for case in cases]
    reranked_rows = [evaluate_query(case, "reranked", top_k) for case in cases]
    baseline_latency = latency_ms["baseline_retrieval"]
    reranked_latency = [
        retrieval + reranker
        for retrieval, reranker in zip(baseline_latency, latency_ms["reranker_stage"], strict=True)
    ]
    baseline = summarize_run("baseline", "First-stage retrieval order, no reranker.", baseline_rows, baseline_latency)
    reranked = summarize_run(
        "reranked",
        f"Same top-{top_k} candidate set reranked by deterministic cross-encoder score.",
        reranked_rows,
        reranked_latency,
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "top_k": top_k,
        "runs": [baseline, reranked],
        "comparison": compare_runs(baseline, reranked),
        "recommendation": recommendation(compare_runs(baseline, reranked)),
    }


def evaluate_query(case: QueryCase, mode: str, top_k: int) -> dict[str, object]:
    if mode == "baseline":
        ranked = sorted(case.candidates, key=lambda candidate: (-candidate.retrieval_score, candidate.doc_id))[:top_k]
    elif mode == "reranked":
        candidate_set = sorted(case.candidates, key=lambda candidate: (-candidate.retrieval_score, candidate.doc_id))[:top_k]
        ranked = sorted(candidate_set, key=lambda candidate: (-candidate.reranker_score, candidate.doc_id))
    else:
        raise ValueError(f"unknown mode: {mode}")
    ranked_ids = [candidate.doc_id for candidate in ranked]
    relevance = {candidate.doc_id: candidate.grade for candidate in case.candidates}
    relevant_ids = {candidate.doc_id for candidate in case.candidates if candidate.grade > 0}
    return {
        "query_id": case.query_id,
        "query": case.query,
        "ranked_ids": ranked_ids,
        "top_result": ranked_ids[0] if ranked_ids else None,
        "ndcg_at_5": ndcg_at_k(ranked_ids, relevance, 5),
        "mrr_at_5": mrr_at_k(ranked_ids, relevant_ids, 5),
        "precision_at_3": precision_at_k(ranked_ids, relevant_ids, 3),
        "recall_at_5": recall_at_k(ranked_ids, relevant_ids, 5),
    }


def summarize_run(name: str, description: str, rows: list[dict[str, object]], latencies: list[float]) -> dict[str, object]:
    return {
        "name": name,
        "description": description,
        "metrics": {
            "ndcg_at_5": mean([float(row["ndcg_at_5"]) for row in rows]),
            "mrr_at_5": mean([float(row["mrr_at_5"]) for row in rows]),
            "precision_at_3": mean([float(row["precision_at_3"]) for row in rows]),
            "recall_at_5": mean([float(row["recall_at_5"]) for row in rows]),
            "p50_latency_ms": percentile(latencies, 50),
            "p95_latency_ms": percentile(latencies, 95),
        },
        "queries": rows,
    }


def compare_runs(baseline: dict[str, object], reranked: dict[str, object]) -> dict[str, object]:
    baseline_metrics = baseline["metrics"]
    reranked_metrics = reranked["metrics"]
    return {
        "baseline": baseline["name"],
        "candidate": reranked["name"],
        "ndcg_at_5_delta": reranked_metrics["ndcg_at_5"] - baseline_metrics["ndcg_at_5"],
        "mrr_at_5_delta": reranked_metrics["mrr_at_5"] - baseline_metrics["mrr_at_5"],
        "precision_at_3_delta": reranked_metrics["precision_at_3"] - baseline_metrics["precision_at_3"],
        "recall_at_5_delta": reranked_metrics["recall_at_5"] - baseline_metrics["recall_at_5"],
        "p95_latency_ms_delta": reranked_metrics["p95_latency_ms"] - baseline_metrics["p95_latency_ms"],
    }


def recommendation(comparison: dict[str, object]) -> str:
    ndcg_delta = float(comparison["ndcg_at_5_delta"])
    latency_delta = float(comparison["p95_latency_ms_delta"])
    if ndcg_delta >= 0.05 and latency_delta <= 45:
        return "Use reranking conditionally for ambiguous, high-value, or answer-generating searches; keep first-stage retrieval for low-latency browsing."
    return "Keep reranking opt-in until the judged uplift justifies the added latency."


def markdown_report(report: dict[str, object]) -> str:
    comparison = report["comparison"]
    lines = [
        "# Reranker Ablation Benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Top-k reranked: `{report['top_k']}`",
        "",
        "## ROI Summary",
        "",
        "| Baseline | Candidate | nDCG@5 delta | MRR@5 delta | Precision@3 delta | Recall@5 delta | p95 latency delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        f"| {comparison['baseline']} | {comparison['candidate']} | {comparison['ndcg_at_5_delta']:+.3f} | {comparison['mrr_at_5_delta']:+.3f} | {comparison['precision_at_3_delta']:+.3f} | {comparison['recall_at_5_delta']:+.3f} | {comparison['p95_latency_ms_delta']:+.1f} ms |",
        "",
        "## When Reranking Helps",
        "",
        str(report["recommendation"]),
        "",
    ]
    for run in report["runs"]:
        metrics = run["metrics"]
        lines.extend([
            f"## {run['name']}",
            "",
            run["description"],
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| nDCG@5 | {metrics['ndcg_at_5']:.3f} |",
            f"| MRR@5 | {metrics['mrr_at_5']:.3f} |",
            f"| Precision@3 | {metrics['precision_at_3']:.3f} |",
            f"| Recall@5 | {metrics['recall_at_5']:.3f} |",
            f"| p50 latency | {metrics['p50_latency_ms']:.1f} ms |",
            f"| p95 latency | {metrics['p95_latency_ms']:.1f} ms |",
            "",
            "| Query | Top result | nDCG@5 | MRR@5 | Ranked ids |",
            "| --- | --- | ---: | ---: | --- |",
        ])
        for row in run["queries"]:
            lines.append(
                f"| {row['query_id']} | {row['top_result']} | {row['ndcg_at_5']:.3f} | {row['mrr_at_5']:.3f} | {', '.join(row['ranked_ids'])} |"
            )
        lines.append("")
    return "\n".join(lines)


def ndcg_at_k(ranked_ids: Sequence[str], relevance: dict[str, int], k: int) -> float:
    dcg = 0.0
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        gain = relevance.get(doc_id, 0)
        dcg += (2**gain - 1) / math.log2(index + 1)
    ideal_gains = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**gain - 1) / math.log2(index + 1) for index, gain in enumerate(ideal_gains, start=1))
    return dcg / idcg if idcg else 0.0


def mrr_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in relevant_ids:
            return 1.0 / index
    return 0.0


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    return len(set(ranked_ids[:k]) & relevant_ids) / k if k > 0 else 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def percentile(values: Sequence[float], percentile_value: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run reranker/no-reranker ablation on a fixed top-k candidate set.")
    parser.add_argument("--input", type=Path, default=Path("data/candidates.json"))
    parser.add_argument("--report-json", type=Path, default=Path("reports/reranker-ablation-report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/reranker-ablation-report.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    top_k, cases, latency_ms = load_cases(args.input)
    report = evaluate_ablation(top_k, cases, latency_ms)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.report_md.write_text(markdown_report(report), encoding="utf-8")
    print(f"wrote {args.report_json} and {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
