"""
Models endpoint (placeholder for future implementation).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["models"])


@router.get("/models")
async def list_models() -> dict[str, list[str]]:
    """
    Placeholder endpoint to list available models.
    
    Returns:
        dict: Placeholder response with available models
    """
    return {"models": []}
