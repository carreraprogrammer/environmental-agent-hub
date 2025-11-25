"""
E2E tests for POST /classify endpoint with real pipeline execution.

These tests execute the COMPLETE pipeline without mocks:
- Real LLM API calls (OpenAI, Anthropic, Gemini)
- Real Roboflow waste detection
- Real image processing
- Real latency measurements
- Real cost tracking

REQUIREMENTS:
1. API keys configured in .env:
   - OPENAI_API_KEY
   - ANTHROPIC_API_KEY (optional)
   - ROBOFLOW_API_KEY
   - GOOGLE_API_KEY (optional)

2. Test images available in tests/fixtures/images/

USAGE:
    # Run E2E tests with real API calls
    RUN_E2E_TESTS=1 pytest tests/integration/test_classify_endpoint_e2e.py -v -s

    # Skip E2E tests (default in CI)
    pytest tests/integration/test_classify_endpoint_e2e.py -v

COST WARNING:
    These tests make real API calls and will incur costs:
    - ~$0.01-0.02 per test with OpenAI GPT-4o
    - ~$0.001 per test with Roboflow
    Total: ~$0.05-0.10 per full test run

PERFORMANCE METRICS:
    Tests measure and report:
    - Total request latency (target: <3000ms)
    - Pipeline execution time
    - Individual agent latencies
    - API costs
"""

from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.classification import Material

# Skip all E2E tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_E2E_TESTS"),
    reason="E2E tests disabled (set RUN_E2E_TESTS=1 to enable). These tests make real API calls and incur costs."
)

client = TestClient(app)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "images"


class TestClassifyEndpointE2EMultipart:
    """E2E tests for multipart/form-data format with real pipeline."""

    def test_classify_real_pet_bottle_multipart(self) -> None:
        """
        E2E test: Classify real PET bottle image with complete pipeline.

        This test:
        - Uses a real PET bottle image
        - Executes full pipeline (PreValidator → MaterialClassifier → etc.)
        - Makes real API calls to LLMs
        - Measures actual latency
        - Verifies correct classification

        Expected result: PLASTIC classification with high confidence
        """
        # Arrange
        scan_id = str(uuid4())
        trace_id = str(uuid4())

        # Load real test image
        image_path = FIXTURES_DIR / "pet_bottle.jpg"
        assert image_path.exists(), f"Test image not found: {image_path}"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"\n🧪 E2E Test: Real PET Bottle Classification")
        print(f"   Image: {image_path.name} ({len(image_bytes)} bytes)")
        print(f"   Trace ID: {trace_id}")

        # Act
        start_time = time.time()
        response = client.post(
            "/api/v1/classify",
            files={"image": ("pet_bottle.jpg", BytesIO(image_bytes), "image/jpeg")},
            data={
                "scan_id": scan_id,
                "station_id": "TEST-E2E-01",
                "tenant_id": "e2e-test",
                "trace_id": trace_id,
            },
        )
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Assert
        print(f"\n📊 Results:")
        print(f"   Status: {response.status_code}")
        print(f"   Latency: {elapsed_ms}ms")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Print classification results
        print(f"   Material: {data['material']} (confidence: {data['confidence']:.2f})")
        print(f"   Bin Color: {data['color']}")
        print(f"   Waste Type: {data['waste_type_code']}")
        print(f"   Volume: {data['volume_ml']}ml")
        print(f"   Weight: {data['weight_g']}g")

        # Print metadata
        meta = data['meta']
        print(f"\n🔧 Pipeline Metadata:")
        print(f"   Model: {meta['model_used']}")
        print(f"   Provider: {meta['model_provider']}")
        print(f"   Pipeline Latency: {meta['latency_ms']}ms")
        print(f"   Cost: ${meta['cost_usd']:.4f}")
        print(f"   Validator Passed: {meta['validator_passed']}")
        print(f"   Input Format: {meta['input_format']}")
        print(f"   S3 Upload Status: {meta['s3_upload_status']}")
        print(f"   Agents Executed: {', '.join(meta['agents_executed'])}")

        # Verify classification correctness
        assert data["material"] == "PLASTIC", f"Expected PLASTIC, got {data['material']}"
        assert data["confidence"] >= 0.70, f"Confidence too low: {data['confidence']}"
        assert data["color"] in ["WHITE", "BLUE", "YELLOW"], f"Unexpected bin color: {data['color']}"

        # Verify metadata
        assert meta["validator_passed"] is True, "PreValidator should have passed"
        assert meta["input_format"] == "bytes"
        assert meta["s3_upload_status"] == "pending"
        assert len(meta["agents_executed"]) > 0, "No agents executed"

        # Verify response headers
        assert "X-Trace-Id" in response.headers
        assert response.headers["X-Trace-Id"] == trace_id
        assert "X-Request-Duration" in response.headers

        # Performance assertion (target: <3000ms for complete pipeline)
        assert elapsed_ms < 5000, f"Request too slow: {elapsed_ms}ms (target: <5000ms)"

        # Cost assertion (should be reasonable)
        assert meta["cost_usd"] < 0.05, f"Cost too high: ${meta['cost_usd']}"

        print(f"\n✅ E2E Test PASSED")
        print(f"   Total Latency: {elapsed_ms}ms (target: <5000ms)")
        print(f"   Pipeline Latency: {meta['latency_ms']}ms")
        print(f"   Overhead: {elapsed_ms - meta['latency_ms']}ms (networking, serialization)")

    def test_classify_blurry_bottle_multipart(self) -> None:
        """
        E2E test: Classify blurry PET bottle image.

        Tests handling of poor quality images that might:
        - Have lower confidence scores
        - Still pass validation but with lower certainty
        - Take longer to process

        Expected: PLASTIC classification but potentially lower confidence
        """
        # Arrange
        scan_id = str(uuid4())
        image_path = FIXTURES_DIR / "pet_bottle_blurry.jpg"
        assert image_path.exists(), f"Test image not found: {image_path}"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"\n🧪 E2E Test: Blurry PET Bottle Classification")
        print(f"   Image: {image_path.name}")

        # Act
        start_time = time.time()
        response = client.post(
            "/api/v1/classify",
            files={"image": ("pet_bottle_blurry.jpg", BytesIO(image_bytes), "image/jpeg")},
            data={
                "scan_id": scan_id,
                "station_id": "TEST-E2E-01",
                "tenant_id": "e2e-test",
            },
        )
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Assert
        print(f"\n📊 Results:")
        print(f"   Status: {response.status_code}")
        print(f"   Latency: {elapsed_ms}ms")

        # Blurry images might be rejected OR classified with lower confidence
        if response.status_code == 400:
            data = response.json()
            print(f"   ⚠️  Rejected: {data['detail']['error_code']}")
            print(f"   Message: {data['detail']['message']}")
            # This is acceptable for very blurry images
            assert data['detail']['error_code'] in ["LOW_CONFIDENCE", "NO_WASTE_DETECTED"]
        else:
            assert response.status_code == 200
            data = response.json()
            print(f"   Material: {data['material']} (confidence: {data['confidence']:.2f})")
            # Blurry images should have lower confidence
            assert data["confidence"] >= 0.50, "Confidence should be at least 0.50 for accepted classifications"

        print(f"✅ E2E Test PASSED (blurry image handling)")


class TestClassifyEndpointE2EValidationErrors:
    """E2E tests for validation errors with real pipeline."""

    def test_classify_no_waste_food_image(self) -> None:
        """
        E2E test: Submit food image (not waste).

        Expected: ValidationError NO_WASTE_DETECTED or similar rejection
        """
        # Arrange
        scan_id = str(uuid4())
        image_path = FIXTURES_DIR / "food.jpg"
        assert image_path.exists(), f"Test image not found: {image_path}"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"\n🧪 E2E Test: Food Image (Not Waste) - Should Reject")
        print(f"   Image: {image_path.name}")

        # Act
        response = client.post(
            "/api/v1/classify",
            files={"image": ("food.jpg", BytesIO(image_bytes), "image/jpeg")},
            data={
                "scan_id": scan_id,
                "station_id": "TEST-E2E-01",
                "tenant_id": "e2e-test",
            },
        )

        # Assert
        print(f"\n📊 Results:")
        print(f"   Status: {response.status_code}")

        # Should reject non-waste images
        assert response.status_code == 400, "Food image should be rejected"

        data = response.json()
        print(f"   Error Code: {data['detail']['error_code']}")
        print(f"   Message: {data['detail']['message']}")
        print(f"   Suggestion: {data['detail']['suggestion']}")

        assert data['detail']['error_code'] in ["NO_WASTE_DETECTED", "VALIDATION_FAILED"]
        assert "suggestion" in data['detail']

        print(f"✅ E2E Test PASSED (correctly rejected non-waste)")

    def test_classify_person_image(self) -> None:
        """
        E2E test: Submit person image.

        Expected: ValidationError NO_WASTE_DETECTED (anti-troll)
        """
        # Arrange
        scan_id = str(uuid4())
        image_path = FIXTURES_DIR / "person.jpg"
        assert image_path.exists(), f"Test image not found: {image_path}"

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"\n🧪 E2E Test: Person Image - Should Reject (Anti-Troll)")
        print(f"   Image: {image_path.name}")

        # Act
        response = client.post(
            "/api/v1/classify",
            files={"image": ("person.jpg", BytesIO(image_bytes), "image/jpeg")},
            data={
                "scan_id": scan_id,
                "station_id": "TEST-E2E-01",
                "tenant_id": "e2e-test",
            },
        )

        # Assert
        print(f"\n📊 Results:")
        print(f"   Status: {response.status_code}")

        assert response.status_code == 400, "Person image should be rejected"

        data = response.json()
        print(f"   Error Code: {data['detail']['error_code']}")
        print(f"   Message: {data['detail']['message']}")

        assert data['detail']['error_code'] == "NO_WASTE_DETECTED"

        print(f"✅ E2E Test PASSED (anti-troll working)")


class TestClassifyEndpointE2EPerformance:
    """E2E performance tests with real pipeline."""

    def test_classify_performance_multiple_requests(self) -> None:
        """
        E2E test: Measure performance over multiple requests.

        Executes 3 sequential requests and measures:
        - Average latency
        - Latency consistency (std deviation)
        - Total cost
        """
        # Arrange
        image_path = FIXTURES_DIR / "pet_bottle.jpg"
        assert image_path.exists()

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        num_requests = 3
        latencies = []
        costs = []

        print(f"\n🧪 E2E Performance Test: {num_requests} Sequential Requests")

        # Act - Execute multiple requests
        for i in range(num_requests):
            scan_id = str(uuid4())

            start_time = time.time()
            response = client.post(
                "/api/v1/classify",
                files={"image": (f"test_{i}.jpg", BytesIO(image_bytes), "image/jpeg")},
                data={
                    "scan_id": scan_id,
                    "station_id": "TEST-E2E-PERF",
                    "tenant_id": "e2e-test",
                },
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            assert response.status_code == 200, f"Request {i+1} failed"

            data = response.json()
            latencies.append(elapsed_ms)
            costs.append(data['meta']['cost_usd'])

            print(f"   Request {i+1}: {elapsed_ms}ms, ${data['meta']['cost_usd']:.4f}")

        # Assert - Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        total_cost = sum(costs)

        print(f"\n📊 Performance Statistics:")
        print(f"   Average Latency: {avg_latency:.0f}ms")
        print(f"   Min Latency: {min_latency}ms")
        print(f"   Max Latency: {max_latency}ms")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Avg Cost per Request: ${total_cost/num_requests:.4f}")

        # Performance assertions
        assert avg_latency < 5000, f"Average latency too high: {avg_latency}ms"
        assert max_latency < 8000, f"Max latency too high: {max_latency}ms"
        assert total_cost < 0.15, f"Total cost too high: ${total_cost}"

        print(f"✅ E2E Performance Test PASSED")


class TestClassifyEndpointE2EJSON:
    """E2E tests for JSON format (legacy) with real pipeline."""

    @pytest.mark.skip(reason="Requires accessible image URL - implement when S3 URLs are available")
    def test_classify_json_with_url(self) -> None:
        """
        E2E test: Classify using JSON format with image URL.

        Note: Skipped by default as it requires a publicly accessible image URL.
        Enable when S3 integration is complete.
        """
        # Arrange
        scan_id = str(uuid4())
        # TODO: Replace with actual accessible S3 URL
        image_url = "https://example.com/test-pet-bottle.jpg"

        print(f"\n🧪 E2E Test: JSON Format with URL")
        print(f"   URL: {image_url}")

        # Act
        response = client.post(
            "/api/v1/classify",
            json={
                "scan_id": scan_id,
                "station_id": "TEST-E2E-JSON",
                "image_url": image_url,
                "tenant_id": "e2e-test",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['meta']['input_format'] == "url"

        print(f"✅ E2E JSON Test PASSED")


# Pytest configuration to add --e2e flag
def pytest_addoption(parser):
    """Add custom command line option for E2E tests."""
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run E2E tests with real API calls (costs money)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip E2E tests unless --e2e flag is used or RUN_E2E_TESTS=1."""
    if not config.getoption("--e2e") and not os.getenv("RUN_E2E_TESTS"):
        skip_e2e = pytest.mark.skip(
            reason="E2E tests require --e2e flag or RUN_E2E_TESTS=1 (makes real API calls, costs money)"
        )
        for item in items:
            if "test_classify_endpoint_e2e" in str(item.fspath):
                item.add_marker(skip_e2e)
