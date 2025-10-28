"""
Classification endpoint (placeholder for future implementation).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["classification"])


@router.post("/classify")
async def classify_image() -> dict[str, str]:
    """
    Placeholder classification endpoint.
    
    Returns:
        dict: Placeholder response
    """
    return {"message": "Classification endpoint not implemented yet"}
