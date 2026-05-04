"""Prepare small deterministic Olist product/review/event samples."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset_etl import (  # noqa: E402
    as_float,
    popularity_from_counts,
    read_records,
    stable_availability,
    stable_price,
    write_standard_outputs,
)

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "olist"


def prepare_olist_sample(
    *,
    products: list[dict[str, Any]],
    order_items: list[dict[str, Any]] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    max_products: int = 100,
    seed: int = 17,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    order_items = order_items or []
    reviews = reviews or []
    order_product: dict[str, str] = {}
    price_by_product: dict[str, list[float]] = defaultdict(list)
    seller_by_product: dict[str, Counter[str]] = defaultdict(Counter)
    sales_counts: Counter[str] = Counter()
    for row in order_items:
        product_id = str(row.get("product_id") or "")
        if not product_id:
            continue
        order_product[str(row.get("order_id") or "")] = product_id
        sales_counts[product_id] += 1
        price_by_product[product_id].append(as_float(row.get("price"), 0))
        seller = str(row.get("seller_id") or "olist-unknown-seller")
        seller_by_product[product_id][seller] += 1

    review_scores: dict[str, list[float]] = defaultdict(list)
    for row in reviews:
        product_id = order_product.get(str(row.get("order_id") or ""))
        if product_id:
            review_scores[product_id].append(as_float(row.get("review_score"), 0))

    selected_raw = sorted(
        [row for row in products if row.get("product_id")],
        key=lambda row: (-sales_counts[str(row["product_id"])], str(row["product_id"])),
    )[:max_products]

    transformed: list[dict[str, Any]] = []
    for row in selected_raw:
        product_id = str(row["product_id"])
        category = str(row.get("product_category_name") or "Olist Imported Products")
        title = category.replace("_", " ").title()
        prices = [price for price in price_by_product[product_id] if price > 0]
        synthetic_price = not prices
        product_reviews = review_scores[product_id]
        review_count = len(product_reviews)
        average_rating = round(sum(product_reviews) / review_count, 3) if review_count else 0.0
        seller = seller_by_product[product_id].most_common(1)[0][0] if seller_by_product[product_id] else "olist-dataset"
        transformed.append(
            {
                "product_id": f"OLIST-{product_id}",
                "title": title,
                "description": (
                    f"Olist product in {category}; name_length={row.get('product_name_lenght') or row.get('product_name_length')}; "
                    f"description_length={row.get('product_description_lenght') or row.get('product_description_length')}."
                ),
                "brand": "olist",
                "category": category,
                "attributes": {
                    "source_dataset": "olist",
                    "raw_product_id": product_id,
                    "photos_qty": row.get("product_photos_qty"),
                    "weight_g": row.get("product_weight_g"),
                    "length_cm": row.get("product_length_cm"),
                    "height_cm": row.get("product_height_cm"),
                    "width_cm": row.get("product_width_cm"),
                    "average_rating": average_rating,
                    "review_count": review_count,
                    "sales_count": sales_counts[product_id],
                    "synthetic_price": synthetic_price,
                    "synthetic_inventory": True,
                },
                "price": round(sum(prices) / len(prices), 2) if prices else stable_price(product_id, seed=seed),
                "currency": "BRL",
                "availability": stable_availability(product_id, seed=seed),
                "popularity_score": popularity_from_counts(sales_counts, product_id),
                "seller_id": seller,
                "updated_at": "2026-01-01T00:00:00Z",
            }
        )
    return transformed, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Olist product snapshots and canonical events.")
    parser.add_argument("--products", type=Path, required=True, help="olist_products_dataset CSV or JSONL.")
    parser.add_argument("--order-items", type=Path, default=None, help="olist_order_items_dataset CSV or JSONL.")
    parser.add_argument("--reviews", type=Path, default=None, help="olist_order_reviews_dataset CSV or JSONL.")
    parser.add_argument("--max-products", type=int, default=100)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        products, judgments = prepare_olist_sample(
            products=read_records(args.products),
            order_items=read_records(args.order_items) if args.order_items else None,
            reviews=read_records(args.reviews) if args.reviews else None,
            max_products=args.max_products,
            seed=args.seed,
        )
        outputs = write_standard_outputs(output_dir=args.output_dir, products=products, judgments=judgments, dataset="olist")
        for name, path in outputs.items():
            print(f"Wrote {name} to {path}")
    except Exception as exc:  # noqa: BLE001 - CLI should print a clear local failure.
        print(f"Olist sample preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
