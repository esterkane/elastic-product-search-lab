from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_hybrid_explain import build_report, load_fixture, markdown_report


def test_report_distinguishes_required_failure_categories() -> None:
    report = build_report(load_fixture(ROOT / "data" / "hard_queries.json"))
    categories = {query["failure_category"] for query in report["queries"]}

    assert {"lexical_miss", "semantic_miss", "fusion_issue", "metadata_issue"}.issubset(categories)
    assert report["failure_summary"]["no_failure"] == 1


def test_markdown_includes_score_breakdown_and_fixes() -> None:
    report = build_report(load_fixture(ROOT / "data" / "hard_queries.json"))
    markdown = markdown_report(report)

    assert "Lexical norm" in markdown
    assert "Semantic norm" in markdown
    assert "metadata_multiplier" in markdown
    assert "Recommended fix" in markdown
