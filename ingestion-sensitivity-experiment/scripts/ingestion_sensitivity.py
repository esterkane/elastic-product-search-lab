from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
NOISE_TERMS = ["sale", "new", "popular", "premium", "bundle", "limited", "deal", "featured"]


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    category: str
    body: str


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    source_id: str
    title: str
    category: str
    body: str


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    query: str
    judgments: dict[str, int]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_documents(path: Path) -> list[Document]:
    return [Document(**row) for row in read_jsonl(path)]


def load_cases(path: Path) -> list[QueryCase]:
    cases: dict[str, QueryCase] = {}
    for row in read_jsonl(path):
        query_id = str(row["query_id"])
        current = cases.get(query_id)
        judgments = dict(current.judgments) if current else {}
        judgments[str(row["doc_id"])] = int(row["grade"])
        cases[query_id] = QueryCase(query_id=query_id, query=str(row["query"]), judgments=judgments)
    return list(cases.values())


def build_index(documents: list[Document], mode: str, seed: int) -> list[IndexedChunk]:
    rng = random.Random(seed)
    chunks: list[IndexedChunk] = []
    for doc in documents:
        title = doc.title
        category = doc.category
        body = doc.body
        if mode == "missing_metadata":
            title = ""
            category = ""
        elif mode == "noisy_descriptions":
            body = add_noise(body, rng)
        elif mode == "bad_chunking":
            chunks.extend(split_badly(doc))
            continue
        elif mode != "clean":
            raise ValueError(f"unknown perturbation mode: {mode}")
        chunks.append(IndexedChunk(id=doc.id, source_id=doc.id, title=title, category=category, body=body))
    return chunks


def add_noise(body: str, rng: random.Random) -> str:
    distractors = [
        "headphones",
        "battery",
        "boots",
        "waterproof",
        "espresso",
        "grinder",
        "backpack",
        "warranty",
    ]
    noise = " ".join(rng.choice(NOISE_TERMS + distractors) for _ in range(28))
    return f"{noise}. {body} {noise}."


def split_badly(doc: Document) -> list[IndexedChunk]:
    tokens = doc.body.split()
    midpoint = max(1, len(tokens) // 2)
    return [
        IndexedChunk(
            id=f"{doc.id}#chunk-1",
            source_id=doc.id,
            title=doc.title,
            category=doc.category,
            body="",
        ),
        IndexedChunk(
            id=f"{doc.id}#chunk-2",
            source_id=doc.id,
            title="",
            category="",
            body=" ".join(tokens[midpoint:]),
        ),
    ]


def search(query: str, chunks: list[IndexedChunk], limit: int = 5) -> list[str]:
    query_terms = tokenize(query)
    scored = []
    for chunk in chunks:
        score = score_chunk(query_terms, chunk)
        if score > 0:
            scored.append((chunk.source_id, score, chunk.id))
    scored.sort(key=lambda item: (-item[1], item[2]))
    ranked_source_ids = []
    seen = set()
    for source_id, _, _ in scored:
        if source_id in seen:
            continue
        ranked_source_ids.append(source_id)
        seen.add(source_id)
        if len(ranked_source_ids) >= limit:
            break
    return ranked_source_ids


def score_chunk(query_terms: list[str], chunk: IndexedChunk) -> float:
    title_counts = Counter(tokenize(chunk.title))
    body_counts = Counter(tokenize(chunk.body))
    category_terms = set(tokenize(chunk.category))
    score = 0.0
    for term in query_terms:
        score += 4.0 * title_counts[term]
        score += 1.0 * body_counts[term]
        if term in category_terms:
            score += 2.0
    # Penalize very noisy chunks because useful terms are diluted at indexing time.
    unique_terms = len(set(tokenize(chunk.body)))
    if unique_terms > 25:
        score *= 18 / unique_terms
    return score


def evaluate_variant(mode: str, documents: list[Document], cases: list[QueryCase], seed: int) -> dict[str, object]:
    chunks = build_index(documents, mode, seed)
    rows = []
    for case in cases:
        ranked = search(case.query, chunks)
        relevant_ids = {doc_id for doc_id, grade in case.judgments.items() if grade > 0}
        rows.append({
            "query_id": case.query_id,
            "query": case.query,
            "top_result": ranked[0] if ranked else None,
            "ranked_ids": ranked,
            "ndcg_at_5": ndcg_at_k(ranked, case.judgments, 5),
            "mrr_at_5": mrr_at_k(ranked, relevant_ids, 5),
            "precision_at_3": precision_at_k(ranked, relevant_ids, 3),
            "recall_at_5": recall_at_k(ranked, relevant_ids, 5),
        })
    return {
        "name": mode,
        "chunks": len(chunks),
        "metrics": {
            "ndcg_at_5": mean([row["ndcg_at_5"] for row in rows]),
            "mrr_at_5": mean([row["mrr_at_5"] for row in rows]),
            "precision_at_3": mean([row["precision_at_3"] for row in rows]),
            "recall_at_5": mean([row["recall_at_5"] for row in rows]),
        },
        "queries": rows,
    }


def build_report(documents: list[Document], cases: list[QueryCase], seed: int) -> dict[str, object]:
    variants = ["clean", "missing_metadata", "noisy_descriptions", "bad_chunking"]
    runs = [evaluate_variant(variant, documents, cases, seed) for variant in variants]
    clean = runs[0]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "documents": len(documents),
        "variants": runs,
        "deltas_vs_clean": [delta(clean, run) for run in runs[1:]],
        "interpretation": interpret(runs),
    }


def delta(clean: dict[str, object], variant: dict[str, object]) -> dict[str, object]:
    clean_metrics = clean["metrics"]
    variant_metrics = variant["metrics"]
    return {
        "variant": variant["name"],
        "ndcg_at_5_delta": variant_metrics["ndcg_at_5"] - clean_metrics["ndcg_at_5"],
        "mrr_at_5_delta": variant_metrics["mrr_at_5"] - clean_metrics["mrr_at_5"],
        "precision_at_3_delta": variant_metrics["precision_at_3"] - clean_metrics["precision_at_3"],
        "recall_at_5_delta": variant_metrics["recall_at_5"] - clean_metrics["recall_at_5"],
    }


def interpret(runs: list[dict[str, object]]) -> str:
    deltas = [delta(runs[0], run) for run in runs[1:]]
    worst = min(deltas, key=lambda item: item["ndcg_at_5_delta"])
    if worst["variant"] == "missing_metadata":
        reason = "title and category loss removes the strongest lexical signal."
    elif worst["variant"] == "bad_chunking":
        reason = "bad chunk boundaries split context and create weaker fragments."
    else:
        reason = "description noise dilutes useful terms with high-frequency junk."
    return f"{worst['variant']} caused the largest nDCG@5 drop because {reason}"


def markdown_report(report: dict[str, object]) -> str:
    lines = [
        "# Ingestion Sensitivity Experiment",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Seed: `{report['seed']}`",
        f"Documents: `{report['documents']}`",
        "",
        "## Variant Metrics",
        "",
        "| Variant | Chunks | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in report["variants"]:
        metrics = run["metrics"]
        lines.append(
            f"| {run['name']} | {run['chunks']} | {metrics['ndcg_at_5']:.3f} | {metrics['mrr_at_5']:.3f} | {metrics['precision_at_3']:.3f} | {metrics['recall_at_5']:.3f} |"
        )
    lines.extend([
        "",
        "## Deltas Vs Clean",
        "",
        "| Variant | nDCG@5 delta | MRR@5 delta | Precision@3 delta | Recall@5 delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for row in report["deltas_vs_clean"]:
        lines.append(
            f"| {row['variant']} | {row['ndcg_at_5_delta']:+.3f} | {row['mrr_at_5_delta']:+.3f} | {row['precision_at_3_delta']:+.3f} | {row['recall_at_5_delta']:+.3f} |"
        )
    lines.extend(["", "## Interpretation", "", str(report["interpretation"]), "", "## Per Query Effects", ""])
    for run in report["variants"]:
        lines.extend([
            f"### {run['name']}",
            "",
            "| Query | Top result | nDCG@5 | Ranked ids |",
            "| --- | --- | ---: | --- |",
        ])
        for row in run["queries"]:
            lines.append(
                f"| {row['query_id']} | {row['top_result']} | {row['ndcg_at_5']:.3f} | {', '.join(row['ranked_ids'])} |"
            )
        lines.append("")
    return "\n".join(lines)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    dcg = 0.0
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        gain = relevance.get(doc_id, 0)
        dcg += (2**gain - 1) / math.log2(index + 1)
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**gain - 1) / math.log2(index + 1) for index, gain in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0


def mrr_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    for index, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in relevant_ids:
            return 1.0 / index
    return 0.0


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    return len(set(ranked_ids[:k]) & relevant_ids) / k if k else 0.0


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure retrieval sensitivity to deterministic ingestion defects.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument("--judgments", type=Path, default=Path("data/judgments.jsonl"))
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--report-json", type=Path, default=Path("reports/ingestion-sensitivity-report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/ingestion-sensitivity-report.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(load_documents(args.corpus), load_cases(args.judgments), args.seed)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.report_md.write_text(markdown_report(report), encoding="utf-8")
    print(f"wrote {args.report_json} and {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
