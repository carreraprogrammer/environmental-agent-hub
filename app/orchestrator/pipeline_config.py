"""
Pipeline configuration (placeholder).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

default_steps: list[str] = [
    "validate_payload",
    "route_request",
    "classify",
    "map_material_to_color",
    "generate_feedback",
    "assemble_response",
]


@dataclass(slots=True)
class PipelineConfig:
    """
    Configuration for the classification pipeline.
    """

    steps: list[str]
    metadata: dict[str, Any]


DEFAULT_PIPELINE_CONFIG = PipelineConfig(steps=default_steps, metadata={"version": "0.1.0"})
