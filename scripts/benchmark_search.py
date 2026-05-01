"""Local search latency benchmark for product-search strategies."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.embeddings.embedder import get_embedder  # noqa: E402
from src.search.hybrid_search import (  # noqa: E402
    baseline_lexical_query,
    boosted_lexical_query,
    extract_ids,
    hybrid_rrf_search,
)

DEFAULT_INDEX = "products-v1"
DEFAULT_QUERIES = [
    "wireless mouse",
    "noise cancelling headphones",
    "usb c charger",
    "running shoes waterproof",
    "coffee maker",
    "yoga mat",
    "office chair",
    "stainless steel bottle",
]
DEFAULT_OUTPUT_JSON = PROJECT_ROOT / "data" / "generated" / "performance_report.json"
DEFAULT_OUTPUT_MD = PROJECT_ROOT / "examples" / "performance_report.md"


@dataclass(frozen=True)
class BenchmarkAttempt:
    strategy: str
    query: str
    latency_ms: float
    success: bool
    timed_out: bool = False
    error: str | None = None
    result_count: int = 0


@dataclass(frozen=True)
class BenchmarkSummary:
    strategy: str
    count: int
    success_count: int
    error_count: int
    timeout_count: int
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    error_rate: float
    timeout_rate: float


def percentile(values: list[float], percentile_rank: float) -> float:
    if not values:
        return 0.0
    if percentile_rank <= 0:
        return min(values)
    if percentile_rank >= 100:
        return max(values)

    ordered = sorted(values)
    position = (len(ordered) - 1) * (percentile_rank / 100.0)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_attempts(attempts: list[BenchmarkAttempt]) -> list[BenchmarkSummary]:
    summaries: list[BenchmarkSummary] = []
    for strategy in sorted({attempt.strategy for attempt in attempts}):
        strategy_attempts = [attempt for attempt in attempts if attempt.strategy == strategy]
        successful_latencies = [attempt.latency_ms for attempt in strategy_attempts if attempt.success]
        count = len(strategy_attempts)
        error_count = sum(1 for attempt in strategy_attempts if not attempt.success)
        timeout_count = sum(1 for attempt in strategy_attempts if attempt.timed_out)
        summaries.append(
            BenchmarkSummary(
                strategy=strategy,
                count=count,
                success_count=count - error_count,
                error_count=error_count,
                timeout_count=timeout_count,
                p50=percentile(successful_latencies, 50),
                p95=percentile(successful_latencies, 95),
                p99=percentile(successful_latencies, 99),
                min=min(successful_latencies) if successful_latencies else 0.0,
                max=max(successful_latencies) if successful_latencies else 0.0,
                error_rate=error_count / count if count else 0.0,
                timeout_rate=timeout_count / count if count else 0.0,
            )
        )
    return summaries


def is_timeout_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "timeout" in text or "timed out" in text


def run_timed_query(strategy: str, query: str, search_fn: Any) -> BenchmarkAttempt:
    started = time.perf_counter()
    try:
        product_ids = list(search_fn())
        latency_ms = (time.perf_counter() - started) * 1000
        return BenchmarkAttempt(strategy=strategy, query=query, latency_ms=latency_ms, success=True, result_count=len(product_ids))
    except Exception as exc:  # noqa: BLE001 - benchmark should keep running and report failures.
        latency_ms = (time.perf_counter() - started) * 1000
        return BenchmarkAttempt(
            strategy=strategy,
            query=query,
            latency_ms=latency_ms,
            success=False,
            timed_out=is_timeout_error(exc),
            error=exc.__class__.__name__,
        )


def direct_lexical_search(client: Any, index_name: str, query: str, size: int, boosted: bool, timeout_seconds: float) -> list[str]:
    body = boosted_lexical_query(query, size) if boosted else baseline_lexical_query(query, size)
    response = client.options(request_timeout=timeout_seconds).search(index=index_name, **body)
    return extract_ids(response)


def index_has_embeddings(client: Any, index_name: str) -> bool:
    response = client.search(index=index_name, size=0, query={"exists": {"field": "embedding"}})
    return int(response.get("hits", {}).get("total", {}).get("value", 0)) > 0


def run_benchmark(
    client: Any,
    index_name: str,
    queries: list[str],
    size: int,
    repeat: int,
    timeout_seconds: float,
    include_hybrid: bool,
    provider: str,
    model: str,
) -> tuple[list[BenchmarkAttempt], list[BenchmarkSummary]]:
    attempts: list[BenchmarkAttempt] = []
    embedder = get_embedder(provider, model) if include_hybrid else None

    for _ in range(repeat):
        for query in queries:
            attempts.append(
                run_timed_query(
                    "baseline_lexical",
                    query,
                    lambda q=query: direct_lexical_search(client, index_name, q, size, boosted=False, timeout_seconds=timeout_seconds),
                )
            )
            attempts.append(
                run_timed_query(
                    "boosted_lexical",
                    query,
                    lambda q=query: direct_lexical_search(client, index_name, q, size, boosted=True, timeout_seconds=timeout_seconds),
                )
            )
            if embedder is not None:
                attempts.append(
                    run_timed_query(
                        "hybrid_rrf",
                        query,
                        lambda q=query: hybrid_rrf_search(client, index_name, q, embedder, size),
                    )
                )

    return attempts, summarize_attempts(attempts)


def write_reports(attempts: list[BenchmarkAttempt], summaries: list[BenchmarkSummary], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at_unix": time.time(),
        "summary": [asdict(summary) for summary in summaries],
        "attempts": [asdict(attempt) for attempt in attempts],
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Search Performance Report",
        "",
        "Local benchmark results for product-search strategies. Latency values are milliseconds.",
        "",
        "| Strategy | Count | Success | Error Rate | Timeout Rate | p50 | p95 | p99 | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary.strategy} | {summary.count} | {summary.success_count} | "
            f"{summary.error_rate:.3f} | {summary.timeout_rate:.3f} | {summary.p50:.2f} | "
            f"{summary.p95:.2f} | {summary.p99:.2f} | {summary.min:.2f} | {summary.max:.2f} |"
        )
    lines.extend(
        [
            "",
            "Tail latency should be reviewed alongside relevance metrics. A relevance gain that doubles p99 latency may be a regression for real users.",
        ]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local product search latency.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--hybrid", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--provider", choices=["auto", "sentence-transformers", "hash"], default="hash")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        has_embeddings = index_has_embeddings(client, args.index)
        include_hybrid = args.hybrid == "always" or (args.hybrid == "auto" and has_embeddings)
        attempts, summaries = run_benchmark(
            client=client,
            index_name=args.index,
            queries=list(args.queries),
            size=args.size,
            repeat=args.repeat,
            timeout_seconds=args.timeout_seconds,
            include_hybrid=include_hybrid,
            provider=args.provider,
            model=args.model,
        )
        write_reports(attempts, summaries, args.output, args.markdown_output)
        for summary in summaries:
            print(
                f"{summary.strategy}: p50={summary.p50:.2f}ms p95={summary.p95:.2f}ms "
                f"p99={summary.p99:.2f}ms error_rate={summary.error_rate:.3f} timeout_rate={summary.timeout_rate:.3f}"
            )
        if args.hybrid == "auto" and not include_hybrid:
            print("hybrid_rrf skipped because no embedding field exists in the index.")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly.
        print(f"Search benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
