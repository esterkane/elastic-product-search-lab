"""Prepare local JSONL files from an Amazon ESCI dataset copy."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset_etl import stable_availability, stable_price, write_standard_outputs  # noqa: E402

DEFAULT_PRODUCTS_OUT = PROJECT_ROOT / "data" / "generated" / "esci_products.jsonl"
DEFAULT_JUDGMENTS_OUT = PROJECT_ROOT / "data" / "generated" / "esci_judgments.jsonl"
DEFAULT_FULL_PRODUCTS_OUT = PROJECT_ROOT / "data" / "generated" / "esci_full_products.jsonl"
DEFAULT_FULL_JUDGMENTS_OUT = PROJECT_ROOT / "data" / "generated" / "esci_full_judgments.jsonl"

LABEL_TO_GRADE = {
    "e": 3,
    "exact": 3,
    "s": 2,
    "substitute": 2,
    "c": 1,
    "complement": 1,
    "i": 0,
    "irrelevant": 0,
}


def map_esci_label(label: str) -> int:
    normalized = label.strip().lower()
    if normalized not in LABEL_TO_GRADE:
        raise ValueError(f"Unknown ESCI label: {label}")
    return LABEL_TO_GRADE[normalized]


def read_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".parquet":
        try:
            import pandas as pd  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Reading parquet requires pandas and pyarrow installed in the Python environment.") from exc
        return pd.read_parquet(path).to_dict(orient="records")
    raise ValueError(f"Unsupported input format: {path}")


def english_only(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        locale = record.get("product_locale")
        if locale is None or str(locale).lower() in {"us", "en_us", "en-us"}:
            filtered.append(record)
    return filtered


def sample_queries(examples: list[dict[str, Any]], max_queries: int, seed: int) -> list[str]:
    queries = sorted({str(row["query"]) for row in examples if row.get("query")})
    if len(queries) <= max_queries:
        return queries
    rng = random.Random(seed)
    return sorted(rng.sample(queries, max_queries))


def transform_product(record: dict[str, Any], *, seed: int = 7) -> dict[str, Any]:
    title = str(record.get("product_title") or record.get("title") or "Untitled product")
    description_parts = [
        str(record.get("product_description") or record.get("description") or ""),
        str(record.get("product_bullet_point") or ""),
    ]
    description = " ".join(part for part in description_parts if part).strip()
    brand = str(record.get("product_brand") or record.get("brand") or "unknown")
    color = str(record.get("product_color") or "").strip()
    locale = str(record.get("product_locale") or "us")

    product_id = str(record["product_id"])
    return {
        "product_id": product_id,
        "title": title,
        "description": description,
        "brand": brand,
        "category": "ESCI Imported Products",
        "attributes": {
            "product_color": color,
            "product_locale": locale,
            "source_dataset": "amazon_esci",
            "synthetic_price": True,
            "synthetic_inventory": True,
        },
        "price": stable_price(product_id, seed=seed),
        "currency": "USD",
        "availability": stable_availability(product_id, seed=seed),
        "popularity_score": 0.0,
        "seller_id": "esci-dataset",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def transform_judgment(record: dict[str, Any]) -> dict[str, Any]:
    label = str(record.get("esci_label") or record.get("label") or "")
    grade = map_esci_label(label)
    return {
        "query": str(record["query"]),
        "product_id": str(record["product_id"]),
        "label": label,
        "grade": grade,
    }


def prepare_esci_dataset(
    products: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    max_queries: int,
    max_products: int,
    seed: int = 7,
    full: bool = False,
    all_locales: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scoped_examples = list(examples) if all_locales else english_only(examples)
    scoped_products = list(products) if all_locales else english_only(products)

    if full:
        selected_examples = [row for row in scoped_examples if row.get("query") and row.get("product_id")]
    else:
        selected_queries = set(sample_queries(scoped_examples, max_queries, seed))
        selected_examples = [row for row in scoped_examples if str(row.get("query")) in selected_queries]

    selected_product_ids = {str(row["product_id"]) for row in selected_examples if row.get("product_id")}
    product_lookup = {str(row["product_id"]): row for row in scoped_products if row.get("product_id")}
    selected_products = [product_lookup[product_id] for product_id in sorted(selected_product_ids) if product_id in product_lookup]
    if not full:
        selected_products = selected_products[:max_products]
    kept_product_ids = {str(row["product_id"]) for row in selected_products}
    selected_examples = [row for row in selected_examples if str(row.get("product_id")) in kept_product_ids]

    return [transform_product(row, seed=seed) for row in selected_products], [transform_judgment(row) for row in selected_examples]


def prepare_esci_sample(
    products: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    max_queries: int,
    max_products: int,
    seed: int = 7,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return prepare_esci_dataset(
        products,
        examples,
        max_queries=max_queries,
        max_products=max_products,
        seed=seed,
        full=False,
        all_locales=False,
    )


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare local product and judgment JSONL files from Amazon ESCI files.")
    parser.add_argument("--products", type=Path, required=True, help="Path to ESCI products parquet, CSV, or JSONL file.")
    parser.add_argument("--examples", type=Path, required=True, help="Path to ESCI examples parquet, CSV, or JSONL file.")
    parser.add_argument("--full", action="store_true", help="Prepare every matching local record instead of a capped sample.")
    parser.add_argument("--all-locales", action="store_true", help="Keep every locale instead of filtering to English/US records.")
    parser.add_argument("--max-queries", type=int, default=100)
    parser.add_argument("--max-products", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--products-out", type=Path)
    parser.add_argument("--judgments-out", type=Path)
    parser.add_argument(
        "--standard-output-dir",
        type=Path,
        default=None,
        help="Also write shared product_snapshots/events/judgments JSONL files to this directory.",
    )
    args = parser.parse_args()
    if args.products_out is None:
        args.products_out = DEFAULT_FULL_PRODUCTS_OUT if args.full else DEFAULT_PRODUCTS_OUT
    if args.judgments_out is None:
        args.judgments_out = DEFAULT_FULL_JUDGMENTS_OUT if args.full else DEFAULT_JUDGMENTS_OUT
    return args


def main() -> int:
    args = parse_args()
    try:
        products, judgments = prepare_esci_dataset(
            read_records(args.products),
            read_records(args.examples),
            max_queries=args.max_queries,
            max_products=args.max_products,
            seed=args.seed,
            full=args.full,
            all_locales=args.all_locales,
        )
        write_jsonl(args.products_out, products)
        write_jsonl(args.judgments_out, judgments)
        print(f"Wrote {len(products)} products to {args.products_out}")
        print(f"Wrote {len(judgments)} judgments to {args.judgments_out}")
        if args.standard_output_dir is not None:
            outputs = write_standard_outputs(
                output_dir=args.standard_output_dir,
                products=products,
                judgments=judgments,
                dataset="esci",
            )
            for name, path in outputs.items():
                print(f"Wrote {name} to {path}")
    except Exception as exc:  # noqa: BLE001 - CLI should print a clear local failure.
        print(f"ESCI sample preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
