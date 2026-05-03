import json

from scripts.benchmark_search import BenchmarkAttempt, percentile, summarize_attempts, write_reports


def test_percentile_uses_linear_interpolation():
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 25.0
    assert round(percentile(values, 95), 2) == 38.5
    assert percentile([], 95) == 0.0


def test_summary_aggregates_errors_timeouts_and_average():
    attempts = [
        BenchmarkAttempt("baseline_bm25", "wireless mouse", 10.0, True, result_count=3),
        BenchmarkAttempt("baseline_bm25", "usb c charger", 30.0, True, result_count=5),
        BenchmarkAttempt("baseline_bm25", "bad query", 50.0, False, timed_out=True, error="ConnectionTimeout"),
        BenchmarkAttempt("boosted_bm25", "wireless mouse", 20.0, True, result_count=3),
    ]

    summaries = {summary.strategy: summary for summary in summarize_attempts(attempts)}

    baseline = summaries["baseline_bm25"]
    assert baseline.count == 3
    assert baseline.success_count == 2
    assert baseline.error_count == 1
    assert baseline.timeout_count == 1
    assert baseline.p50 == 20.0
    assert baseline.avg == 20.0
    assert baseline.error_rate == 1 / 3
    assert baseline.timeout_rate == 1 / 3

    boosted = summaries["boosted_bm25"]
    assert boosted.p95 == 20.0
    assert boosted.error_rate == 0.0


def test_write_reports_creates_json_and_markdown(tmp_path):
    attempts = [
        BenchmarkAttempt("enriched_profile", "wireless mouse", 12.0, True, result_count=5),
        BenchmarkAttempt("enriched_profile", "usb c charger", 18.0, True, result_count=5),
    ]
    summaries = summarize_attempts(attempts)
    json_path = tmp_path / "latency-report.json"
    markdown_path = tmp_path / "latency-report.md"

    write_reports(attempts, summaries, json_path, markdown_path)

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["query_count"] == 2
    assert report["summary"][0]["strategy"] == "enriched_profile"
    assert report["summary"][0]["avg"] == 15.0
    assert "Avg" in markdown_path.read_text(encoding="utf-8")
