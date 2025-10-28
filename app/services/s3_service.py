"""
S3 service placeholder.
"""

from __future__ import annotations

from typing import Any


class S3Service:
    """
    Placeholder service for S3 interactions.
    """

    def upload_file(self, *, file_path: str, destination: str) -> dict[str, Any]:
        """
        Placeholder file upload.
        
        Args:
            file_path: Local file path
            destination: Destination key
        
        Returns:
            dict: Placeholder upload metadata
        """
        return {"file_path": file_path, "destination": destination, "status": "pending"}
