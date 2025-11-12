"""
Simple smoke test for PreValidator Agent.

Usage examples:

  # Test with a sample waste image URL
  python scripts/smoke_pre_validator.py --image-url "https://upload.wikimedia.org/wikipedia/commons/3/3a/Plastic_bottle.jpg"

  # Test with verbose output
  python scripts/smoke_pre_validator.py --image-url "https://..." --verbose

  # Test expected non-waste (selfie, landscape)
  python scripts/smoke_pre_validator.py --image-url "https://..." --expect-no-waste

Requires valid API key in .env:
  - OPENAI_API_KEY for GPT-4o-mini
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
    parser = argparse.ArgumentParser(description="Smoke test for PreValidator")
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
        help="Expect has_waste=False (for testing rejection of selfies, etc.)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Timeout in seconds (default: 2.0 for testing)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("PreValidator Agent - Smoke Test")
    print("=" * 50)
    print(f"Image URL: {args.image_url}")
    print(f"Timeout: {args.timeout}s")
    print(f"Expecting waste: {not args.expect_no_waste}")
    print("=" * 50 + "\n")

    try:
        # Download image
        print("📥 Downloading image...")
        image_bytes = await download_image(args.image_url)
        print(f"✅ Downloaded {len(image_bytes)} bytes\n")

        # Run PreValidator
        print("🤖 Running PreValidator...")
        async with PreValidator(timeout=args.timeout) as validator:
            result = await validator.validate(image_bytes, "smoke-test-trace")

        # Display results
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"has_waste: {result.has_waste}")
        print(f"confidence: {result.confidence:.2f}")
        print(f"reason: {result.reason}")
        print("=" * 50 + "\n")

        # Verify expectations
        if args.expect_no_waste and result.has_waste:
            print("❌ FAILED: Expected has_waste=False but got True")
            sys.exit(1)
        elif not args.expect_no_waste and not result.has_waste:
            print("❌ FAILED: Expected has_waste=True but got False")
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

