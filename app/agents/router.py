"""
Router Agent - First step in the classification pipeline.

Responsibilities:
- Validate request schema with Pydantic
- Detect input format (bytes vs URL)
- Process image based on format
- Return validated request + image_data

Supports two input formats:
1. ClassifyRequestForm (multipart/form-data with bytes) - PREFERRED (60% faster)
2. ClassifyRequest (JSON with image_url) - LEGACY (backward compatible)
"""

from __future__ import annotations

from typing import Tuple, Union

import httpx

from app.core.logging import logger
from app.schemas.requests import ClassifyRequest, ClassifyRequestForm


class Router:
    """
    Router Agent - Validates request and processes input image.

    The Router is the entry point of the 10-step classification pipeline.
    It does NOT classify or analyze content - only validates structure and prepares data.

    Performance:
        - Bytes processing: ~5ms (validation only)
        - URL processing: ~200-500ms (includes network download)

    Example:
        >>> router = Router()
        >>> request = ClassifyRequestForm(
        ...     station_id="STATION-01",
        ...     image_bytes=b"...",
        ...     tenant_id="tenant-123"
        ... )
        >>> validated_request, image_data = await router.validate_and_process(request)
    """

    def __init__(self, timeout: float = 10.0):
        """
        Initialize Router with HTTP client.

        Args:
            timeout: Timeout in seconds for image downloads (default: 10.0)
        """
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def validate_and_process(
        self, request: Union[ClassifyRequest, ClassifyRequestForm]
    ) -> Tuple[ClassifyRequestForm, bytes]:
        """
        Validate request and process image input.

        Args:
            request: Either ClassifyRequest (JSON + URL) or ClassifyRequestForm (multipart + bytes)

        Returns:
            Tuple of (validated_request, image_bytes)

        Raises:
            ValidationError: If request is invalid (raised by Pydantic)
            ValueError: If image_bytes is empty or image cannot be fetched from URL

        Example:
            >>> # Preferred: bytes input
            >>> request = ClassifyRequestForm(
            ...     station_id="STATION-01",
            ...     image_bytes=b"...",
            ...     tenant_id="tenant-123"
            ... )
            >>> validated, image_data = await router.validate_and_process(request)

            >>> # Legacy: URL input
            >>> request = ClassifyRequest(
            ...     station_id="STATION-01",
            ...     image_url="https://example.com/image.jpg",
            ...     tenant_id="tenant-123"
            ... )
            >>> validated, image_data = await router.validate_and_process(request)
        """
        trace_id = str(request.trace_id)

        logger.info(
            "router_started",
            trace_id=trace_id,
            agent="Router",
            input_format="bytes" if isinstance(request, ClassifyRequestForm) else "url",
        )

        # Case 1: Multipart/form-data with bytes (PREFERRED)
        if isinstance(request, ClassifyRequestForm):
            if request.image_bytes and len(request.image_bytes) > 0:
                logger.info(
                    "router_complete",
                    trace_id=trace_id,
                    agent="Router",
                    input_format="bytes",
                    image_size_bytes=len(request.image_bytes),
                )
                return request, request.image_bytes
            else:
                logger.error(
                    "router_validation_failed",
                    trace_id=trace_id,
                    agent="Router",
                    error="image_bytes is empty or None",
                )
                raise ValueError("image_bytes is empty or None")

        # Case 2: JSON with image_url (LEGACY)
        if isinstance(request, ClassifyRequest):
            image_bytes = await self._fetch_image_from_url(request.image_url, trace_id)

            # Convert to ClassifyRequestForm
            form_request = ClassifyRequestForm(
                scan_id=request.scan_id,
                station_id=request.station_id,
                image_bytes=image_bytes,
                tenant_id=request.tenant_id,
                trace_id=request.trace_id,
                idempotency_key=request.idempotency_key,
            )

            logger.info(
                "router_complete",
                trace_id=trace_id,
                agent="Router",
                input_format="url",
                image_size_bytes=len(image_bytes),
            )

            return form_request, image_bytes

        # This should never happen due to type hints, but handle gracefully
        logger.error(
            "router_validation_failed",
            trace_id=trace_id,
            agent="Router",
            error=f"Unsupported request type: {type(request).__name__}",
        )
        raise ValueError(f"Unsupported request type: {type(request).__name__}")

    async def _fetch_image_from_url(self, url: str, trace_id: str) -> bytes:
        """
        Fetch image from URL (for legacy support).

        Args:
            url: Image URL (http://, https://, or s3://)
            trace_id: Trace ID for logging

        Returns:
            Image data as bytes

        Raises:
            ValueError: If image cannot be fetched (network error, 404, timeout, etc.)

        Note:
            This method is used for backward compatibility with systems that send
            image URLs instead of bytes. For production use, prefer bytes input.
        """
        try:
            logger.info(
                "image_fetch_started",
                trace_id=trace_id,
                agent="Router",
                url=url,
            )

            response = await self.http_client.get(url)
            response.raise_for_status()

            logger.info(
                "image_fetched",
                trace_id=trace_id,
                agent="Router",
                url=url,
                size_bytes=len(response.content),
                status_code=response.status_code,
            )

            return response.content

        except httpx.HTTPStatusError as e:
            logger.error(
                "image_fetch_failed",
                trace_id=trace_id,
                agent="Router",
                url=url,
                error=f"HTTP {e.response.status_code}: {str(e)}",
                status_code=e.response.status_code,
            )
            raise ValueError(f"Failed to fetch image (HTTP {e.response.status_code}): {str(e)}")

        except httpx.TimeoutException as e:
            logger.error(
                "image_fetch_failed",
                trace_id=trace_id,
                agent="Router",
                url=url,
                error=f"Timeout: {str(e)}",
            )
            raise ValueError(f"Failed to fetch image (timeout): {str(e)}")

        except Exception as e:
            logger.error(
                "image_fetch_failed",
                trace_id=trace_id,
                agent="Router",
                url=url,
                error=str(e),
            )
            raise ValueError(f"Failed to fetch image: {str(e)}")

    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.http_client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Legacy function for backward compatibility
def route_request(payload: dict[str, object]) -> dict[str, object]:
    """
    Placeholder function for routing requests to appropriate agents.

    DEPRECATED: Use Router class instead.

    Args:
        payload: Request payload data

    Returns:
        dict: Placeholder routed payload
    """
    return payload
