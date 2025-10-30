"""
Backend client placeholder.
"""

from __future__ import annotations

from typing import Any


class BackendClient:
    """
    Placeholder client for backend integration.
    """

    def send_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Placeholder method for sending classification results.
        
        Args:
            payload: Classification payload
        
        Returns:
            dict: Placeholder response
        """
        return {"status": "queued", "payload": payload}
