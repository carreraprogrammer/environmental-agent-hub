"""
Health check endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status information
    """
    try:
        return {
            "status": "healthy",
            "service": "agent-hub",
            "version": "2.0.0",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "service": "agent-hub",
        }
