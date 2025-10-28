"""
Metrics collector placeholder.
"""

from __future__ import annotations

from typing import Any


class MetricsCollector:
    """
    Placeholder metrics collector service.
    """

    def record_metric(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        """
        Placeholder metric recording.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional metric labels
        """
        _ = (name, value, labels)
