from scripts.publish_events import delivery_report


class FakeMessage:
    def topic(self):
        return "product.price"


def test_delivery_report_records_retryable_failure(capsys):
    failures = []

    delivery_report(Exception("temporary broker outage"), FakeMessage(), failures)

    assert failures == [
        {
            "event": "kafka_delivery_failed",
            "error_kind": "retryable",
            "topic": "product.price",
            "message": "temporary broker outage",
        }
    ]
    assert "kafka_delivery_failed" in capsys.readouterr().err


def test_delivery_report_ignores_success():
    failures = []

    delivery_report(None, FakeMessage(), failures)

    assert failures == []
