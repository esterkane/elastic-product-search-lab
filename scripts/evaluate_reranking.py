"""Evaluate optional reranking quality and latency tradeoffs."""

from __future__ import annotations

import argparse
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
from scripts.benchmark_search import index_has_embeddings, percentile  # noqa: E402
from src.embeddings.embedder import get_embedder  # noqa: E402
from src.evaluation.judgments import load_judgments  # noqa: E402
from src.evaluation.metrics import ndcg_at_k, precision_at_k, reciprocal_rank  # noqa: E402
from src.search.hybrid_search import baseline_lexical_query, boosted_lexical_query, hybrid_rrf_search  # noqa: E402
from src.search.rerank import PlaceholderTextSimilarityReranker, SearchResult, metric_delta, rerank_window  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS = PROJECT_ROOT / "data" / "sample" / "judgments.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "examples" / "reranking_report.md"


@dataclass(frozen=True)
class RerankingRow:
    query: str
    strategy: str
    before_ndcg_at_10: float
    after_ndcg_at_10: float
    delta_ndcg_at_10: float
    before_mrr: float
    after_mrr: float
    delta_mrr: float
    before_precision_at_10: float
    after_precision_at_10: float
    delta_precision_at_10: float
    first_stage_latency_ms: float
    rerank_latency_ms: float
    total_latency_ms: float


def hit_to_search_result(hit: dict[str, Any], fallback_id: str | None = None, fallback_score: float = 0.0) -> SearchResult:
    source = hit.get("_source", {}) or {}
    product_id = str(hit.get("_id") or fallback_id or source.get("product_id"))
    return SearchResult(
        product_id=product_id,
        score=float(hit.get("_score") or fallback_score),
        title=str(source.get("title", "")),
        brand=str(source.get("brand", "")),
        category=str(source.get("category", "")),
        description=str(source.get("description", "")),
        catalog_text=str(source.get("catalog_text", "")),
        source=source,
    )


def lexical_candidates(client: Any, index_name: str, query: str, size: int, boosted: bool) -> list[SearchResult]:
    body = boosted_lexical_query(query, size) if boosted else baseline_lexical_query(query, size)
    response = client.search(index=index_name, **body)
    return [hit_to_search_result(hit) for hit in response.get("hits", {}).get("hits", [])]


def fetch_candidates_by_ids(client: Any, index_name: str, product_ids: list[str]) -> list[SearchResult]:
    if not product_ids:
        return []
    response = client.mget(index=index_name, ids=product_ids)
    docs_by_id = {str(doc.get("_id")): doc for doc in response.get("docs", []) if doc.get("found", False)}
    candidates: list[SearchResult] = []
    for position, product_id in enumerate(product_ids):
        doc = docs_by_id.get(product_id)
        if doc is None:
            continue
        candidates.append(hit_to_search_result(doc, fallback_id=product_id, fallback_score=1.0 / (position + 1)))
    return candidates


def hybrid_candidates(client: Any, index_name: str, query: str, size: int, embedder: Any) -> list[SearchResult]:
    product_ids = hybrid_rrf_search(client, index_name, query, embedder, size=size)
    return fetch_candidates_by_ids(client, index_name, product_ids)


def score(product_ids: list[str], judgments: dict[str, int], k: int) -> dict[str, float]:
    return {
        "precision_at_10": precision_at_k(product_ids, judgments, k),
        "mrr": reciprocal_rank(product_ids, judgments),
        "ndcg_at_10": ndcg_at_k(product_ids, judgments, k),
    }


def evaluate_strategy(
    client: Any,
    index_name: str,
    query: str,
    judgments: dict[str, int],
    strategy: str,
    candidate_size: int,
    rerank_size: int,
    k: int,
    embedder: Any | None,
) -> RerankingRow:
    started = time.perf_counter()
    if strategy == "baseline_lexical":
        candidates = lexical_candidates(client, index_name, query, candidate_size, boosted=False)
    elif strategy == "boosted_lexical":
        candidates = lexical_candidates(client, index_name, query, candidate_size, boosted=True)
    elif strategy == "hybrid_rrf" and embedder is not None:
        candidates = hybrid_candidates(client, index_name, query, candidate_size, embedder)
    else:
        raise ValueError(f"Unsupported reranking strategy: {strategy}")
    first_stage_latency_ms = (time.perf_counter() - started) * 1000

    before_ids = [candidate.product_id for candidate in candidates]
    before = score(before_ids, judgments, k)

    reranker = PlaceholderTextSimilarityReranker()
    rerank_started = time.perf_counter()
    reranked = rerank_window(query, candidates, reranker, rerank_size)
    rerank_latency_ms = (time.perf_counter() - rerank_started) * 1000
    after = score([candidate.product_id for candidate in reranked], judgments, k)
    delta = metric_delta(before, after)

    return RerankingRow(
        query=query,
        strategy=strategy,
        before_ndcg_at_10=before["ndcg_at_10"],
        after_ndcg_at_10=after["ndcg_at_10"],
        delta_ndcg_at_10=delta["ndcg_at_10"],
        before_mrr=before["mrr"],
        after_mrr=after["mrr"],
        delta_mrr=delta["mrr"],
        before_precision_at_10=before["precision_at_10"],
        after_precision_at_10=after["precision_at_10"],
        delta_precision_at_10=delta["precision_at_10"],
        first_stage_latency_ms=first_stage_latency_ms,
        rerank_latency_ms=rerank_latency_ms,
        total_latency_ms=first_stage_latency_ms + rerank_latency_ms,
    )


def write_markdown(rows: list[RerankingRow], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reranking Report",
        "",
        "Optional local reranking comparison using the deterministic placeholder reranker. This is a workflow demonstration, not an ML quality claim.",
        "",
        "| Query | Strategy | nDCG@10 Before | nDCG@10 After | Delta | First Stage ms | Rerank ms | Total ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.query} | {row.strategy} | {row.before_ndcg_at_10:.3f} | {row.after_ndcg_at_10:.3f} | "
            f"{row.delta_ndcg_at_10:+.3f} | {row.first_stage_latency_ms:.1f} | {row.rerank_latency_ms:.1f} | {row.total_latency_ms:.1f} |"
        )
    if rows:
        before_totals = [row.first_stage_latency_ms for row in rows]
        after_totals = [row.total_latency_ms for row in rows]
        before_p95 = percentile(before_totals, 95)
        after_p95 = percentile(after_totals, 95)
        ndcg_delta = mean(row.delta_ndcg_at_10 for row in rows)
        lines.extend(
            [
                "",
                f"Average nDCG@10 delta: {ndcg_delta:+.3f}",
                f"p95 latency before rerank: {before_p95:.1f} ms",
                f"p95 latency after rerank: {after_p95:.1f} ms",
            ]
        )
        if ndcg_delta > 0 and after_p95 > before_p95:
            lines.append("Warning: relevance improved while p95 latency worsened. Review whether the tradeoff is acceptable.")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate optional reranking on top of first-stage retrieval.")
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    parser.add_argument("--candidate-size", type=int, default=100)
    parser.add_argument("--rerank-size", type=int, default=20)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--provider", choices=["auto", "sentence-transformers", "hash"], default="hash")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--hybrid", choices=["auto", "always", "never"], default="auto", help="Include hybrid_rrf when embeddings exist, always, or never.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = build_client()
    try:
        ensure_reachable(client)
        judgments_by_query = load_judgments(args.judgments)
        strategies = ["baseline_lexical", "boosted_lexical"]
        include_hybrid = args.hybrid == "always" or (args.hybrid == "auto" and index_has_embeddings(client, args.index))
        embedder = None
        if include_hybrid:
            strategies.append("hybrid_rrf")
            embedder = get_embedder(args.provider, args.model)

        rows: list[RerankingRow] = []
        for query, judgments in sorted(judgments_by_query.items()):
            for strategy in strategies:
                row = evaluate_strategy(
                    client=client,
                    index_name=args.index,
                    query=query,
                    judgments=judgments,
                    strategy=strategy,
                    candidate_size=args.candidate_size,
                    rerank_size=args.rerank_size,
                    k=args.k,
                    embedder=embedder,
                )
                rows.append(row)
                print(
                    f"{query} [{strategy}]: nDCG@10 {row.before_ndcg_at_10:.3f}->{row.after_ndcg_at_10:.3f} "
                    f"delta={row.delta_ndcg_at_10:+.3f} latency_ms {row.first_stage_latency_ms:.1f}->{row.total_latency_ms:.1f}"
                )

        write_markdown(rows, args.output)
        if rows:
            before_p95 = percentile([row.first_stage_latency_ms for row in rows], 95)
            after_p95 = percentile([row.total_latency_ms for row in rows], 95)
            ndcg_delta = mean(row.delta_ndcg_at_10 for row in rows)
            print(f"aggregate nDCG@10 delta={ndcg_delta:+.3f}")
            print(f"p95 latency delta={after_p95 - before_p95:+.1f}ms")
            if ndcg_delta > 0 and after_p95 > before_p95:
                print("WARNING: relevance improved but p95 latency worsened.")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly.
        print(f"Reranking evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
