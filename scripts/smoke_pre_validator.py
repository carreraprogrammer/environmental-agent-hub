"""
Simple smoke test for PreValidator Agent V4 (Roboflow + technical validation).

Usage examples:

  # Test with a sample waste image URL
  python scripts/smoke_pre_validator.py --image-url "https://upload.wikimedia.org/wikipedia/commons/3/3a/Plastic_bottle.jpg"

  # Test with verbose output
  python scripts/smoke_pre_validator.py --image-url "https://..." --verbose

  # Test expected non-waste (selfie, landscape)
  python scripts/smoke_pre_validator.py --image-url "https://..." --expect-no-waste

Requires valid keys in .env:
  - ROBOFLOW_API_KEY for Roboflow Object Detection
  - ROBOFLOW_MODEL_ID (workspace/project/version), e.g. "workspace/waste-hsysm/6"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx

from app.agents.pre_validator import PreValidator
from app.core.logging import logger


async def download_image(url: str) -> bytes:
    """Download image from URL and return bytes."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for PreValidator V4")
    parser.add_argument(
        "--image-url",
        required=True,
        help="Publicly accessible image URL (jpg/png)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output and logs",
    )
    parser.add_argument(
        "--expect-no-waste",
        action="store_true",
        help="Expect is_valid=False (for testing rejection of selfies, etc.)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("PreValidator Agent V4 - Smoke Test")
    print("=" * 50)
    print(f"Image URL: {args.image_url}")
    print(f"Expecting valid (waste detected): {not args.expect_no_waste}")
    print("=" * 50 + "\n")

    try:
        # Download image
        print("📥 Downloading image...")
        image_bytes = await download_image(args.image_url)
        print(f"✅ Downloaded {len(image_bytes)} bytes\n")

        # Run PreValidator V4
        print("🤖 Running PreValidator V4 (Roboflow + technical checks)...")
        validator = PreValidator()
        result = await validator.validate(image_bytes, "smoke-test-trace")

        # Display results
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"is_valid: {result.is_valid}")
        print(f"reason: {result.reason}")
        metadata = getattr(result, "metadata", {}) or {}
        detections = metadata.get("detections") or []
        classes = metadata.get("classes") or []
        print(f"num_detections: {len(detections)}")
        if classes:
            print(f"classes: {classes}")
        print(f"cost: {getattr(result, 'cost', 0.0)}")
        print(f"fallback_used: {getattr(result, 'fallback_used', False)}")
        print("=" * 50 + "\n")

        # Verify expectations
        if args.expect_no_waste and result.is_valid:
            print("❌ FAILED: Expected is_valid=False (no waste) but got True")
            sys.exit(1)
        elif not args.expect_no_waste and not result.is_valid:
            print("❌ FAILED: Expected is_valid=True (waste) but got False")
            sys.exit(1)
        else:
            print("✅ PASSED: Result matches expectations")
            sys.exit(0)

    except TimeoutError as e:
        print(f"\n❌ TIMEOUT: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    except Exception as e:  # pragma: no cover
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
