"""Alert threshold evaluation tests."""

from app.alerts import evaluate_alerts


def test_no_metrics_no_alerts():
    result = evaluate_alerts(None, cpu_threshold=80, memory_threshold=80)
    assert result["any_alert"] is False


def test_cpu_alert():
    metrics = {"cpu_percent": 90.0, "memory": {"percent": 10.0}}
    result = evaluate_alerts(metrics, cpu_threshold=80, memory_threshold=80)
    assert result["cpu_alert"] is True
    assert result["memory_alert"] is False
    assert result["any_alert"] is True


def test_memory_alert_at_threshold():
    metrics = {"cpu_percent": 10.0, "memory": {"percent": 80.0}}
    result = evaluate_alerts(metrics, cpu_threshold=80, memory_threshold=80)
    assert result["memory_alert"] is True
