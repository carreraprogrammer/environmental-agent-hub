"""
Classification pipeline orchestrator (legacy placeholder).

This module provides a simple synchronous pipeline used in early
experiments. The real V4 pipeline uses PreValidator + MaterialClassifier
and is covered by separate tickets; this file remains only for backward
compatibility of basic flows and is not used by the V4 agents.
"""

from __future__ import annotations

from app.agents.assembler import assemble_response
from app.agents.feedback_coach import generate_feedback
from app.agents.mapper import map_material_to_color
from app.agents.pre_validator import validate_payload
from app.agents.router import route_request


def _legacy_classify(payload: dict[str, object]) -> dict[str, object]:
    """
    Legacy placeholder classification logic.

    This mirrors the old app.agents.classifier.classify behaviour without
    depending on the deprecated classifier module.
    """
    return {"result": "unclassified", "payload": payload}


def execute_pipeline(payload: dict[str, object]) -> dict[str, object]:
    """
    Execute the placeholder classification pipeline (legacy).

    Args:
        payload: Incoming payload data

    Returns:
        dict: Placeholder pipeline result.
    """
    if not validate_payload(payload):
        return {"status": "invalid"}

    routed_payload = route_request(payload)
    classification = _legacy_classify(routed_payload)
    classification["color"] = map_material_to_color(str(classification.get("result")))
    classification["feedback"] = generate_feedback(classification)
    return assemble_response(classification)
