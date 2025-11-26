"""
Integration tests for S3 upload functionality.

These tests interact with real AWS S3 infrastructure and are skipped by default.
To run these tests, set environment variable:
    RUN_S3_INTEGRATION_TESTS=1

Requirements:
- Valid AWS credentials in environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- S3 bucket configured and accessible
- Internet connectivity

Tests verify:
- Real S3 upload operations
- S3 object metadata
- Retry behavior with real network
- Error handling with real S3 errors
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest

from app.services.s3_service import S3Service


# Skip all tests if RUN_S3_INTEGRATION_TESTS is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_S3_INTEGRATION_TESTS"),
    reason="S3 integration tests disabled. Set RUN_S3_INTEGRATION_TESTS=1 to enable.",
)


@pytest.fixture
def s3_service():
    """
    Create S3Service with real AWS credentials.

    Requires environment variables:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - S3_BUCKET (optional, defaults to agent-hub-images)
    """
    bucket_name = os.getenv("S3_BUCKET", "agent-hub-images-test")
    return S3Service(bucket_name=bucket_name)


@pytest.mark.asyncio
async def test_real_s3_upload(s3_service):
    """
    Test real S3 upload with valid credentials.

    This test:
    1. Uploads a test image to S3
    2. Verifies upload success
    3. Checks returned S3 URL and metadata
    """
    # Create fake image data
    fake_image = b"fake_jpeg_data_for_integration_testing"
    tenant_id = "integration-test"
    trace_id = f"test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    # Upload to S3
    result = await s3_service.upload_image(
        image_bytes=fake_image,
        tenant_id=tenant_id,
        trace_id=trace_id,
    )

    # Verify upload succeeded
    assert result["success"] is True, f"Upload failed: {result.get('error')}"
    assert result["attempts"] >= 1
    assert result["attempts"] <= 3  # Should succeed within max retries
    assert result["error"] is None

    # Verify S3 URL format
    assert result["s3_url"] is not None
    assert s3_service.bucket_name in result["s3_url"]
    assert tenant_id in result["s3_url"]
    assert trace_id in result["s3_url"]

    # Verify S3 key format
    assert result["s3_key"] is not None
    assert result["s3_key"].startswith(f"{tenant_id}/")
    assert result["s3_key"].endswith(f"{trace_id}.jpg")


@pytest.mark.asyncio
async def test_real_s3_upload_with_metadata(s3_service):
    """
    Test that uploaded S3 objects have correct metadata.

    This test:
    1. Uploads an image
    2. Retrieves the object metadata from S3
    3. Verifies metadata contains tenant_id, trace_id, uploaded_at
    """
    fake_image = b"test_metadata_image"
    tenant_id = "metadata-test"
    trace_id = f"metadata-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    # Upload to S3
    result = await s3_service.upload_image(
        image_bytes=fake_image,
        tenant_id=tenant_id,
        trace_id=trace_id,
    )

    assert result["success"] is True

    # Retrieve object metadata from S3
    s3_key = result["s3_key"]
    response = s3_service.s3_client.head_object(
        Bucket=s3_service.bucket_name,
        Key=s3_key,
    )

    # Verify metadata
    metadata = response.get("Metadata", {})
    assert metadata.get("tenant_id") == tenant_id
    assert metadata.get("trace_id") == trace_id
    assert "uploaded_at" in metadata

    # Verify uploaded_at is valid ISO 8601 format
    uploaded_at = metadata["uploaded_at"]
    try:
        datetime.fromisoformat(uploaded_at)
    except ValueError:
        pytest.fail(f"uploaded_at is not valid ISO 8601: {uploaded_at}")

    # Verify ContentType
    assert response.get("ContentType") == "image/jpeg"


@pytest.mark.asyncio
async def test_real_s3_upload_with_large_image(s3_service):
    """
    Test upload of larger image (simulating real photo).

    This test uploads a 1MB fake image to verify that larger uploads work.
    """
    # Create 1MB fake image
    large_image = b"x" * (1024 * 1024)  # 1MB
    tenant_id = "large-image-test"
    trace_id = f"large-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    # Upload to S3
    result = await s3_service.upload_image(
        image_bytes=large_image,
        tenant_id=tenant_id,
        trace_id=trace_id,
    )

    # Verify upload succeeded
    assert result["success"] is True, f"Large image upload failed: {result.get('error')}"

    # Verify object exists and has correct size
    s3_key = result["s3_key"]
    response = s3_service.s3_client.head_object(
        Bucket=s3_service.bucket_name,
        Key=s3_key,
    )

    assert response["ContentLength"] == len(large_image)


@pytest.mark.asyncio
async def test_s3_key_organization(s3_service):
    """
    Test that S3 keys are properly organized by tenant and date.

    This test:
    1. Uploads images for different tenants
    2. Verifies they're stored in separate prefixes
    3. Verifies date-based organization
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    trace_id = f"org-test-{datetime.utcnow().strftime('%H%M%S')}"

    # Upload for tenant1
    result1 = await s3_service.upload_image(
        image_bytes=b"tenant1_image",
        tenant_id="tenant1",
        trace_id=f"{trace_id}-1",
    )

    # Upload for tenant2
    result2 = await s3_service.upload_image(
        image_bytes=b"tenant2_image",
        tenant_id="tenant2",
        trace_id=f"{trace_id}-2",
    )

    assert result1["success"] is True
    assert result2["success"] is True

    # Verify keys are organized by tenant
    assert result1["s3_key"].startswith(f"tenant1/{today}/")
    assert result2["s3_key"].startswith(f"tenant2/{today}/")

    # Verify they're in different tenant prefixes
    assert result1["s3_key"].split("/")[0] != result2["s3_key"].split("/")[0]


@pytest.mark.asyncio
async def test_s3_upload_with_invalid_credentials():
    """
    Test upload behavior with invalid AWS credentials.

    This test verifies that authentication errors are handled gracefully
    and don't retry (as they're permanent failures).
    """
    # Create service with invalid credentials
    service = S3Service(bucket_name="test-bucket")

    # Override credentials with invalid ones
    service.s3_client._request_signer._credentials.access_key = "INVALID_KEY"
    service.s3_client._request_signer._credentials.secret_key = "INVALID_SECRET"

    # Attempt upload
    result = await service.upload_image(
        image_bytes=b"test",
        tenant_id="test",
        trace_id="test-trace",
    )

    # Should fail without retry (auth errors don't retry)
    assert result["success"] is False
    assert result["attempts"] == 1  # No retry on auth errors
    assert "error" in result
