"""Load graded relevance judgments for offline search evaluation."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

LABEL_TO_GRADE = {
    "irrelevant": 0,
    "complement": 1,
    "substitute": 2,
    "exact": 3,
}


def label_to_grade(label: str) -> int:
    try:
        return LABEL_TO_GRADE[label]
    except KeyError as exc:
        raise ValueError(f"Unknown relevance label: {label}") from exc


def load_judgments(path: Path) -> dict[str, dict[str, int]]:
    judgments: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open("r", encoding="utf-8") as judgments_file:
        for line_number, line in enumerate(judgments_file, start=1):
            if not line.strip():
                continue
            row: dict[str, Any] = json.loads(line)
            query = str(row["query"])
            product_id = str(row["product_id"])
            grade = int(row.get("grade", label_to_grade(str(row["label"]))))
            judgments[query][product_id] = grade
    return dict(judgments)