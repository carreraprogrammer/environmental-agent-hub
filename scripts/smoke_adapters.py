"""
Simple smoke test for OpenAI, Google Gemini, and Roboflow adapters.

This script exercises the **V3-style** `classify(image_url)` method to quickly
verify that adapters are correctly configured and can return a basic
`ClassificationResult` (material + confidence).

For full V4 unified classification (MaterialClassifier + `classify_material`),
see the MaterialClassifier tests and integration pipeline.

Usage examples:

  # Test all providers with a sample plastic bottle image
  python scripts/smoke_adapters.py --image-url "https://upload.wikimedia.org/wikipedia/commons/3/3a/Plastic_bottle.jpg"

  # Test only OpenAI
  python scripts/smoke_adapters.py --provider openai --image-url "https://.../image.jpg"

  # Test only Gemini
  python scripts/smoke_adapters.py --provider gemini --image-url "https://.../image.jpg"

  # Test only Roboflow
  python scripts/smoke_adapters.py --provider roboflow --image-url "https://.../image.jpg"

  # Show verbose output with raw responses
  python scripts/smoke_adapters.py --provider all --image-url "https://.../image.jpg" --verbose

Requires valid API keys in .env:
  - OPENAI_API_KEY for OpenAI
  - GOOGLE_API_KEY for Gemini
  - ROBOFLOW_API_KEY for Roboflow
  - ROBOFLOW_MODEL_ID for Roboflow (format: workspace/project/version)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Literal

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.schemas.domain import ClassificationResult


async def run_openai(image_url: str) -> ClassificationResult:
    adapter = OpenAIClassifierAdapter()
    return await adapter.classify(image_url)


async def run_gemini(image_url: str) -> ClassificationResult:
    adapter = GoogleClassifierAdapter()
    return await adapter.classify(image_url)


async def run_roboflow(image_url: str) -> ClassificationResult:
    adapter = RoboflowClassifierAdapter()
    return await adapter.classify(image_url)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for adapters")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "roboflow", "all"],
        default="all",
        help="Which provider to test",
    )
    parser.add_argument(
        "--image-url",
        required=True,
        help="Publicly accessible image URL (jpg/png)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print raw response and extra details",
    )
    args = parser.parse_args()

    providers: list[Literal["openai", "gemini", "roboflow"]]
    if args.provider == "all":
        providers = ["openai", "gemini", "roboflow"]
    else:
        providers = [args.provider]

    for p in providers:
        print("\n======================")
        print(f"Testing provider: {p}")
        print("======================")
        try:
            if p == "openai":
                result = await run_openai(args.image_url)
            elif p == "gemini":
                result = await run_gemini(args.image_url)
            else:  # roboflow
                result = await run_roboflow(args.image_url)

            print(
                "Result:",
                {
                    "material": result.material.value,
                    "confidence": result.confidence,
                    "model_used": result.model_used,
                    "model_provider": result.model_provider,
                },
            )
            if args.verbose:
                print("raw_response:", result.raw_response)
        except Exception as e:  # pragma: no cover - smoke test convenience
            print(f"Error testing {p}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
