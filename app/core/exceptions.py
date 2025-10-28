"""
Custom exceptions for Agent Hub.

Defines domain-specific exceptions with error codes and user-friendly messages.
"""

from __future__ import annotations


class AgentHubException(Exception):
    """
    Base exception for all Agent Hub errors.
    
    Attributes:
        error_code: Unique error code
        message: User-friendly error message
        suggestion: Suggested action for user
    """
    
    def __init__(
        self,
        error_code: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """
        Initialize exception.
        
        Args:
            error_code: Unique error identifier
            message: User-friendly error description
            suggestion: Optional suggested action
        """
        self.error_code = error_code
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)
    
    def to_dict(self) -> dict[str, str]:
        """
        Convert exception to dictionary format.
        
        Returns:
            dict: Error information
        """
        result = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


class ValidationError(AgentHubException):
    """
    Raised when request validation fails.
    
    Examples:
        - Invalid image URL
        - Missing required fields
        - Invalid format
    """
    pass


class ClassificationError(AgentHubException):
    """
    Raised when classification fails.
    
    Examples:
        - LLM API error
        - Timeout
        - Invalid response
    """
    pass


class ConfigurationError(AgentHubException):
    """
    Raised when configuration is invalid.
    
    Examples:
        - Missing API keys
        - Invalid model selection
        - Invalid settings
    """
    pass
