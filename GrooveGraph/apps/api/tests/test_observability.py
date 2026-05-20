import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observability import JsonLogFormatter, metrics


def test_metrics_endpoint_works_and_request_id_is_returned() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-Id": "test-request-id"})
    metrics_response = client.get("/metrics")

    assert response.headers["X-Request-Id"] == "test-request-id"
    assert metrics_response.status_code == 200
    assert "groovegraph_http_requests_total" in metrics_response.text
    assert "/health" in metrics_response.text


def test_json_logs_redact_secrets() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer raw-secret-token access_token=abc refresh_token=def",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert "raw-secret-token" not in payload["message"]
    assert "abc" not in payload["message"]
    assert "def" not in payload["message"]
    assert "[REDACTED]" in payload["message"]


def test_tool_and_retrieval_metrics_render() -> None:
    metrics.observe_tool_call("vector_retrieval")
    metrics.observe_retrieval(
        query="q",
        rewritten_query="rewritten q",
        retriever_used="vector_retrieval",
        top_k=3,
        reranker_score=0.7,
        evidence_quality_score=0.9,
    )

    rendered = metrics.render_prometheus()

    assert 'groovegraph_tool_calls_total{tool="vector_retrieval"}' in rendered
    assert "groovegraph_retrievals_total" in rendered
