"""
Agent Hub - FastAPI Application

Waste classification orchestrator with interchangeable AI models.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.health import router as health_router

# Import settings and logging with error handling
try:
    from app.core.config import settings
    from app.core.logging import logger, setup_logging
    setup_logging()
except Exception as e:
    print(f"Warning: Failed to setup logging: {e}")
    # Fallback simple logger
    import logging
    logger = logging.getLogger(__name__)
    settings = None

# Create FastAPI application
app = FastAPI(
    title="Agent Hub API",
    version="2.0.0",
    description="Waste classification orchestrator with interchangeable models",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS with fallback
try:
    cors_origins = settings.CORS_ORIGINS if settings else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception as e:
    print(f"Warning: Failed to configure CORS: {e}")
    # Add permissive CORS as fallback
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
    try:
        if settings and logger:
            logger.info(
                "agent_hub_started",
                version="2.0.0",
                debug=settings.DEBUG,
                classifier_model=settings.CLASSIFIER_MODEL,
            )
        else:
            print("Agent Hub started - version 2.0.0")
    except Exception as e:
        print(f"Startup warning: {e}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Shutdown event handler.
    
    Logs application shutdown.
    """
    try:
        if logger:
            logger.info("agent_hub_shutdown")
        else:
            print("Agent Hub shutdown")
    except Exception as e:
        print(f"Shutdown warning: {e}")


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


@app.get("/health")
async def health_check_direct():
    """
    Direct health check endpoint (backup).
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "agent-hub",
        "version": "2.0.0",
        "message": "Service is running"
    }


# Import routers (futuro)
# from app.api.endpoints import classify, models
# app.include_router(classify.router)
# app.include_router(models.router)
