from scripts.benchmark_search import BenchmarkAttempt, percentile, summarize_attempts


def test_percentile_uses_linear_interpolation():
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 25.0
    assert round(percentile(values, 95), 2) == 38.5
    assert percentile([], 95) == 0.0


def test_summary_aggregates_errors_and_timeouts():
    attempts = [
        BenchmarkAttempt("baseline_lexical", "wireless mouse", 10.0, True, result_count=3),
        BenchmarkAttempt("baseline_lexical", "usb c charger", 30.0, True, result_count=5),
        BenchmarkAttempt("baseline_lexical", "bad query", 50.0, False, timed_out=True, error="ConnectionTimeout"),
        BenchmarkAttempt("boosted_lexical", "wireless mouse", 20.0, True, result_count=3),
    ]

    summaries = {summary.strategy: summary for summary in summarize_attempts(attempts)}

    baseline = summaries["baseline_lexical"]
    assert baseline.count == 3
    assert baseline.success_count == 2
    assert baseline.error_count == 1
    assert baseline.timeout_count == 1
    assert baseline.p50 == 20.0
    assert baseline.error_rate == 1 / 3
    assert baseline.timeout_rate == 1 / 3

    boosted = summaries["boosted_lexical"]
    assert boosted.p95 == 20.0
    assert boosted.error_rate == 0.0
