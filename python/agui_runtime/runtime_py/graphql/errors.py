"""
GraphQL error handling for CopilotKit Python Runtime.

This module provides standardized error handling for GraphQL operations,
including error code mapping, structured error responses, and error recovery
mechanisms. All errors are mapped to GraphQL-compliant error responses.
"""

from __future__ import annotations

import logging
import traceback
from enum import Enum
from typing import Any

import strawberry
from strawberry.types import ExecutionResult


@strawberry.enum
class CopilotErrorCode(Enum):
    """Standardized error codes for CopilotKit operations."""

    # Generic errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Authentication/Authorization errors
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # Input validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_THREAD_ID = "INVALID_THREAD_ID"
    INVALID_AGENT_NAME = "INVALID_AGENT_NAME"

    # Provider errors
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_INITIALIZATION_FAILED = "PROVIDER_INITIALIZATION_FAILED"
    PROVIDER_EXECUTION_FAILED = "PROVIDER_EXECUTION_FAILED"

    # Agent errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    AGENT_EXECUTION_TIMEOUT = "AGENT_EXECUTION_TIMEOUT"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"

    # State management errors
    STATE_STORE_UNAVAILABLE = "STATE_STORE_UNAVAILABLE"
    STATE_NOT_FOUND = "STATE_NOT_FOUND"
    STATE_SAVE_FAILED = "STATE_SAVE_FAILED"
    STATE_LOAD_FAILED = "STATE_LOAD_FAILED"
    STATE_CORRUPTION = "STATE_CORRUPTION"

    # Runtime errors
    RUNTIME_NOT_INITIALIZED = "RUNTIME_NOT_INITIALIZED"
    RUNTIME_OVERLOADED = "RUNTIME_OVERLOADED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    OPERATION_CANCELLED = "OPERATION_CANCELLED"

    # Network/External errors
    NETWORK_ERROR = "NETWORK_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Resource errors
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Configuration errors
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    MISSING_CONFIGURATION = "MISSING_CONFIGURATION"


class CopilotKitError(Exception):
    """
    Base exception class for CopilotKit Runtime errors.

    This exception provides structured error information that can be
    properly converted to GraphQL error responses.
    """

    def __init__(
        self,
        message: str,
        error_code: CopilotErrorCode = CopilotErrorCode.UNKNOWN_ERROR,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        recoverable: bool = False,
        user_facing: bool = True,
    ) -> None:
        """
        Initialize CopilotKit error.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            details: Additional error details and context
            correlation_id: Request correlation ID for tracing
            recoverable: Whether the error is recoverable
            user_facing: Whether the error should be shown to users
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id
        self.recoverable = recoverable
        self.user_facing = user_facing

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "message": self.message,
            "error_code": self.error_code.value,
            "details": self.details,
            "correlation_id": self.correlation_id,
            "recoverable": self.recoverable,
            "user_facing": self.user_facing,
        }

    def __str__(self) -> str:
        """String representation of the error."""
        return f"[{self.error_code.value}] {self.message}"


class AuthenticationError(CopilotKitError):
    """Authentication-related errors."""

    def __init__(self, message: str = "Authentication required", **kwargs: Any) -> None:
        super().__init__(
            message,
            error_code=CopilotErrorCode.AUTHENTICATION_REQUIRED,
            user_facing=True,
            **kwargs
        )


class AuthorizationError(CopilotKitError):
    """Authorization-related errors."""

    def __init__(self, message: str = "Access denied", **kwargs: Any) -> None:
        super().__init__(
            message,
            error_code=CopilotErrorCode.AUTHORIZATION_DENIED,
            user_facing=True,
            **kwargs
        )


class ProviderError(CopilotKitError):
    """Provider-related errors."""

    def __init__(self, message: str, provider_name: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {})
        details["provider_name"] = provider_name

        super().__init__(
            message,
            error_code=CopilotErrorCode.PROVIDER_EXECUTION_FAILED,
            details=details,
            recoverable=True,
            **kwargs
        )


class AgentError(CopilotKitError):
    """Agent-related errors."""

    def __init__(self, message: str, agent_name: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {})
        details["agent_name"] = agent_name

        super().__init__(
            message,
            error_code=CopilotErrorCode.AGENT_EXECUTION_FAILED,
            details=details,
            recoverable=True,
            **kwargs
        )


class StateStoreError(CopilotKitError):
    """State store-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message,
            error_code=CopilotErrorCode.STATE_STORE_UNAVAILABLE,
            recoverable=True,
            **kwargs
        )


def map_exception_to_error(
    exception: Exception,
    correlation_id: str | None = None,
    operation_name: str | None = None,
) -> CopilotKitError:
    """
    Map generic exceptions to CopilotKit errors.

    Args:
        exception: The original exception
        correlation_id: Request correlation ID
        operation_name: Name of the operation that failed

    Returns:
        Mapped CopilotKitError
    """
    if isinstance(exception, CopilotKitError):
        return exception

    # Map common exception types
    exception_mappings = {
        ValueError: CopilotErrorCode.INVALID_INPUT,
        TypeError: CopilotErrorCode.INVALID_INPUT,
        KeyError: CopilotErrorCode.MISSING_REQUIRED_FIELD,
        FileNotFoundError: CopilotErrorCode.STATE_NOT_FOUND,
        ConnectionError: CopilotErrorCode.NETWORK_ERROR,
        TimeoutError: CopilotErrorCode.OPERATION_TIMEOUT,
        PermissionError: CopilotErrorCode.AUTHORIZATION_DENIED,
    }

    error_code = exception_mappings.get(type(exception), CopilotErrorCode.INTERNAL_ERROR)

    # Create user-friendly message based on error type
    if error_code == CopilotErrorCode.INVALID_INPUT:
        user_message = "Invalid input provided. Please check your request."
    elif error_code == CopilotErrorCode.NETWORK_ERROR:
        user_message = "Network error occurred. Please try again."
    elif error_code == CopilotErrorCode.OPERATION_TIMEOUT:
        user_message = "Operation timed out. Please try again."
    else:
        user_message = "An unexpected error occurred. Please try again."

    details = {
        "original_exception": str(exception),
        "exception_type": type(exception).__name__,
    }

    if operation_name:
        details["operation_name"] = operation_name

    return CopilotKitError(
        message=user_message,
        error_code=error_code,
        details=details,
        correlation_id=correlation_id,
        recoverable=True,
        user_facing=True,
    )


def create_graphql_error(
    error: CopilotKitError,
    path: list[str | int] | None = None,
    locations: list[dict[str, int]] | None = None,
) -> dict[str, Any]:
    """
    Create a GraphQL-compliant error response.

    Args:
        error: CopilotKitError to convert
        path: GraphQL path where error occurred
        locations: GraphQL locations where error occurred

    Returns:
        GraphQL error dictionary
    """
    graphql_error = {
        "message": error.message if error.user_facing else "An error occurred",
        "extensions": {
            "code": error.error_code.value,
            "correlation_id": error.correlation_id,
            "recoverable": error.recoverable,
        }
    }

    # Add details for internal errors
    if not error.user_facing:
        graphql_error["extensions"]["details"] = error.details

    # Add path and locations if provided
    if path is not None:
        graphql_error["path"] = path

    if locations is not None:
        graphql_error["locations"] = locations

    return graphql_error


def log_graphql_error(
    error: CopilotKitError,
    logger: logging.Logger,
    operation_name: str | None = None,
) -> None:
    """
    Log GraphQL error with appropriate level and context.

    Args:
        error: Error to log
        logger: Logger instance
        operation_name: GraphQL operation name
    """
    log_context = {
        "error_code": error.error_code.value,
        "correlation_id": error.correlation_id,
        "recoverable": error.recoverable,
        "user_facing": error.user_facing,
        "details": error.details,
    }

    if operation_name:
        log_context["operation_name"] = operation_name

    # Log level based on error severity
    if error.error_code in [
        CopilotErrorCode.INTERNAL_ERROR,
        CopilotErrorCode.RUNTIME_NOT_INITIALIZED,
        CopilotErrorCode.STATE_CORRUPTION,
    ]:
        logger.error(f"Critical error: {error.message}", extra=log_context)
    elif error.recoverable:
        logger.warning(f"Recoverable error: {error.message}", extra=log_context)
    else:
        logger.info(f"User error: {error.message}", extra=log_context)


def handle_resolver_exception(
    exception: Exception,
    resolver_name: str,
    logger: logging.Logger,
    correlation_id: str | None = None,
    include_traceback: bool = False,
) -> CopilotKitError:
    """
    Handle exceptions that occur in GraphQL resolvers.

    Args:
        exception: Exception that occurred
        resolver_name: Name of the resolver
        logger: Logger instance
        correlation_id: Request correlation ID
        include_traceback: Whether to include traceback in details

    Returns:
        Processed CopilotKitError
    """
    # Map the exception to a CopilotKit error
    copilot_error = map_exception_to_error(
        exception,
        correlation_id=correlation_id,
        operation_name=resolver_name,
    )

    # Add traceback if requested (for debugging)
    if include_traceback and not isinstance(exception, CopilotKitError):
        copilot_error.details["traceback"] = traceback.format_exc()

    # Log the error
    log_graphql_error(copilot_error, logger, resolver_name)

    return copilot_error


def create_error_response(
    error: CopilotKitError,
    default_value: Any = None,
) -> Any:
    """
    Create a fallback response for GraphQL operations that encounter errors.

    Args:
        error: Error that occurred
        default_value: Default value to return

    Returns:
        Error response or default value
    """
    if error.recoverable and default_value is not None:
        return default_value

    # For non-recoverable errors, raise them to be handled by GraphQL
    raise error


# Error recovery strategies
class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""

    @staticmethod
    def can_recover(error: CopilotKitError) -> bool:
        """Check if error can be recovered from."""
        return error.recoverable

    @staticmethod
    def get_fallback_response(error: CopilotKitError, operation_type: str) -> Any:
        """Get fallback response for different operation types."""
        if operation_type == "agents_query":
            return {"agents": []}
        elif operation_type == "runtime_info_query":
            return {
                "version": "unknown",
                "providers": [],
                "agents_count": 0
            }
        elif operation_type == "generate_response_mutation":
            return {
                "thread_id": error.details.get("thread_id", "unknown"),
                "messages": [],
                "status": "ERROR",
                "error_message": error.message if error.user_facing else "An error occurred"
            }
        elif operation_type == "load_agent_state_query":
            return {
                "thread_id": error.details.get("thread_id", "unknown"),
                "agent_name": error.details.get("agent_name", "unknown"),
                "state_data": None,
                "state_found": False,
                "error_message": error.message if error.user_facing else None
            }
        elif operation_type == "save_agent_state_mutation":
            return {
                "thread_id": error.details.get("thread_id", "unknown"),
                "agent_name": error.details.get("agent_name", "unknown"),
                "success": False,
                "error_message": error.message if error.user_facing else None
            }

        return None


# Export public API
__all__ = [
    "CopilotErrorCode",
    "CopilotKitError",
    "AuthenticationError",
    "AuthorizationError",
    "ProviderError",
    "AgentError",
    "StateStoreError",
    "map_exception_to_error",
    "create_graphql_error",
    "log_graphql_error",
    "handle_resolver_exception",
    "create_error_response",
    "ErrorRecoveryStrategy",
]
