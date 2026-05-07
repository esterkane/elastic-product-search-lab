from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.eval.metrics import mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k, zero_result_rate


ESCI_GRADES = {
    "E": 3,
    "EXACT": 3,
    "S": 2,
    "SUBSTITUTE": 2,
    "C": 1,
    "COMPLEMENT": 1,
    "I": 0,
    "IRRELEVANT": 0,
}


@dataclass(frozen=True)
class EsciCase:
    query_id: str
    query: str
    judgments: dict[str, int]
    segment: str = "default"


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    status: str
    expected_recovery: str
    observed: str
    gate: str
    evidence: str


@dataclass
class SearchChangeRun:
    name: str
    ranked_results: dict[str, list[str]]
    latency_ms: list[float]
    request_count: int
    duration_seconds: float
    strategy: str = "ranked-list"
    description: str = ""
    channel_results: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    rrf_rank_constant: int = 60
    shard_scenarios: dict[str, list[float]] = field(default_factory=dict)
    resilience: list[ScenarioResult] = field(default_factory=list)


@dataclass(frozen=True)
class Gates:
    ndcg_at_10: float = 0.72
    precision_at_5: float = 0.60
    mrr_at_10: float = 0.68
    recall_at_10: float = 0.72
    zero_result_rate: float = 0.05
    p95_latency_ms: float = 180.0
    p99_latency_ms: float = 260.0
    throughput_qps: float = 25.0


@dataclass(frozen=True)
class StrategyComparison:
    baseline: str
    candidate: str


def default_esci_cases() -> list[EsciCase]:
    return [
        EsciCase(
            query_id="q-hybrid",
            query="hybrid search reranking product catalog",
            judgments={"p-hybrid-guide": 3, "p-rerank-model": 3, "p-keyword-only": 1, "p-returns-policy": 0},
            segment="relevance",
        ),
        EsciCase(
            query_id="q-vector",
            query="vector search filtered retrieval latency",
            judgments={"p-vector-filter": 3, "p-latency-tuning": 2, "p-bulk-ingest": 1, "p-size-chart": 0},
            segment="performance",
        ),
        EsciCase(
            query_id="q-ingest",
            query="replay failed product updates idempotently",
            judgments={"p-replay-runbook": 3, "p-idempotent-upsert": 3, "p-soft-delete": 2, "p-homepage": 0},
            segment="resilience",
        ),
        EsciCase(
            query_id="q-zero",
            query="nonexistent sku nickname",
            judgments={"p-no-match-help": 2, "p-fuzzy-fallback": 1, "p-autocorrect": 2, "p-empty-state": 1},
            segment="zero-results",
        ),
    ]


def default_runs() -> list[SearchChangeRun]:
    resilience = default_resilience_matrix()
    return [
        SearchChangeRun(
            name="baseline-bm25",
            ranked_results={
                "q-hybrid": ["p-keyword-only", "p-hybrid-guide", "p-rerank-model", "p-returns-policy"],
                "q-vector": ["p-latency-tuning", "p-vector-filter", "p-bulk-ingest", "p-size-chart"],
                "q-ingest": ["p-replay-runbook", "p-idempotent-upsert", "p-soft-delete", "p-homepage"],
                "q-zero": ["p-fuzzy-fallback", "p-no-match-help", "p-autocorrect", "p-empty-state"],
            },
            latency_ms=[31, 34, 39, 42, 45, 52, 61, 74, 88, 111, 130],
            request_count=620,
            duration_seconds=20,
            strategy="bm25",
            description="Keyword/BM25 baseline using the lexical candidate set only.",
            shard_scenarios={
                "1_shard_50k_docs": [24, 28, 32, 38, 45, 52],
                "3_shards_250k_docs": [36, 44, 53, 66, 79, 95],
                "6_shards_1m_docs": [58, 74, 96, 119, 145, 172],
            },
            resilience=resilience,
        ),
        SearchChangeRun(
            name="hybrid-rrf",
            ranked_results={},
            channel_results={
                "q-hybrid": {
                    "lexical": ["p-keyword-only", "p-hybrid-guide", "p-rerank-model", "p-returns-policy"],
                    "dense": ["p-rerank-model", "p-hybrid-guide", "p-keyword-only", "p-returns-policy"],
                },
                "q-vector": {
                    "lexical": ["p-latency-tuning", "p-vector-filter", "p-bulk-ingest", "p-size-chart"],
                    "dense": ["p-vector-filter", "p-latency-tuning", "p-bulk-ingest", "p-size-chart"],
                },
                "q-ingest": {
                    "lexical": ["p-replay-runbook", "p-idempotent-upsert", "p-soft-delete", "p-homepage"],
                    "dense": ["p-idempotent-upsert", "p-replay-runbook", "p-soft-delete", "p-homepage"],
                },
                "q-zero": {
                    "lexical": ["p-fuzzy-fallback", "p-no-match-help", "p-empty-state"],
                    "dense": ["p-no-match-help", "p-autocorrect", "p-fuzzy-fallback", "p-empty-state"],
                },
            },
            latency_ms=[42, 47, 50, 53, 58, 64, 72, 81, 95, 121, 145],
            request_count=550,
            duration_seconds=20,
            strategy="hybrid-rrf",
            description="Lexical and dense candidate sets fused with reciprocal rank fusion before optional reranking.",
            rrf_rank_constant=60,
            shard_scenarios={
                "1_shard_50k_docs": [35, 38, 42, 49, 55, 61],
                "3_shards_250k_docs": [48, 55, 64, 75, 90, 110],
                "6_shards_1m_docs": [76, 92, 118, 145, 172, 205],
            },
            resilience=resilience,
        ),
        SearchChangeRun(
            name="candidate-good",
            ranked_results={
                "q-hybrid": ["p-rerank-model", "p-hybrid-guide", "p-keyword-only", "p-returns-policy"],
                "q-vector": ["p-vector-filter", "p-latency-tuning", "p-bulk-ingest", "p-size-chart"],
                "q-ingest": ["p-idempotent-upsert", "p-replay-runbook", "p-soft-delete", "p-homepage"],
                "q-zero": ["p-no-match-help", "p-autocorrect", "p-fuzzy-fallback", "p-empty-state", "p-homepage"],
            },
            latency_ms=[42, 47, 50, 53, 58, 64, 72, 81, 95, 121, 145],
            request_count=550,
            duration_seconds=20,
            strategy="hybrid-rerank",
            description="Hybrid retrieval with reranker scores applied after fusion.",
            shard_scenarios={
                "1_shard_50k_docs": [35, 38, 42, 49, 55, 61],
                "3_shards_250k_docs": [48, 55, 64, 75, 90, 110],
                "6_shards_1m_docs": [76, 92, 118, 145, 172, 205],
            },
            resilience=resilience,
        ),
        SearchChangeRun(
            name="candidate-bad",
            ranked_results={
                "q-hybrid": ["p-returns-policy", "p-keyword-only", "p-hybrid-guide"],
                "q-vector": ["p-size-chart", "p-bulk-ingest", "p-vector-filter"],
                "q-ingest": [],
                "q-zero": [],
            },
            latency_ms=[90, 130, 160, 210, 270, 340, 410, 490, 560, 710],
            request_count=240,
            duration_seconds=20,
            strategy="regression",
            description="Known-bad run that demonstrates gate failure behavior.",
            shard_scenarios={
                "1_shard_50k_docs": [80, 120, 160, 220, 260],
                "3_shards_250k_docs": [150, 220, 310, 410, 530],
                "6_shards_1m_docs": [260, 390, 540, 730, 900],
            },
            resilience=[result if result.name != "429/backoff" else ScenarioResult(
                name="429/backoff",
                status="fail",
                expected_recovery="Retry with jittered exponential backoff and preserve request budget.",
                observed="Retries stampede immediately and exhaust the budget.",
                gate="No unbounded retry loops; final response must be success or explicit retryable error.",
                evidence="Synthetic 429 sequence never reaches the success response.",
            ) for result in resilience],
        ),
    ]


def default_resilience_matrix() -> list[ScenarioResult]:
    return [
        ScenarioResult("replay", "pass", "Reprocess failed events without duplicates.", "Replay preserves event ids.", "No duplicated chunk or product ids.", "Replay fixture count equals unique output count."),
        ScenarioResult("idempotency", "pass", "Repeated upsert has the same final state.", "Second write is a no-op.", "Hash and version remain stable.", "Content hash stays unchanged."),
        ScenarioResult("429/backoff", "pass", "Retry with jittered exponential backoff and preserve request budget.", "Third attempt succeeds.", "No unbounded retry loops; final response must be success or explicit retryable error.", "Observed attempts: 3."),
        ScenarioResult("partial-cluster degradation", "pass", "Serve degraded lexical or semantic results with warning.", "Semantic failure returns lexical results.", "Partial data beats hard failure, and warning is emitted.", "warning=semantic_unavailable."),
        ScenarioResult("alias rollback", "pass", "Rollback read alias to previous healthy index.", "Alias returns to products_v41.", "Rollback must restore last green alias target.", "alias_before=products_v42 alias_after=products_v41."),
        ScenarioResult("soft-delete merge", "pass", "Merged updates must not resurrect soft-deleted products.", "Deleted sku remains hidden.", "Soft deletes win over stale update events.", "deleted_at is retained after merge."),
    ]


def evaluate_run(cases: Sequence[EsciCase], run: SearchChangeRun, gates: Gates) -> dict[str, object]:
    query_rows = []
    result_sets = []
    ranked_results = resolved_ranked_results(run)
    for case in cases:
        ranked = ranked_results.get(case.query_id, [])
        relevant_ids = {doc_id for doc_id, grade in case.judgments.items() if grade > 0}
        result_sets.append(ranked)
        query_rows.append({
            "query_id": case.query_id,
            "query": case.query,
            "segment": case.segment,
            "result_count": len(ranked),
            "ndcg_at_10": ndcg_at_k(ranked, case.judgments, 10),
            "precision_at_5": precision_at_k(ranked, relevant_ids, 5),
            "mrr_at_10": mrr_at_k(ranked, relevant_ids, 10),
            "recall_at_5": recall_at_k(ranked, relevant_ids, 5),
            "recall_at_10": recall_at_k(ranked, relevant_ids, 10),
            "top_result": ranked[0] if ranked else None,
        })

    relevance = {
        "ndcg_at_10": mean(row["ndcg_at_10"] for row in query_rows),
        "precision_at_5": mean(row["precision_at_5"] for row in query_rows),
        "mrr_at_10": mean(row["mrr_at_10"] for row in query_rows),
        "recall_at_5": mean(row["recall_at_5"] for row in query_rows),
        "recall_at_10": mean(row["recall_at_10"] for row in query_rows),
        "zero_result_rate": zero_result_rate(result_sets),
        "queries": query_rows,
    }
    performance = performance_summary(run)
    resilience = resilience_summary(run.resilience)
    gate_results = evaluate_gates(relevance, performance, resilience, gates)
    return {
        "name": run.name,
        "strategy": run.strategy,
        "description": run.description,
        "ship": all(item["status"] == "pass" for item in gate_results),
        "relevance": relevance,
        "performance": performance,
        "resilience": resilience,
        "gates": gate_results,
        "ranked_results": ranked_results,
        "rrf": {
            "rank_constant": run.rrf_rank_constant,
            "channels": sorted({channel for query_channels in run.channel_results.values() for channel in query_channels}),
        } if run.strategy == "hybrid-rrf" else None,
    }


def performance_summary(run: SearchChangeRun) -> dict[str, object]:
    throughput = run.request_count / run.duration_seconds if run.duration_seconds > 0 else 0.0
    return {
        "p50_latency_ms": percentile(run.latency_ms, 50),
        "p95_latency_ms": percentile(run.latency_ms, 95),
        "p99_latency_ms": percentile(run.latency_ms, 99),
        "throughput_qps": throughput,
        "shard_scenarios": {
            name: {
                "p50_latency_ms": percentile(values, 50),
                "p95_latency_ms": percentile(values, 95),
                "p99_latency_ms": percentile(values, 99),
            }
            for name, values in run.shard_scenarios.items()
        },
    }


def resolved_ranked_results(run: SearchChangeRun) -> dict[str, list[str]]:
    if run.strategy != "hybrid-rrf" or not run.channel_results:
        return run.ranked_results
    return {
        query_id: reciprocal_rank_fusion_ids(channels, k=run.rrf_rank_constant)
        for query_id, channels in run.channel_results.items()
    }


def reciprocal_rank_fusion_ids(channels: dict[str, list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    seen_index = 0
    for channel_name in sorted(channels):
        for rank, doc_id in enumerate(channels[channel_name], start=1):
            if doc_id not in first_seen:
                first_seen[doc_id] = seen_index
                seen_index += 1
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], first_seen[doc_id], doc_id))


def resilience_summary(results: Sequence[ScenarioResult]) -> dict[str, object]:
    rows = [asdict(result) for result in results]
    return {
        "pass_rate": mean(1.0 if row["status"] == "pass" else 0.0 for row in rows),
        "matrix": rows,
    }


def evaluate_gates(relevance: dict[str, object], performance: dict[str, object], resilience: dict[str, object], gates: Gates) -> list[dict[str, object]]:
    checks = [
        minimum_gate("nDCG@10", relevance["ndcg_at_10"], gates.ndcg_at_10),
        minimum_gate("Precision@5", relevance["precision_at_5"], gates.precision_at_5),
        minimum_gate("MRR@10", relevance["mrr_at_10"], gates.mrr_at_10),
        minimum_gate("Recall@10", relevance["recall_at_10"], gates.recall_at_10),
        maximum_gate("Zero-result rate", relevance["zero_result_rate"], gates.zero_result_rate),
        maximum_gate("p95 latency", performance["p95_latency_ms"], gates.p95_latency_ms),
        maximum_gate("p99 latency", performance["p99_latency_ms"], gates.p99_latency_ms),
        minimum_gate("Throughput", performance["throughput_qps"], gates.throughput_qps),
    ]
    for scenario in resilience["matrix"]:
        checks.append({
            "name": f"Resilience: {scenario['name']}",
            "value": scenario["status"],
            "threshold": "pass",
            "status": "pass" if scenario["status"] == "pass" else "fail",
        })
    return checks


def minimum_gate(name: str, value: object, threshold: float) -> dict[str, object]:
    numeric = float(value)
    return {"name": name, "value": numeric, "threshold": threshold, "status": "pass" if numeric >= threshold else "fail"}


def maximum_gate(name: str, value: object, threshold: float) -> dict[str, object]:
    numeric = float(value)
    return {"name": name, "value": numeric, "threshold": threshold, "status": "pass" if numeric <= threshold else "fail"}


def build_report(
    cases: Sequence[EsciCase],
    runs: Sequence[SearchChangeRun],
    gates: Gates,
    comparisons: Sequence[StrategyComparison] | None = None,
) -> dict[str, object]:
    evaluated = [evaluate_run(cases, run, gates) for run in runs]
    comparison_rows = compare_runs(evaluated, comparisons or default_comparisons(evaluated))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "program": "search-quality",
        "esci_scale": {"exact": 3, "substitute": 2, "complement": 1, "irrelevant": 0},
        "gates": asdict(gates),
        "required_strategies": ["baseline-bm25", "hybrid-rrf"],
        "runs": evaluated,
        "comparisons": comparison_rows,
        "decision_summary": decision_summary(evaluated),
    }


def decision_summary(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    shippable = [run["name"] for run in runs if run["ship"]]
    blocked = [run["name"] for run in runs if not run["ship"]]
    return {
        "shippable_changes": shippable,
        "blocked_changes": blocked,
        "recommendation": "ship" if shippable and not blocked else "review_required",
    }


def default_comparisons(runs: Sequence[dict[str, object]]) -> list[StrategyComparison]:
    names = {str(run["name"]) for run in runs}
    if {"baseline-bm25", "hybrid-rrf"}.issubset(names):
        return [StrategyComparison("baseline-bm25", "hybrid-rrf")]
    return []


def compare_runs(runs: Sequence[dict[str, object]], comparisons: Sequence[StrategyComparison]) -> list[dict[str, object]]:
    by_name = {str(run["name"]): run for run in runs}
    rows: list[dict[str, object]] = []
    for comparison in comparisons:
        baseline = by_name.get(comparison.baseline)
        candidate = by_name.get(comparison.candidate)
        if baseline is None or candidate is None:
            rows.append({
                "baseline": comparison.baseline,
                "candidate": comparison.candidate,
                "status": "missing",
            })
            continue
        baseline_relevance = baseline["relevance"]
        candidate_relevance = candidate["relevance"]
        baseline_performance = baseline["performance"]
        candidate_performance = candidate["performance"]
        ndcg_delta = float(candidate_relevance["ndcg_at_10"]) - float(baseline_relevance["ndcg_at_10"])
        recall_delta = float(candidate_relevance["recall_at_10"]) - float(baseline_relevance["recall_at_10"])
        p95_latency_delta = float(candidate_performance["p95_latency_ms"]) - float(baseline_performance["p95_latency_ms"])
        rows.append({
            "baseline": comparison.baseline,
            "candidate": comparison.candidate,
            "status": "pass" if candidate["ship"] and ndcg_delta >= 0 and recall_delta >= 0 else "review",
            "ndcg_at_10_delta": ndcg_delta,
            "recall_at_10_delta": recall_delta,
            "p95_latency_ms_delta": p95_latency_delta,
            "latency_tradeoff": f"{p95_latency_delta:+.1f} ms p95 vs {comparison.baseline}",
        })
    return rows


def markdown_summary(report: dict[str, object]) -> str:
    lines = [
        "# Search Quality Decision Summary",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Decision",
        "",
    ]
    summary = report["decision_summary"]
    lines.append(f"- Recommendation: **{summary['recommendation']}**")
    lines.append(f"- Shippable changes: {', '.join(summary['shippable_changes']) or 'none'}")
    lines.append(f"- Blocked changes: {', '.join(summary['blocked_changes']) or 'none'}")
    lines.append("")
    if report.get("comparisons"):
        lines.extend([
            "## Before/After",
            "",
            "| Baseline | Candidate | nDCG@10 delta | Recall@10 delta | p95 latency delta | Result |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ])
        for comparison in report["comparisons"]:
            if comparison["status"] == "missing":
                lines.append(f"| {comparison['baseline']} | {comparison['candidate']} | n/a | n/a | n/a | missing |")
            else:
                lines.append(
                    f"| {comparison['baseline']} | {comparison['candidate']} | "
                    f"{comparison['ndcg_at_10_delta']:+.3f} | {comparison['recall_at_10_delta']:+.3f} | "
                    f"{comparison['p95_latency_ms_delta']:+.1f} ms | {comparison['status']} |"
                )
        lines.append("")
    for run in report["runs"]:
        lines.extend(run_markdown(run))
    return "\n".join(lines) + "\n"


def run_markdown(run: dict[str, object]) -> list[str]:
    relevance = run["relevance"]
    performance = run["performance"]
    resilience = run["resilience"]
    status = "SHIPS" if run["ship"] else "DO NOT SHIP"
    lines = [
        f"## {run['name']} ({run['strategy']}): {status}",
        "",
        run["description"],
        "",
        "| Gate | Value | Threshold | Result |",
        "| --- | ---: | ---: | --- |",
    ]
    for gate in run["gates"]:
        lines.append(f"| {gate['name']} | {format_value(gate['value'])} | {format_value(gate['threshold'])} | {gate['status']} |")
    lines.extend([
        "",
        "### Why",
        "",
        f"- Relevance: nDCG@10 `{relevance['ndcg_at_10']:.3f}`, Precision@5 `{relevance['precision_at_5']:.3f}`, MRR@10 `{relevance['mrr_at_10']:.3f}`, Recall@10 `{relevance['recall_at_10']:.3f}`, zero-result rate `{relevance['zero_result_rate']:.3f}`.",
        f"- Performance: p50 `{performance['p50_latency_ms']:.1f} ms`, p95 `{performance['p95_latency_ms']:.1f} ms`, p99 `{performance['p99_latency_ms']:.1f} ms`, throughput `{performance['throughput_qps']:.1f} qps`.",
        f"- Resilience: pass rate `{resilience['pass_rate']:.3f}` across replay, idempotency, 429/backoff, partial-cluster degradation, alias rollback, and soft-delete merge scenarios.",
        "",
        "### Recovery Matrix",
        "",
        "| Scenario | Status | Expected recovery | Observed |",
        "| --- | --- | --- | --- |",
    ])
    for scenario in resilience["matrix"]:
        lines.append(f"| {scenario['name']} | {scenario['status']} | {scenario['expected_recovery']} | {scenario['observed']} |")
    lines.append("")
    return lines


def format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def load_cases(path: Path | None) -> list[EsciCase]:
    if path is None:
        return default_esci_cases()
    rows = read_json_records(path)
    cases: dict[str, EsciCase] = {}
    for row in rows:
        query_id = str(row["query_id"])
        document_id = str(row["doc_id"])
        raw_grade = row.get("esci_label", row.get("grade", row.get("judgment", 0)))
        grade = normalize_grade(raw_grade)
        existing = cases.get(query_id)
        judgments = dict(existing.judgments) if existing else {}
        judgments[document_id] = grade
        cases[query_id] = EsciCase(
            query_id=query_id,
            query=str(row.get("query", query_id)),
            judgments=judgments,
            segment=str(row.get("segment", "default")),
        )
    return list(cases.values())


def load_runs(path: Path | None) -> list[SearchChangeRun]:
    if path is None:
        return default_runs()
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = []
    for item in data.get("runs", data):
        raw_resilience = item.get("resilience")
        resilience = default_resilience_matrix() if raw_resilience is None else [
            scenario if isinstance(scenario, ScenarioResult) else ScenarioResult(**scenario)
            for scenario in raw_resilience
        ]
        runs.append(SearchChangeRun(
            name=str(item["name"]),
            ranked_results={str(key): [str(doc_id) for doc_id in value] for key, value in item.get("ranked_results", {}).items()},
            latency_ms=[float(value) for value in item.get("latency_ms", [])],
            request_count=int(item.get("request_count", 0)),
            duration_seconds=float(item.get("duration_seconds", 1)),
            strategy=str(item.get("strategy", "ranked-list")),
            description=str(item.get("description", "")),
            channel_results={
                str(query_id): {
                    str(channel): [str(doc_id) for doc_id in doc_ids]
                    for channel, doc_ids in channels.items()
                }
                for query_id, channels in item.get("channel_results", {}).items()
            },
            rrf_rank_constant=int(item.get("rrf_rank_constant", 60)),
            shard_scenarios={str(key): [float(value) for value in values] for key, values in item.get("shard_scenarios", {}).items()},
            resilience=resilience,
        ))
    return runs


def load_gate_config(path: Path | None) -> tuple[Gates, list[StrategyComparison]]:
    if path is None:
        return Gates(), [StrategyComparison("baseline-bm25", "hybrid-rrf")]
    data = json.loads(path.read_text(encoding="utf-8"))
    gates = Gates(**{key: value for key, value in data.get("gates", {}).items() if key in Gates.__dataclass_fields__})
    comparisons = [
        StrategyComparison(str(item["baseline"]), str(item["candidate"]))
        for item in data.get("comparisons", [])
    ]
    return gates, comparisons


def read_json_records(path: Path) -> list[dict[str, object]]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return list(data.get("judgments", []))


def normalize_grade(value: object) -> int:
    if isinstance(value, int | float):
        return int(value)
    return ESCI_GRADES.get(str(value).strip().upper(), 0)


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline ESCI relevance, performance, and resilience gates.")
    parser.add_argument("--judgments", type=Path, help="Optional ESCI judgments JSON or JSONL.")
    parser.add_argument("--runs", type=Path, help="Optional search run JSON.")
    parser.add_argument("--gate-config", type=Path, default=Path("config/search-quality-gate.json"))
    parser.add_argument("--report-json", type=Path, default=Path("reports/search-quality-report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/search-quality-decision.md"))
    parser.add_argument("--fail-on-gate", action="store_true", help="Exit non-zero when any run fails a gate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases(args.judgments)
    runs = load_runs(args.runs)
    gate_config = args.gate_config if args.gate_config.exists() else None
    gates, comparisons = load_gate_config(gate_config)
    report = build_report(cases, runs, gates, comparisons)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.report_md.write_text(markdown_summary(report), encoding="utf-8")
    if args.fail_on_gate and any(not run["ship"] for run in report["runs"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
