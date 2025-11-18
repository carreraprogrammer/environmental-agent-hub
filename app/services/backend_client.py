"""
Backend client for Rails API integration.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


class BackendClient:
    """
    Client for backend Rails API integration.

    Handles communication with the Rails backend including
    sending classifications and fetching catalogs.
    """

    # Timeout for waste types catalog fetch (5 seconds)
    CATALOG_TIMEOUT = 5.0

    def __init__(self) -> None:
        """Initialize BackendClient with settings."""
        self.base_url = settings.BACKEND_API_URL
        self.timeout = settings.BACKEND_TIMEOUT

    def send_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Placeholder method for sending classification results.

        Args:
            payload: Classification payload

        Returns:
            dict: Placeholder response
        """
        return {"status": "queued", "payload": payload}

    async def get_waste_types_catalog(self) -> list[dict[str, Any]]:
        """
        Fetch waste types catalog from Backend Rails.

        Makes GET request to /api/v1/waste_types endpoint.

        Returns:
            List of waste type definitions from backend

        Raises:
            TimeoutException: If request times out (5s)
            HTTPStatusError: If response status is not 2xx
            Exception: For other network/parsing errors
        """
        url = f"{self.base_url}/waste_types"

        try:
            async with httpx.AsyncClient(timeout=self.CATALOG_TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()

                # Handle both direct array and wrapped response
                if isinstance(data, list):
                    catalog = data
                elif isinstance(data, dict) and "waste_types" in data:
                    catalog = data["waste_types"]
                else:
                    catalog = []

                logger.info(
                    "backend_waste_types_fetched",
                    url=url,
                    count=len(catalog),
                )

                return catalog

        except httpx.TimeoutException as e:
            logger.error(
                "backend_waste_types_timeout",
                url=url,
                timeout=self.CATALOG_TIMEOUT,
                error=str(e),
            )
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "backend_waste_types_http_error",
                url=url,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise

        except Exception as e:
            logger.error(
                "backend_waste_types_error",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
