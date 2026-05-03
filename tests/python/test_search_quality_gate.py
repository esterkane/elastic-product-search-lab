from scripts.gate_search_quality import evaluate_gate


def test_gate_passes_when_thresholds_are_met():
    config = {
        "strategy": "enriched_profile",
        "thresholds": {
            "minimum_average_precision_at_5": 0.6,
            "minimum_average_mrr_at_10": 0.75,
            "maximum_p95_latency_ms": 500,
        },
    }
    relevance_report = {"summary": [{"strategy": "enriched_profile", "precision_at_5": 0.7, "mrr_at_10": 0.8}]}
    latency_report = {"summary": [{"strategy": "enriched_profile", "p95": 120.0}]}

    assert evaluate_gate(config, relevance_report, latency_report) == []


def test_gate_reports_all_threshold_failures():
    config = {
        "strategy": "enriched_profile",
        "thresholds": {
            "minimum_average_precision_at_5": 0.6,
            "minimum_average_mrr_at_10": 0.75,
            "maximum_p95_latency_ms": 100,
        },
    }
    relevance_report = {"summary": [{"strategy": "enriched_profile", "precision_at_5": 0.4, "mrr_at_10": 0.5}]}
    latency_report = {"summary": [{"strategy": "enriched_profile", "p95": 150.0}]}

    failures = evaluate_gate(config, relevance_report, latency_report)

    assert len(failures) == 3
    assert "Precision@5 failed" in failures[0]
    assert "MRR@10 failed" in failures[1]
    assert "p95 latency failed" in failures[2]
