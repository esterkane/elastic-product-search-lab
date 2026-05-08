from __future__ import annotations

import argparse
from pathlib import Path

from embedding import DIMENSIONS, embed_text
from opensearch_api import OpenSearchClient, read_jsonl

INDEX_NAME = "product_support_docs"
PIPELINE_NAME = "product-support-rrf"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create OpenSearch index, RRF pipeline, and ingest corpus.")
    parser.add_argument("--host", default="http://localhost:9201")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    args = parser.parse_args()

    client = OpenSearchClient(args.host)
    client.wait_until_ready()
    recreate_index(client)
    create_rrf_pipeline(client)
    records = prepared_records(read_jsonl(args.corpus))
    response = client.bulk_jsonl(INDEX_NAME, records)
    if response.get("errors"):
        raise RuntimeError(f"bulk ingest reported errors: {response}")
    print(f"indexed {len(records)} documents into {INDEX_NAME}")
    return 0


def recreate_index(client: OpenSearchClient) -> None:
    try:
        client.request("DELETE", f"/{INDEX_NAME}")
    except RuntimeError:
        pass
    client.request(
        "PUT",
        f"/{INDEX_NAME}",
        {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "category": {"type": "keyword"},
                    "body": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": DIMENSIONS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {"ef_construction": 64, "m": 16},
                        },
                    },
                }
            },
        },
    )


def create_rrf_pipeline(client: OpenSearchClient) -> None:
    client.request(
        "PUT",
        f"/_search/pipeline/{PIPELINE_NAME}",
        {
            "description": "RRF rank fusion for BM25 plus raw-vector retrieval.",
            "phase_results_processors": [
                {
                    "score-ranker-processor": {
                        "combination": {
                            "technique": "rrf",
                            "rank_constant": 60,
                        }
                    }
                }
            ],
        },
    )


def prepared_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    prepared = []
    for record in records:
        text = f"{record['title']} {record['body']}"
        prepared.append({**record, "embedding": embed_text(text)})
    return prepared


if __name__ == "__main__":
    raise SystemExit(main())
