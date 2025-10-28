"""
Health check endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check", response_model=None)
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "agent-hub",
        "version": "2.0.0",
    }
