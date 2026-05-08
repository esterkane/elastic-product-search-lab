from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingestion_sensitivity import build_index, build_report, load_cases, load_documents


def test_perturbations_are_deterministic_by_seed() -> None:
    documents = load_documents(ROOT / "data" / "corpus.jsonl")

    first = build_index(documents, "noisy_descriptions", seed=30)
    second = build_index(documents, "noisy_descriptions", seed=30)
    other = build_index(documents, "noisy_descriptions", seed=31)

    assert first == second
    assert first != other


def test_report_compares_variants_against_clean() -> None:
    documents = load_documents(ROOT / "data" / "corpus.jsonl")
    cases = load_cases(ROOT / "data" / "judgments.jsonl")
    report = build_report(documents, cases, seed=30)

    variants = [run["name"] for run in report["variants"]]
    assert variants == ["clean", "missing_metadata", "noisy_descriptions", "bad_chunking"]
    assert len(report["deltas_vs_clean"]) == 3
    assert any(row["ndcg_at_5_delta"] < 0 for row in report["deltas_vs_clean"])
    assert "largest nDCG@5 drop" in report["interpretation"]
