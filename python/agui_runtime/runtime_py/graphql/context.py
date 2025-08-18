"""
GraphQL execution context for CopilotKit Python Runtime.

This module provides the GraphQL execution context that carries runtime
references, request information, and operation context through all GraphQL
resolvers, enabling proper orchestration and request lifecycle management.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agui_runtime.runtime_py.core.runtime import CopilotRuntime


class GraphQLExecutionContext:
    """
    GraphQL execution context carrying runtime and request information.

    This context is created for each GraphQL request and provides:
    - Runtime reference for orchestration
    - Request correlation ID and tracking
    - Operation logging and monitoring
    - Authentication and authorization context
    - Request-specific configuration
    """

    def __init__(
        self,
        runtime: CopilotRuntime,
        request: Any = None,
        correlation_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        client_info: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize GraphQL execution context.

        Args:
            runtime: CopilotRuntime instance for orchestration
            request: FastAPI request object
            correlation_id: Request correlation ID for tracing
            user_id: Authenticated user ID
            session_id: Session identifier
            client_info: Client information and metadata
        """
        self.runtime = runtime
        self.request = request
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.client_info = client_info or {}

        # Request tracking
        self.created_at = datetime.datetime.utcnow()
        self.operations_logged: list[dict[str, Any]] = []

        # Logging setup
        self.logger = logging.getLogger(f"{__name__}.{self.correlation_id[:8]}")

        # Performance tracking
        self.performance_metrics: dict[str, Any] = {}

        # Request state
        self.is_authenticated = user_id is not None
        self.request_metadata: dict[str, Any] = {}

    def log_operation(
        self,
        operation_name: str,
        operation_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a GraphQL operation for monitoring and debugging.

        Args:
            operation_name: Name of the GraphQL operation
            operation_type: Type of operation (query, mutation, subscription)
            details: Additional operation details
        """
        operation_log = {
            "operation_name": operation_name,
            "operation_type": operation_type,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "details": details or {},
        }

        self.operations_logged.append(operation_log)

        self.logger.info(
            f"GraphQL {operation_type}: {operation_name}",
            extra={
                "correlation_id": self.correlation_id,
                "user_id": self.user_id,
                "operation_details": details,
            }
        )

    def start_performance_timer(self, operation_name: str) -> None:
        """Start a performance timer for an operation."""
        self.performance_metrics[f"{operation_name}_start"] = datetime.datetime.utcnow()

    def end_performance_timer(self, operation_name: str) -> float:
        """
        End a performance timer and return the duration.

        Args:
            operation_name: Name of the operation to time

        Returns:
            Duration in seconds
        """
        start_key = f"{operation_name}_start"
        if start_key not in self.performance_metrics:
            self.logger.warning(f"No start time found for operation: {operation_name}")
            return 0.0

        start_time = self.performance_metrics[start_key]
        end_time = datetime.datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        self.performance_metrics[f"{operation_name}_duration"] = duration

        self.logger.debug(
            f"Operation {operation_name} completed in {duration:.3f}s",
            extra={"correlation_id": self.correlation_id, "duration_seconds": duration}
        )

        return duration

    def add_request_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the request context.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.request_metadata[key] = value

    def get_request_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata from the request context.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.request_metadata.get(key, default)

    def create_child_context(self, operation_name: str) -> GraphQLExecutionContext:
        """
        Create a child context for nested operations.

        Args:
            operation_name: Name of the child operation

        Returns:
            New child context
        """
        child_correlation_id = f"{self.correlation_id}-{operation_name}"

        child_context = GraphQLExecutionContext(
            runtime=self.runtime,
            request=self.request,
            correlation_id=child_correlation_id,
            user_id=self.user_id,
            session_id=self.session_id,
            client_info=self.client_info.copy(),
        )

        # Copy relevant metadata
        child_context.request_metadata = self.request_metadata.copy()
        child_context.is_authenticated = self.is_authenticated

        return child_context

    def to_dict(self) -> dict[str, Any]:
        """
        Convert context to dictionary for logging and debugging.

        Returns:
            Dictionary representation of the context
        """
        return {
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "is_authenticated": self.is_authenticated,
            "operations_count": len(self.operations_logged),
            "client_info": self.client_info,
            "request_metadata": self.request_metadata,
            "performance_metrics": self.performance_metrics,
        }

    def __repr__(self) -> str:
        """String representation of the context."""
        return (
            f"GraphQLExecutionContext("
            f"correlation_id={self.correlation_id[:8]}..., "
            f"user_id={self.user_id}, "
            f"operations={len(self.operations_logged)}"
            f")"
        )


def create_graphql_context(
    runtime: CopilotRuntime,
    request: Any = None,
    **kwargs: Any,
) -> GraphQLExecutionContext:
    """
    Factory function to create GraphQL execution context.

    Args:
        runtime: CopilotRuntime instance
        request: FastAPI request object
        **kwargs: Additional context parameters

    Returns:
        Initialized GraphQL execution context
    """
    # Extract user information from request if available
    user_id = None
    session_id = None
    client_info = {}

    if request:
        # Extract from headers or authentication
        headers = getattr(request, "headers", {})
        user_id = headers.get("x-user-id")
        session_id = headers.get("x-session-id")

        client_info = {
            "user_agent": headers.get("user-agent"),
            "client_ip": getattr(request, "client", {}).get("host"),
            "method": getattr(request, "method", "POST"),
            "url": str(getattr(request, "url", "")),
        }

    # Override with explicit kwargs
    user_id = kwargs.get("user_id", user_id)
    session_id = kwargs.get("session_id", session_id)
    client_info.update(kwargs.get("client_info", {}))

    return GraphQLExecutionContext(
        runtime=runtime,
        request=request,
        correlation_id=kwargs.get("correlation_id"),
        user_id=user_id,
        session_id=session_id,
        client_info=client_info,
    )


# Export public API
__all__ = [
    "GraphQLExecutionContext",
    "create_graphql_context",
]
