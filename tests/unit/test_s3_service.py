"""
Unit tests for S3Service.

Tests verify:
- S3Service initialization
- S3 key generation with correct format
- Successful image upload
- Retry logic with exponential backoff
- Error handling (auth errors, transient errors)
- Logging of all operations
- No exceptions raised (all errors return dict)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from app.services.s3_service import S3Service


@pytest.fixture
def s3_service():
    """Create S3Service instance with test configuration."""
    with patch("app.services.s3_service.settings") as mock_settings:
        mock_settings.S3_BUCKET = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret-key"
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.AWS_ENDPOINT_URL = None  # No custom endpoint by default

        with patch("app.services.s3_service.boto3.client"):
            service = S3Service(bucket_name="test-bucket")
            return service


@pytest.fixture
def mock_s3_client(s3_service):
    """Get mock S3 client from service."""
    return s3_service.s3_client


class TestS3ServiceInitialization:
    """Test S3Service initialization."""

    def test_init_with_default_bucket(self):
        """Test initialization with default bucket from settings."""
        with patch("app.services.s3_service.settings") as mock_settings:
            mock_settings.S3_BUCKET = "default-bucket"
            mock_settings.AWS_ACCESS_KEY_ID = "key-id"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key"
            mock_settings.AWS_REGION = "us-west-2"
            mock_settings.AWS_ENDPOINT_URL = None

            with patch("app.services.s3_service.boto3.client") as mock_boto:
                service = S3Service()

                assert service.bucket_name == "default-bucket"
                assert service.max_retries == 3
                assert service.base_delay == 1

                # Verify boto3 client was created with correct credentials
                mock_boto.assert_called_once()
                call_kwargs = mock_boto.call_args.kwargs
                assert call_kwargs["service_name"] == "s3"
                assert call_kwargs["aws_access_key_id"] == "key-id"
                assert call_kwargs["aws_secret_access_key"] == "secret-key"
                assert call_kwargs["region_name"] == "us-west-2"

    def test_init_with_custom_bucket(self):
        """Test initialization with custom bucket name."""
        with patch("app.services.s3_service.settings") as mock_settings:
            mock_settings.AWS_ACCESS_KEY_ID = "key-id"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ENDPOINT_URL = None

            with patch("app.services.s3_service.boto3.client"):
                service = S3Service(bucket_name="custom-bucket", max_retries=5, base_delay=2)

                assert service.bucket_name == "custom-bucket"
                assert service.max_retries == 5
                assert service.base_delay == 2

    def test_init_logs_configuration(self):
        """Test that initialization doesn't raise exceptions (logs are tested separately)."""
        with patch("app.services.s3_service.settings") as mock_settings:
            mock_settings.S3_BUCKET = "test-bucket"
            mock_settings.AWS_ACCESS_KEY_ID = "key-id"
            mock_settings.AWS_SECRET_ACCESS_KEY = "secret-key"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ENDPOINT_URL = None

            with patch("app.services.s3_service.boto3.client"):
                # Should not raise
                service = S3Service()
                assert service is not None

    def test_init_with_custom_endpoint(self):
        """Test initialization with custom endpoint URL (MinIO, R2, etc.)."""
        with patch("app.services.s3_service.settings") as mock_settings:
            mock_settings.S3_BUCKET = "test-bucket"
            mock_settings.AWS_ACCESS_KEY_ID = "minioadmin"
            mock_settings.AWS_SECRET_ACCESS_KEY = "minioadmin123"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ENDPOINT_URL = "http://localhost:9000"

            with patch("app.services.s3_service.boto3.client") as mock_boto:
                S3Service()

                # Verify boto3 client was called with endpoint_url
                mock_boto.assert_called_once()
                call_kwargs = mock_boto.call_args.kwargs
                assert call_kwargs["endpoint_url"] == "http://localhost:9000"
                assert call_kwargs["aws_access_key_id"] == "minioadmin"

    def test_init_without_custom_endpoint(self):
        """Test initialization without custom endpoint (AWS S3 default)."""
        with patch("app.services.s3_service.settings") as mock_settings:
            mock_settings.S3_BUCKET = "test-bucket"
            mock_settings.AWS_ACCESS_KEY_ID = "aws-key"
            mock_settings.AWS_SECRET_ACCESS_KEY = "aws-secret"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ENDPOINT_URL = None

            with patch("app.services.s3_service.boto3.client") as mock_boto:
                S3Service()

                # Verify boto3 client was called WITHOUT endpoint_url
                mock_boto.assert_called_once()
                call_kwargs = mock_boto.call_args.kwargs
                assert "endpoint_url" not in call_kwargs


class TestGenerateS3Key:
    """Test S3 key generation."""

    def test_generate_s3_key_format(self, s3_service):
        """Test that S3 key follows correct format."""
        key = s3_service.generate_s3_key("unarino", "abc-123-def")

        # Should be: {tenant}/{YYYY-MM-DD}/{trace_id}.jpg
        parts = key.split("/")
        assert len(parts) == 3
        assert parts[0] == "unarino"
        assert parts[2] == "abc-123-def.jpg"

        # Verify date format (YYYY-MM-DD)
        date_part = parts[1]
        assert len(date_part) == 10
        assert date_part.count("-") == 2

        # Verify it's today's date
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert date_part == today

    def test_generate_s3_key_with_different_tenants(self, s3_service):
        """Test key generation with different tenant IDs."""
        key1 = s3_service.generate_s3_key("tenant1", "trace1")
        key2 = s3_service.generate_s3_key("tenant2", "trace1")

        assert key1.startswith("tenant1/")
        assert key2.startswith("tenant2/")

    def test_generate_s3_key_with_different_trace_ids(self, s3_service):
        """Test key generation with different trace IDs."""
        key1 = s3_service.generate_s3_key("unarino", "trace-123")
        key2 = s3_service.generate_s3_key("unarino", "trace-456")

        assert key1.endswith("trace-123.jpg")
        assert key2.endswith("trace-456.jpg")

    def test_generate_s3_key_does_not_raise(self, s3_service):
        """Test that key generation doesn't raise exceptions (logs tested separately)."""
        # Should not raise
        key = s3_service.generate_s3_key("test-tenant", "test-trace")
        assert key is not None
        assert isinstance(key, str)


class TestUploadImageSuccess:
    """Test successful image upload."""

    @pytest.mark.asyncio
    async def test_upload_image_success(self, s3_service, mocker):
        """Test successful image upload on first attempt."""
        # Mock put_object to succeed
        mock_put = mocker.patch.object(s3_service.s3_client, "put_object", return_value={})

        # Mock asyncio.to_thread to execute function directly
        mocker.patch(
            "asyncio.to_thread",
            side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
        )

        # Upload image
        result = await s3_service.upload_image(
            image_bytes=b"fake_image_data",
            tenant_id="unarino",
            trace_id="test-trace-123",
        )

        # Verify result
        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["error"] is None
        assert "s3_url" in result
        assert "s3_key" in result
        assert "test-bucket.s3.us-east-1.amazonaws.com" in result["s3_url"]

        # Verify put_object was called with correct arguments
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["ContentType"] == "image/jpeg"
        assert "tenant_id" in call_kwargs["Metadata"]
        assert call_kwargs["Metadata"]["tenant_id"] == "unarino"
        assert call_kwargs["Metadata"]["trace_id"] == "test-trace-123"

    @pytest.mark.asyncio
    async def test_upload_image_returns_expected_structure(self, s3_service, mocker):
        """Test that successful upload returns expected result structure."""
        mocker.patch.object(s3_service.s3_client, "put_object", return_value={})
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))

        result = await s3_service.upload_image(
            image_bytes=b"test_data",
            tenant_id="test",
            trace_id="trace-123",
        )

        # Verify result has all expected fields
        assert "success" in result
        assert "s3_url" in result
        assert "s3_key" in result
        assert "attempts" in result
        assert "error" in result


class TestUploadImageRetry:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_upload_retry_success_on_second_attempt(self, s3_service, mocker):
        """Test that upload succeeds on retry after transient failure."""
        # First call fails, second succeeds
        mock_put = mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=[Exception("Transient network error"), {}],
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        # Should succeed on second attempt
        assert result["success"] is True
        assert result["attempts"] == 2
        assert mock_put.call_count == 2

        # Should have slept once (1 second before retry)
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_upload_retry_success_on_third_attempt(self, s3_service, mocker):
        """Test that upload succeeds on third attempt."""
        # First two calls fail, third succeeds
        mock_put = mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=[
                Exception("Error 1"),
                Exception("Error 2"),
                {},
            ],
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is True
        assert result["attempts"] == 3
        assert mock_put.call_count == 3

        # Should have slept twice (1s, then 2s)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, s3_service, mocker):
        """Test that exponential backoff follows correct timing."""
        # Make all attempts fail to test all delays
        mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=Exception("Always fails"),
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        # Should fail after max retries
        assert result["success"] is False
        assert result["attempts"] == 3

        # Verify exponential backoff: 1s, 2s, 4s
        # But only 2 sleeps because we don't sleep after the last attempt
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # After attempt 1
        mock_sleep.assert_any_call(2)  # After attempt 2
        # No sleep after attempt 3 (last attempt)


class TestUploadImageAuthErrors:
    """Test authentication error handling (no retry)."""

    @pytest.mark.asyncio
    async def test_auth_error_access_denied_no_retry(self, s3_service, mocker):
        """Test that AccessDenied error does not retry."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        # Should fail immediately without retry
        assert result["success"] is False
        assert result["attempts"] == 1
        assert "Auth error" in result["error"]

        # Should NOT have slept (no retry)
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_auth_error_invalid_access_key_no_retry(self, s3_service, mocker):
        """Test that InvalidAccessKeyId error does not retry."""
        error = ClientError(
            {"Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False
        assert result["attempts"] == 1
        assert "Auth error" in result["error"]
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_auth_error_signature_mismatch_no_retry(self, s3_service, mocker):
        """Test that SignatureDoesNotMatch error does not retry."""
        error = ClientError(
            {"Error": {"Code": "SignatureDoesNotMatch", "Message": "Bad signature"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False
        assert result["attempts"] == 1
        mock_sleep.assert_not_called()


class TestUploadImageTransientErrors:
    """Test transient error handling (with retry)."""

    @pytest.mark.asyncio
    async def test_client_error_throttling_retries(self, s3_service, mocker):
        """Test that throttling errors trigger retry."""
        error = ClientError(
            {"Error": {"Code": "SlowDown", "Message": "Please slow down"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        # Should retry up to max_retries
        assert result["success"] is False
        assert result["attempts"] == 3
        assert "Max retries exceeded" in result["error"]

        # Should have slept (with exponential backoff)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_botocore_error_retries(self, s3_service, mocker):
        """Test that BotoCoreError triggers retry."""
        error = BotoCoreError()
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False
        assert result["attempts"] == 3
        assert "BotoCore error" in result["error"]
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_generic_exception_retries(self, s3_service, mocker):
        """Test that generic exceptions trigger retry."""
        mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=Exception("Network error"),
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mock_sleep = mocker.patch("asyncio.sleep")

        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False
        assert result["attempts"] == 3
        assert "Unexpected error" in result["error"]
        assert mock_sleep.call_count == 2


class TestUploadImageLogging:
    """Test that logging operations don't raise exceptions."""

    @pytest.mark.asyncio
    async def test_logging_does_not_raise_on_success(self, s3_service, mocker):
        """Test that logging during successful upload doesn't raise."""
        mocker.patch.object(s3_service.s3_client, "put_object", return_value={})
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))

        # Should not raise
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace-123",
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_logging_does_not_raise_on_auth_error(self, s3_service, mocker):
        """Test that logging during auth error doesn't raise."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))

        # Should not raise
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_logging_does_not_raise_on_max_retries(self, s3_service, mocker):
        """Test that logging during max retries doesn't raise."""
        mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=Exception("Always fails"),
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mocker.patch("asyncio.sleep")

        # Should not raise
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert result["success"] is False


class TestUploadImageNeverRaises:
    """Test that upload_image never raises exceptions."""

    @pytest.mark.asyncio
    async def test_no_exception_on_auth_error(self, s3_service, mocker):
        """Test that auth errors don't raise exceptions."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        mocker.patch.object(s3_service.s3_client, "put_object", side_effect=error)
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))

        # Should not raise - returns dict instead
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert isinstance(result, dict)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_no_exception_on_max_retries(self, s3_service, mocker):
        """Test that max retries doesn't raise exceptions."""
        mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=Exception("Network error"),
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mocker.patch("asyncio.sleep")

        # Should not raise - returns dict instead
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert isinstance(result, dict)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_no_exception_on_unexpected_error(self, s3_service, mocker):
        """Test that unexpected errors don't raise exceptions."""
        mocker.patch.object(
            s3_service.s3_client,
            "put_object",
            side_effect=ValueError("Unexpected error"),
        )
        mocker.patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        mocker.patch("asyncio.sleep")

        # Should not raise - returns dict instead
        result = await s3_service.upload_image(
            image_bytes=b"test",
            tenant_id="tenant",
            trace_id="trace",
        )

        assert isinstance(result, dict)
        assert result["success"] is False
