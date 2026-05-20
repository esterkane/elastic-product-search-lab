import contextvars
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.privacy import redact_tokens

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_tokens(record.getMessage()),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(""),
        }
        for key in ["path", "method", "status_code", "latency_ms", "run_id", "tool_name"]:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


class MetricsRegistry:
    def __init__(self) -> None:
        self.request_count: dict[tuple[str, str, int], int] = defaultdict(int)
        self.request_latency_ms: dict[tuple[str, str], list[float]] = defaultdict(list)
        self.tool_calls: dict[str, int] = defaultdict(int)
        self.retrievals: list[dict[str, Any]] = []
        self.token_usage: dict[str, int] = defaultdict(int)

    def observe_request(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        self.request_count[(method, path, status_code)] += 1
        self.request_latency_ms[(method, path)].append(latency_ms)

    def observe_tool_call(self, tool_name: str) -> None:
        self.tool_calls[tool_name] += 1

    def observe_retrieval(self, **payload: Any) -> None:
        self.retrievals.append(payload)

    def observe_tokens(self, provider: str, count: int) -> None:
        self.token_usage[provider] += count

    def render_prometheus(self) -> str:
        lines = [
            "# HELP groovegraph_http_requests_total Total HTTP requests.",
            "# TYPE groovegraph_http_requests_total counter",
        ]
        for (method, path, status), count in sorted(self.request_count.items()):
            lines.append(f'groovegraph_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')
        lines.extend(
            [
                "# HELP groovegraph_http_request_latency_ms_avg Average request latency in milliseconds.",
                "# TYPE groovegraph_http_request_latency_ms_avg gauge",
            ]
        )
        for (method, path), values in sorted(self.request_latency_ms.items()):
            avg = sum(values) / len(values)
            lines.append(f'groovegraph_http_request_latency_ms_avg{{method="{method}",path="{path}"}} {avg:.4f}')
        lines.extend(["# HELP groovegraph_tool_calls_total Tool call count.", "# TYPE groovegraph_tool_calls_total counter"])
        for tool, count in sorted(self.tool_calls.items()):
            lines.append(f'groovegraph_tool_calls_total{{tool="{tool}"}} {count}')
        lines.extend(["# HELP groovegraph_retrievals_total Retrieval events.", "# TYPE groovegraph_retrievals_total counter"])
        lines.append(f"groovegraph_retrievals_total {len(self.retrievals)}")
        lines.extend(["# HELP groovegraph_token_usage_total Provider token usage.", "# TYPE groovegraph_token_usage_total counter"])
        for provider, count in sorted(self.token_usage.items()):
            lines.append(f'groovegraph_token_usage_total{{provider="{provider}"}} {count}')
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request_id_var.set(request_id)
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - started) * 1000
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        metrics.observe_request(request.method, path, response.status_code, latency_ms)
        response.headers["X-Request-Id"] = request_id
        logging.getLogger("groovegraph.request").info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self.window[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= self.requests_per_minute:
            return Response("rate limit exceeded", status_code=429)
        bucket.append(now)
        return await call_next(request)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def configure_otel_if_available() -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    logging.getLogger("groovegraph.observability").info(
        "OpenTelemetry endpoint configured",
        extra={"otel_endpoint": settings.otel_exporter_otlp_endpoint},
    )
