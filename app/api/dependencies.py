"""
Dependency injection container for API routes.

Provides reusable dependencies for request handling, including
Pipeline orchestrator and S3Service for image uploads.
"""

from __future__ import annotations

from typing import Generator

from app.orchestrator.pipeline import Pipeline
from app.services.s3_service import S3Service


def get_request_id() -> Generator[str, None, None]:
    """
    Placeholder dependency for generating request identifiers.

    Yields:
        str: Unique request identifier (placeholder value)
    """
    yield "placeholder-request-id"


async def get_pipeline() -> Pipeline:
    """
    Dependency injection for Pipeline orchestrator.

    Creates a new Pipeline instance for each request. This allows for
    proper request isolation and testing with mock pipelines.

    Returns:
        Pipeline: Configured Pipeline orchestrator instance

    Example:
        >>> @router.post("/classify")
        >>> async def classify(pipeline: Pipeline = Depends(get_pipeline)):
        >>>     result = await pipeline.process(request)
    """
    return Pipeline()


async def get_s3_service() -> S3Service:
    """
    Dependency injection for S3Service.

    Creates a new S3Service instance for each request. This allows for
    proper request isolation and testing with mock S3 services.

    Returns:
        S3Service: Configured S3Service instance

    Example:
        >>> @router.post("/classify")
        >>> async def classify(s3: S3Service = Depends(get_s3_service)):
        >>>     await s3.upload_image(image_bytes, scan_id, tenant_id)
    """
    return S3Service()
