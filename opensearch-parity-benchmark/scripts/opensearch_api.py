from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenSearchClient:
    def __init__(self, base_url: str = "http://localhost:9201") -> None:
        self.base_url = base_url.rstrip("/")

    def wait_until_ready(self, timeout_seconds: int = 120) -> None:
        deadline = time.time() + timeout_seconds
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                health = self.request("GET", "/_cluster/health")
                if health.get("status") in {"green", "yellow"}:
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(2)
        raise RuntimeError(f"OpenSearch did not become ready: {last_error}")

    def request(self, method: str, path: str, body: object | None = None) -> dict[str, object]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(f"{method} {path} failed: {exc}") from exc
        return json.loads(raw) if raw else {}

    def bulk_jsonl(self, path: str, records: list[dict[str, object]]) -> dict[str, object]:
        lines = []
        for record in records:
            lines.append(json.dumps({"index": {"_index": path, "_id": record["id"]}}))
            lines.append(json.dumps(record))
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        request = Request(
            f"{self.base_url}/_bulk?refresh=true",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-ndjson"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"bulk ingest failed with {exc.code}: {details}") from exc


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
