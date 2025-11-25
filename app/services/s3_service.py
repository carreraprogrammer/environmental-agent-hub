"""
S3 service for asynchronous image upload operations.

This service handles background uploads of classified images to S3 storage with:
- Non-blocking async uploads using asyncio.to_thread()
- Automatic retry with exponential backoff
- Structured S3 keys: {tenant}/{YYYY-MM-DD}/{trace_id}.jpg
- Comprehensive error handling without aborting classification
- Detailed structured logging

Architecture V3.0 - Services Layer
Cost: $0 per request (S3 storage cost separate)
Latency: Non-blocking (background task)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.logging import logger


class S3Service:
    """
    Service for uploading images to S3 asynchronously.

    Characteristics:
    - Upload does NOT block response of /classify endpoint
    - Automatic retry with exponential backoff (1s, 2s, 4s)
    - Generates structured S3 keys: {tenant}/{date}/{trace_id}.jpg
    - Handles errors gracefully without aborting classification
    - Detailed logging of all operations

    Usage in Pipeline:
        >>> s3_service = S3Service()
        >>> asyncio.create_task(
        ...     s3_service.upload_image(image_bytes, tenant_id, trace_id)
        ... )

    Example:
        >>> service = S3Service()
        >>> result = await service.upload_image(
        ...     image_bytes=b"...",
        ...     tenant_id="unarino",
        ...     trace_id="abc-123-def"
        ... )
        >>> print(result["success"])  # True if uploaded
        >>> print(result["s3_url"])   # S3 URL if successful
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        max_retries: int = 3,
        base_delay: int = 1,
    ):
        """
        Initialize S3Service with boto3 client.

        Args:
            bucket_name: S3 bucket name (defaults to settings.S3_BUCKET)
            max_retries: Maximum number of upload attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1)
        """
        self.bucket_name = bucket_name or settings.S3_BUCKET
        self.max_retries = max_retries
        self.base_delay = base_delay

        # Initialize boto3 S3 client with credentials from settings
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        logger.info(
            "s3_service_initialized",
            bucket=self.bucket_name,
            max_retries=self.max_retries,
            region=settings.AWS_REGION,
        )

    def generate_s3_key(self, tenant_id: str, trace_id: str) -> str:
        """
        Generate structured S3 key for image storage.

        Format: {tenant}/{YYYY-MM-DD}/{trace_id}.jpg
        Example: unarino/2025-11-25/abc-123-def.jpg

        This structure enables:
        - Multi-tenancy (partition by tenant)
        - Temporal organization (partition by date)
        - Full traceability (trace_id → specific request)

        Args:
            tenant_id: Tenant identifier (e.g., "unarino")
            trace_id: UUID trace identifier

        Returns:
            Complete S3 key string
        """
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        s3_key = f"{tenant_id}/{date_str}/{trace_id}.jpg"

        logger.debug(
            "s3_key_generated",
            tenant_id=tenant_id,
            trace_id=trace_id,
            s3_key=s3_key,
            date=date_str,
        )

        return s3_key

    async def upload_image(
        self,
        image_bytes: bytes,
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Upload image to S3 with automatic retry and exponential backoff.

        This method is designed to run as a background task and does not block
        the main classification pipeline. Failures are logged but do not raise
        exceptions.

        Retry Strategy:
        - Attempt 1: immediate
        - Attempt 2: wait 1s (base_delay * 2^0)
        - Attempt 3: wait 2s (base_delay * 2^1)
        - Attempt 4: wait 4s (base_delay * 2^2) - last attempt

        Error Handling:
        - Authentication errors (AccessDenied, InvalidAccessKeyId): NO retry
        - Transient errors (network, throttling): YES retry
        - All errors return dict with error details (no exceptions raised)

        Args:
            image_bytes: Raw image data in bytes
            tenant_id: Tenant identifier (e.g., "unarino")
            trace_id: UUID trace identifier for logging and traceability

        Returns:
            dict with upload result:
                {
                    "success": True/False,
                    "s3_url": "https://..." (if successful),
                    "s3_key": "tenant/date/trace.jpg",
                    "attempts": 2,
                    "error": None (or error message if failed)
                }

        Example:
            >>> # In Pipeline.process() - background task
            >>> asyncio.create_task(
            ...     s3_service.upload_image(
            ...         image_bytes=request.image_bytes,
            ...         tenant_id=request.tenant_id,
            ...         trace_id=str(request.trace_id)
            ...     )
            ... )
        """
        s3_key = self.generate_s3_key(tenant_id, trace_id)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "s3_upload_attempt",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    trace_id=trace_id,
                    s3_key=s3_key,
                    size_kb=len(image_bytes) // 1024,
                    bucket=self.bucket_name,
                )

                # Upload to S3 using asyncio.to_thread to avoid blocking
                # boto3 operations are synchronous, so we run them in a thread
                await asyncio.to_thread(
                    self.s3_client.put_object,
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType="image/jpeg",
                    Metadata={
                        "tenant_id": tenant_id,
                        "trace_id": trace_id,
                        "uploaded_at": datetime.utcnow().isoformat(),
                    },
                )

                # Generate S3 URL (public if bucket is configured as public)
                s3_url = (
                    f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
                )

                logger.info(
                    "s3_upload_success",
                    trace_id=trace_id,
                    s3_key=s3_key,
                    s3_url=s3_url,
                    attempt=attempt,
                    bucket=self.bucket_name,
                )

                return {
                    "success": True,
                    "s3_url": s3_url,
                    "s3_key": s3_key,
                    "attempts": attempt,
                    "error": None,
                }

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]

                logger.warning(
                    "s3_upload_client_error",
                    trace_id=trace_id,
                    error_code=error_code,
                    error_message=error_message,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    will_retry=attempt < self.max_retries,
                )

                # Authentication/permission errors should NOT retry
                # These are permanent failures that won't be fixed by retrying
                if error_code in [
                    "AccessDenied",
                    "InvalidAccessKeyId",
                    "SignatureDoesNotMatch",
                ]:
                    logger.error(
                        "s3_upload_auth_error_permanent",
                        trace_id=trace_id,
                        error_code=error_code,
                        message="Authentication error - not retrying",
                    )
                    return {
                        "success": False,
                        "s3_url": None,
                        "s3_key": s3_key,
                        "attempts": attempt,
                        "error": f"Auth error: {error_code}",
                    }

                # For other ClientErrors, retry if attempts remaining
                if attempt >= self.max_retries:
                    logger.error(
                        "s3_upload_max_retries_exceeded",
                        trace_id=trace_id,
                        error_code=error_code,
                        attempts=attempt,
                    )
                    return {
                        "success": False,
                        "s3_url": None,
                        "s3_key": s3_key,
                        "attempts": attempt,
                        "error": f"Max retries exceeded: {error_code}",
                    }

            except BotoCoreError as e:
                logger.warning(
                    "s3_upload_botocore_error",
                    trace_id=trace_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    will_retry=attempt < self.max_retries,
                )

                if attempt >= self.max_retries:
                    logger.error(
                        "s3_upload_max_retries_exceeded",
                        trace_id=trace_id,
                        error_type="BotoCoreError",
                        attempts=attempt,
                    )
                    return {
                        "success": False,
                        "s3_url": None,
                        "s3_key": s3_key,
                        "attempts": attempt,
                        "error": f"BotoCore error: {str(e)}",
                    }

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "s3_upload_unexpected_error",
                    trace_id=trace_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                if attempt >= self.max_retries:
                    logger.error(
                        "s3_upload_max_retries_exceeded",
                        trace_id=trace_id,
                        error_type="UnexpectedError",
                        attempts=attempt,
                    )
                    return {
                        "success": False,
                        "s3_url": None,
                        "s3_key": s3_key,
                        "attempts": attempt,
                        "error": f"Unexpected error: {str(e)}",
                    }

            # Exponential backoff before retry
            # Formula: delay = base_delay * (2 ** (attempt - 1))
            # Example: attempt 1→2: 1s, attempt 2→3: 2s, attempt 3→4: 4s
            if attempt < self.max_retries:
                delay = self.base_delay * (2 ** (attempt - 1))
                logger.debug(
                    "s3_upload_retry_delay",
                    trace_id=trace_id,
                    delay_seconds=delay,
                    next_attempt=attempt + 1,
                )
                await asyncio.sleep(delay)

        # Should not reach here, but return failure just in case
        logger.error(
            "s3_upload_unexpected_exit",
            trace_id=trace_id,
            message="Upload loop exited unexpectedly",
        )
        return {
            "success": False,
            "s3_url": None,
            "s3_key": s3_key,
            "attempts": self.max_retries,
            "error": "Unknown failure",
        }
