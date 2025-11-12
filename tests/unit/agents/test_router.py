"""
Unit tests for Router Agent.

Tests cover:
- Schema validation (both ClassifyRequest and ClassifyRequestForm)
- Bytes processing (preferred format)
- URL processing (legacy format)
- Error handling (empty bytes, invalid URLs, network errors)
- Logging verification
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from app.agents.router import Router
from app.schemas.requests import ClassifyRequest, ClassifyRequestForm


class TestSchemas:
    """Test Pydantic schema validation."""

    def test_classify_request_valid(self):
        """Test ClassifyRequest with valid data."""
        request = ClassifyRequest(
            station_id="STATION-01",
            image_url="https://example.com/image.jpg",
            tenant_id="tenant-123",
        )

        assert request.station_id == "STATION-01"
        assert request.image_url == "https://example.com/image.jpg"
        assert request.tenant_id == "tenant-123"
        assert request.scan_id is not None
        assert request.trace_id is not None
        assert request.idempotency_key is not None

    def test_classify_request_invalid_url(self):
        """Test ClassifyRequest with invalid URL format."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            ClassifyRequest(
                station_id="STATION-01",
                image_url="ftp://example.com/image.jpg",  # Invalid protocol
                tenant_id="tenant-123",
            )

    def test_classify_request_valid_s3_url(self):
        """Test ClassifyRequest with s3:// URL."""
        request = ClassifyRequest(
            station_id="STATION-01",
            image_url="s3://bucket/image.jpg",
            tenant_id="tenant-123",
        )
        assert request.image_url == "s3://bucket/image.jpg"

    def test_classify_request_station_id_too_short(self):
        """Test ClassifyRequest with station_id too short."""
        with pytest.raises(ValueError):
            ClassifyRequest(
                station_id="",  # Empty string
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

    def test_classify_request_station_id_too_long(self):
        """Test ClassifyRequest with station_id too long."""
        with pytest.raises(ValueError):
            ClassifyRequest(
                station_id="x" * 51,  # 51 chars (max is 50)
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

    def test_classify_request_form_valid(self):
        """Test ClassifyRequestForm with valid data."""
        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=b"fake_image_data",
            tenant_id="tenant-123",
        )

        assert request.station_id == "STATION-01"
        assert request.image_bytes == b"fake_image_data"
        assert request.tenant_id == "tenant-123"
        assert request.scan_id is not None
        assert request.trace_id is not None
        assert request.idempotency_key is not None

    def test_classify_request_form_custom_uuids(self):
        """Test ClassifyRequestForm with custom UUIDs."""
        scan_id = uuid4()
        trace_id = uuid4()
        idempotency_key = uuid4()

        request = ClassifyRequestForm(
            scan_id=scan_id,
            station_id="STATION-01",
            image_bytes=b"fake_image_data",
            tenant_id="tenant-123",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

        assert request.scan_id == scan_id
        assert request.trace_id == trace_id
        assert request.idempotency_key == idempotency_key


class TestRouterBytesProcessing:
    """Test Router with bytes input (preferred format)."""

    @pytest.mark.asyncio
    async def test_validate_and_process_with_bytes_success(self):
        """Test successful processing with bytes input."""
        router = Router()

        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=b"fake_image_data",
            tenant_id="tenant-123",
        )

        validated_request, image_data = await router.validate_and_process(request)

        assert isinstance(validated_request, ClassifyRequestForm)
        assert validated_request.station_id == "STATION-01"
        assert validated_request.tenant_id == "tenant-123"
        assert image_data == b"fake_image_data"
        assert validated_request.image_bytes == b"fake_image_data"

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_empty_bytes(self):
        """Test processing with empty bytes - should raise ValueError."""
        router = Router()

        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=b"",  # Empty bytes
            tenant_id="tenant-123",
        )

        with pytest.raises(ValueError, match="image_bytes is empty or None"):
            await router.validate_and_process(request)

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_none_bytes(self):
        """Test processing with None bytes - should raise ValueError."""
        router = Router()

        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=None,  # None bytes
            tenant_id="tenant-123",
        )

        with pytest.raises(ValueError, match="image_bytes is empty or None"):
            await router.validate_and_process(request)

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_preserves_uuids(self):
        """Test that processing preserves all UUIDs."""
        router = Router()

        scan_id = uuid4()
        trace_id = uuid4()
        idempotency_key = uuid4()

        request = ClassifyRequestForm(
            scan_id=scan_id,
            station_id="STATION-01",
            image_bytes=b"fake_image_data",
            tenant_id="tenant-123",
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

        validated_request, image_data = await router.validate_and_process(request)

        assert validated_request.scan_id == scan_id
        assert validated_request.trace_id == trace_id
        assert validated_request.idempotency_key == idempotency_key

        await router.close()


class TestRouterURLProcessing:
    """Test Router with URL input (legacy format)."""

    @pytest.mark.asyncio
    async def test_validate_and_process_with_url_success(self):
        """Test successful processing with URL input."""
        router = Router()

        # Mock httpx client
        mock_response = Mock()
        mock_response.content = b"downloaded_image_data"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_get = AsyncMock(return_value=mock_response)

        with patch.object(router.http_client, "get", mock_get):
            request = ClassifyRequest(
                station_id="STATION-01",
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

            validated_request, image_data = await router.validate_and_process(request)

            assert isinstance(validated_request, ClassifyRequestForm)
            assert validated_request.station_id == "STATION-01"
            assert validated_request.tenant_id == "tenant-123"
            assert image_data == b"downloaded_image_data"
            assert validated_request.image_bytes == b"downloaded_image_data"

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_url_converts_to_form(self):
        """Test that URL input is converted to ClassifyRequestForm."""
        router = Router()

        scan_id = uuid4()
        trace_id = uuid4()
        idempotency_key = uuid4()

        mock_response = Mock()
        mock_response.content = b"downloaded_image_data"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_get = AsyncMock(return_value=mock_response)

        with patch.object(router.http_client, "get", mock_get):
            request = ClassifyRequest(
                scan_id=scan_id,
                station_id="STATION-01",
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
                trace_id=trace_id,
                idempotency_key=idempotency_key,
            )

            validated_request, image_data = await router.validate_and_process(request)

            # Check conversion to ClassifyRequestForm
            assert isinstance(validated_request, ClassifyRequestForm)
            assert validated_request.scan_id == scan_id
            assert validated_request.trace_id == trace_id
            assert validated_request.idempotency_key == idempotency_key
            assert validated_request.station_id == request.station_id
            assert validated_request.tenant_id == request.tenant_id

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_url_404_error(self):
        """Test URL processing with 404 error."""
        router = Router()

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        with patch.object(router.http_client, "get", side_effect=mock_error):
            request = ClassifyRequest(
                station_id="STATION-01",
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

            with pytest.raises(ValueError, match="Failed to fetch image \\(HTTP 404\\)"):
                await router.validate_and_process(request)

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_url_timeout(self):
        """Test URL processing with timeout error."""
        router = Router()

        # Mock timeout
        with patch.object(
            router.http_client, "get", side_effect=httpx.TimeoutException("Timeout")
        ):
            request = ClassifyRequest(
                station_id="STATION-01",
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

            with pytest.raises(ValueError, match="Failed to fetch image \\(timeout\\)"):
                await router.validate_and_process(request)

        await router.close()

    @pytest.mark.asyncio
    async def test_validate_and_process_with_url_network_error(self):
        """Test URL processing with generic network error."""
        router = Router()

        # Mock generic error
        with patch.object(
            router.http_client, "get", side_effect=Exception("Connection refused")
        ):
            request = ClassifyRequest(
                station_id="STATION-01",
                image_url="https://example.com/image.jpg",
                tenant_id="tenant-123",
            )

            with pytest.raises(ValueError, match="Failed to fetch image"):
                await router.validate_and_process(request)

        await router.close()


class TestRouterContextManager:
    """Test Router async context manager support."""

    @pytest.mark.asyncio
    async def test_router_context_manager(self):
        """Test Router can be used as async context manager."""
        async with Router() as router:
            request = ClassifyRequestForm(
                station_id="STATION-01",
                image_bytes=b"fake_image_data",
                tenant_id="tenant-123",
            )

            validated_request, image_data = await router.validate_and_process(request)

            assert image_data == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_router_custom_timeout(self):
        """Test Router with custom timeout."""
        router = Router(timeout=5.0)

        assert router.http_client.timeout.read == 5.0

        await router.close()


class TestRouterLogging:
    """Test Router logging behavior."""

    @pytest.mark.asyncio
    async def test_logging_with_bytes_input(self):
        """Test that proper logs are emitted for bytes input."""
        router = Router()

        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=b"fake_image_data",
            tenant_id="tenant-123",
        )

        with patch("app.agents.router.logger") as mock_logger:
            await router.validate_and_process(request)

            # Check router_started log
            mock_logger.info.assert_any_call(
                "router_started",
                trace_id=str(request.trace_id),
                agent="Router",
                input_format="bytes",
            )

            # Check router_complete log
            mock_logger.info.assert_any_call(
                "router_complete",
                trace_id=str(request.trace_id),
                agent="Router",
                input_format="bytes",
                image_size_bytes=len(b"fake_image_data"),
            )

        await router.close()

    @pytest.mark.asyncio
    async def test_logging_with_url_input(self):
        """Test that proper logs are emitted for URL input."""
        router = Router()

        mock_response = Mock()
        mock_response.content = b"downloaded_image_data"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_get = AsyncMock(return_value=mock_response)

        request = ClassifyRequest(
            station_id="STATION-01",
            image_url="https://example.com/image.jpg",
            tenant_id="tenant-123",
        )

        with patch("app.agents.router.logger") as mock_logger:
            with patch.object(router.http_client, "get", mock_get):
                await router.validate_and_process(request)

                # Check router_started log
                mock_logger.info.assert_any_call(
                    "router_started",
                    trace_id=str(request.trace_id),
                    agent="Router",
                    input_format="url",
                )

                # Check image_fetch_started log
                mock_logger.info.assert_any_call(
                    "image_fetch_started",
                    trace_id=str(request.trace_id),
                    agent="Router",
                    url=request.image_url,
                )

                # Check router_complete log
                mock_logger.info.assert_any_call(
                    "router_complete",
                    trace_id=str(request.trace_id),
                    agent="Router",
                    input_format="url",
                    image_size_bytes=len(b"downloaded_image_data"),
                )

        await router.close()

    @pytest.mark.asyncio
    async def test_logging_on_empty_bytes_error(self):
        """Test that error is logged when bytes are empty."""
        router = Router()

        request = ClassifyRequestForm(
            station_id="STATION-01",
            image_bytes=b"",
            tenant_id="tenant-123",
        )

        with patch("app.agents.router.logger") as mock_logger:
            with pytest.raises(ValueError):
                await router.validate_and_process(request)

            # Check error log
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "router_validation_failed"
            assert call_args[1]["trace_id"] == str(request.trace_id)
            assert call_args[1]["error"] == "image_bytes is empty or None"

        await router.close()

    @pytest.mark.asyncio
    async def test_logging_on_url_fetch_error(self):
        """Test that error is logged when URL fetch fails."""
        router = Router()

        request = ClassifyRequest(
            station_id="STATION-01",
            image_url="https://example.com/image.jpg",
            tenant_id="tenant-123",
        )

        with patch("app.agents.router.logger") as mock_logger:
            with patch.object(
                router.http_client, "get", side_effect=Exception("Network error")
            ):
                with pytest.raises(ValueError):
                    await router.validate_and_process(request)

                # Check error log was called
                error_calls = [
                    call for call in mock_logger.error.call_args_list
                    if call[0][0] == "image_fetch_failed"
                ]
                assert len(error_calls) > 0

        await router.close()


class TestLegacyFunction:
    """Test legacy route_request function."""

    def test_route_request_returns_payload(self):
        """Test that legacy function returns payload unchanged."""
        from app.agents.router import route_request

        payload = {"key": "value"}
        result = route_request(payload)

        assert result == payload
