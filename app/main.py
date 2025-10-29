"""
Agent Hub - FastAPI Application

Waste classification orchestrator with interchangeable AI models.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.health import router as health_router
from app.core.config import settings
from app.core.logging import logger, setup_logging

# Setup structured logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title="Agent Hub API",
    version="2.0.0",
    description="Waste classification orchestrator with interchangeable models",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(  # type: ignore[call-arg]
    CORSMiddleware,  # type: ignore
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Startup event handler.
    
    Logs application start with configuration info.
    """
    logger.info(
        "agent_hub_started",
        version="2.0.0",
        debug=settings.DEBUG,
        classifier_model=settings.CLASSIFIER_MODEL,
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Shutdown event handler.
    
    Logs application shutdown.
    """
    logger.info("agent_hub_shutdown")


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message with link to docs
    """
    return {
        "message": "Agent Hub API - Visit /docs for documentation",
        "version": "2.0.0",
        "status": "healthy",
    }


# Import routers (futuro)
# from app.api.endpoints import classify, models
# app.include_router(classify.router)
# app.include_router(models.router)
