"""Evaluate product-search relevance via the shared ``relevance_eval`` skill.

This is the skill-backed counterpart to ``scripts/evaluate_relevance.py``. The
Precision@k / MRR@k / nDCG@k math comes from the reusable ``relevance_eval``
package (installed via the ``eval`` optional dependency); this script only:

1. loads the checked-in judgment list and converts it to the skill's
   ``{query: {id: grade}}`` shape,
2. loads a thresholds file in the skill's ``"<metric>@<k>"`` form,
3. builds an injected ``search_fn`` from this lab's Elasticsearch client via the
   thin :func:`src.eval.skill_adapter.make_search_fn` adapter,
4. runs the three comparable strategies, writes ``reports/relevance.{json,md}``,
   prints the Markdown, and exits non-zero if the threshold gate fails.

The original ``evaluate_relevance.py`` + ``gate_search_quality.py`` path is left
untouched; this is an additive, shared-skill alternative. Running it requires a
live Elasticsearch with the products index (it is an integration entry point).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from relevance_eval import (  # noqa: E402
    evaluate_thresholds,
    load_thresholds,
    run_evaluation,
    to_json,
    to_markdown,
)

from scripts.create_index import build_client, ensure_reachable  # noqa: E402
from src.eval.skill_adapter import make_search_fn  # noqa: E402
from src.search.strategies import STRATEGY_NAMES  # noqa: E402

DEFAULT_INDEX = "products-v1"
DEFAULT_JUDGMENTS_PATH = PROJECT_ROOT / "data" / "judgments" / "product_search_judgments.json"
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "config" / "eval_thresholds.json"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "reports" / "relevance.json"
DEFAULT_MD_REPORT_PATH = PROJECT_ROOT / "reports" / "relevance.md"
DEFAULT_KS = (1, 3, 5, 10)


def load_judgments_as_map(path: Path) -> dict[str, dict[str, int]]:
    """Convert the lab's judgment file into the skill's ``{query: {id: grade}}``.

    The checked-in ``data/judgments/product_search_judgments.json`` is a list of
    ``{"query": ..., "judgments": {id: grade}}`` objects; the skill wants a flat
    ``{query: {id: grade}}`` mapping (which it normalises to floats internally).
    """
    rows = json.loads(path.read_text(encoding="utf-8"))
    judgments: dict[str, dict[str, int]] = {}
    for index, row in enumerate(rows, start=1):
        query = str(row.get("query", "")).strip()
        if not query:
            raise ValueError(f"Judgment row {index} is missing query")
        raw = row.get("judgments")
        if not isinstance(raw, dict) or not raw:
            raise ValueError(f"Judgment row {index} must include non-empty judgments")
        judgments[query] = {str(doc_id): int(grade) for doc_id, grade in raw.items()}
    return judgments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate product-search relevance via the shared relevance_eval skill."
    )
    parser.add_argument("--index", default=os.getenv("PRODUCT_INDEX", DEFAULT_INDEX))
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS_PATH)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS_PATH)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MD_REPORT_PATH)
    parser.add_argument("--size", type=int, default=10)
    return parser.parse_args()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        client = build_client()
        ensure_reachable(client)

        judgments = load_judgments_as_map(args.judgments)
        thresholds = load_thresholds(str(args.thresholds))
        search_fn = make_search_fn(client, index_name=args.index, size=args.size)

        report: dict[str, Any] = run_evaluation(
            judgments, search_fn, list(STRATEGY_NAMES), ks=DEFAULT_KS
        )
        gate = evaluate_thresholds(report, thresholds)

        _write(args.json_report, to_json(report))
        markdown = to_markdown(report, gate, title="Product Search Relevance (relevance_eval skill)")
        _write(args.markdown_report, markdown)

        print(markdown)
        print(f"\nWrote {args.json_report}")
        print(f"Wrote {args.markdown_report}")
    except Exception as exc:  # noqa: BLE001 - CLI should fail clearly for local use.
        print(f"Relevance evaluation (skill) failed: {exc}", file=sys.stderr)
        return 1

    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
