"""
Observability metrics for production monitoring.

Provides Prometheus-compatible metrics for tracking pipeline performance,
errors, circuit breaker states, and retry behavior.
"""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Gauge, Histogram


# ========================================
# PIPELINE METRICS
# ========================================

pipeline_requests_total = Counter(
    "pipeline_requests_total",
    "Total pipeline requests",
    ["success", "error_type"],
)

pipeline_latency_ms = Histogram(
    "pipeline_latency_ms",
    "Pipeline latency in milliseconds",
    buckets=[100, 250, 500, 1000, 2000, 5000, 10000],
)

pipeline_agents_executed = Histogram(
    "pipeline_agents_executed",
    "Number of agents executed per request",
    buckets=[1, 2, 3, 4, 5, 6, 7, 8],
)


# ========================================
# CIRCUIT BREAKER METRICS
# ========================================

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
)

circuit_breaker_successes = Counter(
    "circuit_breaker_successes_total",
    "Total circuit breaker successes",
    ["service"],
)


# ========================================
# RETRY METRICS
# ========================================

retry_attempts_total = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["agent", "success"],
)

retry_exhausted_total = Counter(
    "retry_exhausted_total",
    "Total retries that exhausted max attempts",
    ["agent", "exception_type"],
)


# ========================================
# ERROR METRICS
# ========================================

errors_total = Counter(
    "errors_total",
    "Total errors by type and severity",
    ["error_type", "severity", "recoverable"],
)


class MetricsCollector:
    """Centralized metrics collector for observability."""

    @staticmethod
    def record_pipeline_execution(
        trace_id: str,
        latency_ms: float,
        success: bool,
        agents_executed: list[str],
        error_type: str | None = None,
    ) -> None:
        """
        Record complete pipeline execution.

        Args:
            trace_id: Request trace ID
            latency_ms: Total pipeline latency in milliseconds
            success: Whether pipeline succeeded
            agents_executed: List of agents that executed
            error_type: Type of error if failed (None if success)
        """
        pipeline_requests_total.labels(
            success=str(success).lower(),
            error_type=error_type or "none",
        ).inc()

        pipeline_latency_ms.observe(latency_ms)
        pipeline_agents_executed.observe(len(agents_executed))

    @staticmethod
    def record_circuit_breaker_state(service: str, state_value: int) -> None:
        """
        Record circuit breaker state.

        Args:
            service: Name of service
            state_value: State value (0=closed, 1=half_open, 2=open)
        """
        circuit_breaker_state.labels(service=service).set(state_value)

    @staticmethod
    def record_circuit_breaker_failure(service: str) -> None:
        """
        Record circuit breaker failure.

        Args:
            service: Name of service
        """
        circuit_breaker_failures.labels(service=service).inc()

    @staticmethod
    def record_circuit_breaker_success(service: str) -> None:
        """
        Record circuit breaker success.

        Args:
            service: Name of service
        """
        circuit_breaker_successes.labels(service=service).inc()

    @staticmethod
    def record_retry_attempt(agent: str, success: bool) -> None:
        """
        Record retry attempt.

        Args:
            agent: Name of agent
            success: Whether retry succeeded
        """
        retry_attempts_total.labels(
            agent=agent,
            success=str(success).lower(),
        ).inc()

    @staticmethod
    def record_retry_exhausted(agent: str, exception_type: str) -> None:
        """
        Record retry exhaustion.

        Args:
            agent: Name of agent
            exception_type: Type of exception
        """
        retry_exhausted_total.labels(
            agent=agent,
            exception_type=exception_type,
        ).inc()

    @staticmethod
    def record_error(
        error_type: str,
        severity: str,
        recoverable: bool,
    ) -> None:
        """
        Record error with metadata.

        Args:
            error_type: Type of error
            severity: Error severity (low, medium, high, critical)
            recoverable: Whether error is recoverable
        """
        errors_total.labels(
            error_type=error_type,
            severity=severity,
            recoverable=str(recoverable).lower(),
        ).inc()

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, Any] | None = None,
    ) -> None:
        """
        Record generic metric (backward compatibility).

        Args:
            name: Metric name
            value: Metric value
            labels: Optional metric labels
        """
        # This method provides backward compatibility with existing code
        # For now, it's a no-op, but we keep it to avoid breaking changes
        _ = (name, value, labels)
