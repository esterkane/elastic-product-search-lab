from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(values: list[float]) -> list[float]:
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [1.0 for _ in values]
    return [(value - minimum) / (maximum - minimum) for value in values]


def explain_query(query: dict[str, object], config: dict[str, object]) -> dict[str, object]:
    results = query["results"]
    lexical_norm = normalize([float(result["lexical_score"]) for result in results])
    semantic_norm = normalize([float(result["semantic_score"]) for result in results])
    lexical_weight = float(config["lexical_weight"])
    semantic_weight = float(config["semantic_weight"])
    explained_results = []
    for result, lexical, semantic in zip(results, lexical_norm, semantic_norm, strict=True):
        metadata = float(result["metadata_score"])
        combined = ((lexical_weight * lexical) + (semantic_weight * semantic)) * metadata
        explained_results.append({
            **result,
            "normalized_lexical": lexical,
            "normalized_semantic": semantic,
            "combined_score": combined,
            "explanation": (
                f"min_max lexical={lexical:.3f}, min_max semantic={semantic:.3f}, "
                f"weighted_mean={((lexical_weight * lexical) + (semantic_weight * semantic)):.3f}, "
                f"metadata_multiplier={metadata:.2f}"
            ),
        })
    explained_results.sort(key=lambda result: (-result["combined_score"], result["doc_id"]))
    expected_rank = next(
        (index for index, result in enumerate(explained_results, start=1) if result["doc_id"] == query["expected_page"]),
        None,
    )
    return {
        "query_id": query["query_id"],
        "query": query["query"],
        "expected_page": query["expected_page"],
        "expected_rank": expected_rank,
        "failure_category": query["failure_category"],
        "recommended_fix": query["recommended_fix"],
        "top_results": explained_results,
    }


def build_report(fixture: dict[str, object]) -> dict[str, object]:
    config = fixture["hybrid_config"]
    queries = [explain_query(query, config) for query in fixture["queries"]]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "hybrid_config": config,
        "queries": queries,
        "failure_summary": dict(Counter(query["failure_category"] for query in queries)),
        "verification": {
            "explain_path": "OpenSearch 2.19+ hybrid explain requires ?explain=true and a hybrid_score_explanation response processor.",
            "captured_fields": ["normalized_lexical", "normalized_semantic", "combined_score", "metadata_score"],
        },
    }


def markdown_report(report: dict[str, object]) -> str:
    config = report["hybrid_config"]
    lines = [
        "# Hybrid Explain Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Hybrid Configuration",
        "",
        f"- Normalization: `{config['normalization']}`",
        f"- Combination: `{config['combination']}`",
        f"- Lexical weight: `{config['lexical_weight']}`",
        f"- Semantic weight: `{config['semantic_weight']}`",
        f"- Top-k inspected: `{config['top_k']}`",
        "",
        "## Failure Summary",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in sorted(report["failure_summary"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend([
        "",
        "## Hard Query Explanations",
        "",
    ])
    for query in report["queries"]:
        lines.extend([
            f"### {query['query_id']}: {query['query']}",
            "",
            f"- Expected page: `{query['expected_page']}`",
            f"- Expected rank: `{query['expected_rank']}`",
            f"- Failure category: `{query['failure_category']}`",
            f"- Recommended fix: {query['recommended_fix']}",
            "",
            "| Rank | Doc | Lexical raw | Semantic raw | Lexical norm | Semantic norm | Metadata | Combined | Explanation |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ])
        for rank, result in enumerate(query["top_results"], start=1):
            lines.append(
                f"| {rank} | {result['doc_id']} | {result['lexical_score']:.3f} | {result['semantic_score']:.3f} | "
                f"{result['normalized_lexical']:.3f} | {result['normalized_semantic']:.3f} | "
                f"{result['metadata_score']:.2f} | {result['combined_score']:.3f} | {result['explanation']} |"
            )
        lines.append("")
    lines.extend([
        "## Troubleshooting Use",
        "",
        "Use this report when a hybrid result looks wrong but the top-k set still contains the expected document. The breakdown separates missing lexical vocabulary, weak semantic similarity, score-fusion imbalance, and metadata penalties so fixes can target the failing stage.",
        "",
        "## Verification Notes",
        "",
        "OpenSearch hybrid explain supports `explain=true` on hybrid searches when the search pipeline includes the `hybrid_score_explanation` response processor. The fixture mirrors those explain fields with normalized lexical score, normalized semantic score, combination result, and metadata multiplier.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a human-readable hybrid retrieval explain report.")
    parser.add_argument("--input", type=Path, default=Path("data/hard_queries.json"))
    parser.add_argument("--report-json", type=Path, default=Path("reports/hybrid-explain-report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/hybrid-explain-report.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(load_fixture(args.input))
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.report_md.write_text(markdown_report(report), encoding="utf-8")
    print(f"wrote {args.report_json} and {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
