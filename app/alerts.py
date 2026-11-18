"""Local CPU/memory threshold evaluation (no external notifications)."""

from __future__ import annotations

from typing import Any


def evaluate_alerts(
    metrics: dict[str, Any] | None,
    *,
    cpu_threshold: float,
    memory_threshold: float,
) -> dict[str, Any]:
    """
    Return alert flags based on last-fetched metrics.

    No side effects — UI highlighting only.
    """
    result = {
        "cpu_alert": False,
        "memory_alert": False,
        "any_alert": False,
        "cpu_percent": None,
        "memory_percent": None,
        "cpu_threshold": cpu_threshold,
        "memory_threshold": memory_threshold,
    }
    if not metrics:
        return result

    cpu = metrics.get("cpu_percent")
    mem = (metrics.get("memory") or {}).get("percent")
    result["cpu_percent"] = cpu
    result["memory_percent"] = mem

    if isinstance(cpu, (int, float)) and cpu >= cpu_threshold:
        result["cpu_alert"] = True
    if isinstance(mem, (int, float)) and mem >= memory_threshold:
        result["memory_alert"] = True
    result["any_alert"] = bool(result["cpu_alert"] or result["memory_alert"])
    return result
