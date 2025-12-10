"""
Unit tests for DiscrepancyTracker service.

Tests discrepancy detection, record creation, backend communication,
and error handling scenarios.

Target coverage: ≥85%
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.schemas.classification import Material
from app.schemas.discrepancy import CorrectionPayload, DiscrepancyRecord
from app.services.discrepancy_tracker import DiscrepancyTracker


class TestDiscrepancyTrackerInit:
    """Tests for DiscrepancyTracker initialization."""

    def test_init_with_default_backend_url(self):
        """Test initialization with default backend URL from settings."""
        tracker = DiscrepancyTracker()

        # Should use settings.BACKEND_API_URL
        assert tracker.backend_url is not None
        assert tracker.corrections_endpoint.endswith("/classification_corrections")
        assert tracker._client is None

    def test_init_with_custom_backend_url(self):
        """Test initialization with custom backend URL."""
        custom_url = "http://custom-backend:8080/api/v1"
        tracker = DiscrepancyTracker(backend_url=custom_url)

        assert tracker.backend_url == custom_url
        assert (
            tracker.corrections_endpoint
            == f"{custom_url}/classification_corrections"
        )


class TestHasDiscrepancy:
    """Tests for discrepancy detection logic."""

    def test_has_discrepancy_returns_true_when_materials_differ(self):
        """Test discrepancy detected when materials differ."""
        tracker = DiscrepancyTracker()

        result = tracker.has_discrepancy(Material.PLASTIC, Material.METAL)

        assert result is True

    def test_has_discrepancy_returns_false_when_materials_match(self):
        """Test no discrepancy when materials match."""
        tracker = DiscrepancyTracker()

        result = tracker.has_discrepancy(Material.PLASTIC, Material.PLASTIC)

        assert result is False

    def test_has_discrepancy_with_all_material_combinations(self):
        """Test discrepancy detection with various material combinations."""
        tracker = DiscrepancyTracker()

        # Test same materials
        assert tracker.has_discrepancy(Material.GLASS, Material.GLASS) is False
        assert tracker.has_discrepancy(Material.PAPER, Material.PAPER) is False
        assert tracker.has_discrepancy(Material.ORGANIC, Material.ORGANIC) is False

        # Test different materials
        assert tracker.has_discrepancy(Material.PLASTIC, Material.GLASS) is True
        assert tracker.has_discrepancy(Material.METAL, Material.CARDBOARD) is True
        assert tracker.has_discrepancy(Material.PAPER, Material.TETRAPAK) is True


class TestCreateRecord:
    """Tests for creating discrepancy records."""

    def test_create_record_with_all_fields(self):
        """Test creating discrepancy record with all fields populated."""
        tracker = DiscrepancyTracker()

        record = tracker.create_record(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/waste-classifier",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="google/gemini-2.0-flash",
            scan_id="scan-456",
            tenant_id="udenar",
            station_id="station-1",
            image_url="s3://bucket/image.jpg",
        )

        assert isinstance(record, DiscrepancyRecord)
        assert record.trace_id == "trace-123"
        assert record.scan_id == "scan-456"
        assert record.tenant_id == "udenar"
        assert record.station_id == "station-1"
        assert record.fast_path_material == Material.PLASTIC
        assert record.fast_path_confidence == 0.72
        assert record.fast_path_model == "roboflow/waste-classifier"
        assert record.ground_truth_material == Material.METAL
        assert record.ground_truth_confidence == 0.94
        assert record.ground_truth_model == "google/gemini-2.0-flash"
        assert record.image_url == "s3://bucket/image.jpg"
        assert record.confidence_delta == pytest.approx(0.22, abs=0.01)
        assert isinstance(record.timestamp, datetime)

    def test_create_record_with_minimal_fields(self):
        """Test creating discrepancy record with only required fields."""
        tracker = DiscrepancyTracker()

        record = tracker.create_record(
            trace_id="trace-123",
            fast_path_material=Material.GLASS,
            fast_path_confidence=0.65,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.PLASTIC,
            ground_truth_confidence=0.88,
            ground_truth_model="openai/gpt-4o",
        )

        assert record.trace_id == "trace-123"
        assert record.scan_id is None
        assert record.tenant_id is None
        assert record.station_id is None
        assert record.image_url is None
        assert record.fast_path_material == Material.GLASS
        assert record.ground_truth_material == Material.PLASTIC
        assert record.confidence_delta == pytest.approx(0.23, abs=0.01)

    def test_create_record_confidence_delta_calculation(self):
        """Test confidence delta is calculated correctly."""
        tracker = DiscrepancyTracker()

        # Positive delta (ground truth more confident)
        record1 = tracker.create_record(
            trace_id="trace-1",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.60,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.95,
            ground_truth_model="gemini",
        )
        assert record1.confidence_delta == pytest.approx(0.35, abs=0.01)

        # Negative delta (fast path more confident)
        record2 = tracker.create_record(
            trace_id="trace-2",
            fast_path_material=Material.GLASS,
            fast_path_confidence=0.90,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.PLASTIC,
            ground_truth_confidence=0.75,
            ground_truth_model="gemini",
        )
        assert record2.confidence_delta == pytest.approx(-0.15, abs=0.01)


class TestSendCorrectionToBackend:
    """Tests for sending corrections to backend API."""

    @pytest.mark.asyncio
    async def test_send_correction_success_200(self):
        """Test successful correction send with 200 status."""
        tracker = DiscrepancyTracker(backend_url="http://test-backend/api/v1")

        record = DiscrepancyRecord(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            timestamp=datetime.utcnow(),
            confidence_delta=0.22,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        tracker._client = mock_client

        result = await tracker.send_correction_to_backend(record)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args[0][0]
            == "http://test-backend/api/v1/classification_corrections"
        )

    @pytest.mark.asyncio
    async def test_send_correction_success_201(self):
        """Test successful correction send with 201 status."""
        tracker = DiscrepancyTracker()

        record = DiscrepancyRecord(
            trace_id="trace-123",
            fast_path_material=Material.GLASS,
            fast_path_confidence=0.65,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.PLASTIC,
            ground_truth_confidence=0.88,
            ground_truth_model="gpt-4o",
            timestamp=datetime.utcnow(),
            confidence_delta=0.23,
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        tracker._client = mock_client

        result = await tracker.send_correction_to_backend(record)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_correction_backend_rejection_400(self):
        """Test backend rejects correction with 400 status."""
        tracker = DiscrepancyTracker()

        record = DiscrepancyRecord(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            timestamp=datetime.utcnow(),
            confidence_delta=0.22,
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request: invalid payload"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        tracker._client = mock_client

        result = await tracker.send_correction_to_backend(record)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_correction_timeout(self):
        """Test backend timeout is handled gracefully."""
        tracker = DiscrepancyTracker()

        record = DiscrepancyRecord(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            timestamp=datetime.utcnow(),
            confidence_delta=0.22,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        tracker._client = mock_client

        result = await tracker.send_correction_to_backend(record)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_correction_network_error(self):
        """Test network error is handled gracefully."""
        tracker = DiscrepancyTracker()

        record = DiscrepancyRecord(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            timestamp=datetime.utcnow(),
            confidence_delta=0.22,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.NetworkError("Connection failed")
        )

        tracker._client = mock_client

        result = await tracker.send_correction_to_backend(record)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_correction_creates_proper_payload(self):
        """Test correction payload is created correctly."""
        tracker = DiscrepancyTracker()

        record = DiscrepancyRecord(
            trace_id="trace-123",
            scan_id="scan-456",
            tenant_id="udenar",
            station_id="station-1",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            image_url="s3://bucket/image.jpg",
            timestamp=datetime.utcnow(),
            confidence_delta=0.22,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        tracker._client = mock_client

        await tracker.send_correction_to_backend(record)

        # Verify payload structure
        call_args = mock_client.post.call_args
        payload_dict = call_args.kwargs["json"]

        assert payload_dict["trace_id"] == "trace-123"
        assert payload_dict["scan_id"] == "scan-456"
        assert payload_dict["tenant_id"] == "udenar"
        assert payload_dict["station_id"] == "station-1"
        assert payload_dict["incorrect_material"] == "PLASTIC"
        assert payload_dict["incorrect_confidence"] == 0.72
        assert payload_dict["incorrect_model"] == "roboflow/model"
        assert payload_dict["correct_material"] == "METAL"
        assert payload_dict["correct_confidence"] == 0.94
        assert payload_dict["correct_model"] == "gemini"
        assert payload_dict["image_url"] == "s3://bucket/image.jpg"


class TestTrack:
    """Tests for main track() method."""

    @pytest.mark.asyncio
    async def test_track_with_agreement_returns_none(self):
        """Test track returns None when materials match."""
        tracker = DiscrepancyTracker()

        result = await tracker.track(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.85,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.PLASTIC,
            ground_truth_confidence=0.92,
            ground_truth_model="gemini",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_track_with_discrepancy_returns_record(self):
        """Test track returns DiscrepancyRecord when materials differ."""
        tracker = DiscrepancyTracker()

        # Mock backend call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        tracker._client = mock_client

        result = await tracker.track(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
        )

        assert isinstance(result, DiscrepancyRecord)
        assert result.fast_path_material == Material.PLASTIC
        assert result.ground_truth_material == Material.METAL

    @pytest.mark.asyncio
    async def test_track_sends_to_backend_on_discrepancy(self):
        """Test track sends correction to backend when discrepancy detected."""
        tracker = DiscrepancyTracker()

        # Mock backend call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        tracker._client = mock_client

        await tracker.track(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
            scan_id="scan-456",
            tenant_id="udenar",
        )

        # Verify backend was called
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_continues_despite_backend_failure(self):
        """Test track continues and returns record even if backend fails."""
        tracker = DiscrepancyTracker()

        # Mock backend failure
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        tracker._client = mock_client

        result = await tracker.track(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="gemini",
        )

        # Should still return record despite backend failure
        assert isinstance(result, DiscrepancyRecord)
        assert result.fast_path_material == Material.PLASTIC
        assert result.ground_truth_material == Material.METAL

    @pytest.mark.asyncio
    async def test_track_with_all_optional_fields(self):
        """Test track with all optional fields populated."""
        tracker = DiscrepancyTracker()

        # Mock backend call
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        tracker._client = mock_client

        result = await tracker.track(
            trace_id="trace-123",
            fast_path_material=Material.PLASTIC,
            fast_path_confidence=0.72,
            fast_path_model="roboflow/model",
            ground_truth_material=Material.METAL,
            ground_truth_confidence=0.94,
            ground_truth_model="google/gemini-2.0-flash",
            scan_id="scan-456",
            tenant_id="udenar",
            station_id="station-1",
            image_url="s3://agent-hub/scans/scan-456.jpg",
        )

        assert result.scan_id == "scan-456"
        assert result.tenant_id == "udenar"
        assert result.station_id == "station-1"
        assert result.image_url == "s3://agent-hub/scans/scan-456.jpg"


class TestClose:
    """Tests for cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_close_when_client_exists(self):
        """Test close() properly closes HTTP client."""
        tracker = DiscrepancyTracker()

        # Create mock client
        mock_client = AsyncMock()
        tracker._client = mock_client

        await tracker.close()

        # Verify client was closed
        mock_client.aclose.assert_called_once()
        assert tracker._client is None

    @pytest.mark.asyncio
    async def test_close_when_client_is_none(self):
        """Test close() handles None client gracefully."""
        tracker = DiscrepancyTracker()

        # Should not raise exception
        await tracker.close()

        assert tracker._client is None


class TestGetClient:
    """Tests for HTTP client lazy initialization."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client_on_first_call(self):
        """Test _get_client creates new client on first call."""
        tracker = DiscrepancyTracker()

        assert tracker._client is None

        client = await tracker._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert tracker._client is client

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self):
        """Test _get_client reuses existing client."""
        tracker = DiscrepancyTracker()

        client1 = await tracker._get_client()
        client2 = await tracker._get_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_client_timeout_configuration(self):
        """Test _get_client configures 10s timeout."""
        tracker = DiscrepancyTracker()

        client = await tracker._get_client()

        assert client.timeout.connect == 10.0
