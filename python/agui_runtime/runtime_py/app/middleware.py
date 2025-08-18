"""
Comprehensive middleware stack for CopilotKit Python Runtime.

This module provides a complete middleware setup for FastAPI applications
using the CopilotRuntime, including CORS, logging, error handling, tracing,
and authentication preparation.
"""

from __future__ import annotations

import logging
import time
import traceback
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from agui_runtime.runtime_py.core.types import RuntimeConfig


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request logging and metrics.

    Logs all HTTP requests with timing, status codes, and relevant metadata.
    Provides structured logging for monitoring and debugging.
    """

    def __init__(self, app: FastAPI, runtime_config: RuntimeConfig) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(f"{__name__}.RequestLoggingMiddleware")
        self.config = runtime_config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging and timing."""
        # Generate request ID if not already present
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Record request start time
        start_time = time.time()

        # Get request details
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params) if request.query_params else {}

        # Log request start
        self.logger.info(
            f"Request started: {method} {path}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "event": "request_start",
            },
        )

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            self.logger.error(
                f"Request error: {method} {path}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event": "request_error",
                },
                exc_info=True,
            )
            # Create error response with JSON-safe content
            error_message = "An unexpected error occurred"
            if self.config.debug:
                try:
                    error_message = str(e)
                except Exception:
                    error_message = "Error occurred but couldn't be serialized"

            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": error_message,
                    "request_id": str(request.state.request_id),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        # Calculate request duration
        duration = time.time() - start_time

        # Add response headers
        if response:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

        # Log request completion
        status_code = response.status_code if response else 500
        self.logger.info(
            f"Request completed: {method} {path} - {status_code}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "event": "request_complete",
                "error": str(error) if error else None,
            },
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers and connection info."""
        # Check for forwarded headers (common in proxy/load balancer setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive error handling middleware.

    Catches and formats all unhandled exceptions, providing consistent
    error responses and proper logging.
    """

    def __init__(self, app: FastAPI, runtime_config: RuntimeConfig) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(f"{__name__}.ErrorHandlingMiddleware")
        self.config = runtime_config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive error handling."""
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions to let FastAPI handle them
            raise
        except RequestValidationError:
            # Re-raise validation errors to let FastAPI handle them
            raise
        except Exception as e:
            # Handle all other exceptions
            request_id = getattr(request.state, "request_id", "unknown")

            # Log the error with full context
            self.logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc() if self.config.debug else None,
                    "event": "unhandled_exception",
                },
                exc_info=True,
            )

            # Create consistent error response
            error_detail = {
                "error": "Internal server error",
                "message": str(e) if self.config.debug else "An unexpected error occurred",
                "request_id": request_id,
                "type": "INTERNAL_ERROR",
            }

            # Include traceback in debug mode
            if self.config.debug:
                error_detail["traceback"] = traceback.format_exc()

            return JSONResponse(status_code=500, content=error_detail)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for future authentication integration.

    Currently provides a framework for authentication that will be
    implemented in later phases. For now, it sets up the infrastructure
    and passes through all requests.
    """

    def __init__(self, app: FastAPI, runtime_config: RuntimeConfig) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(f"{__name__}.AuthenticationMiddleware")
        self.config = runtime_config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication preparation."""
        # TODO: Implement authentication in later phases
        # For now, set up the structure and pass through

        # Extract potential authentication headers
        auth_header = request.headers.get("authorization")
        api_key = request.headers.get("x-api-key")

        # Set up authentication context for future use
        request.state.auth_header = auth_header
        request.state.api_key = api_key
        request.state.user_id = None  # Will be populated when auth is implemented
        request.state.authenticated = False  # Default to not authenticated

        # For development, allow all requests
        if self.config.debug:
            request.state.authenticated = True
            request.state.user_id = "dev_user"

        # Process request
        response = await call_next(request)

        return response


def setup_cors_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup CORS middleware with proper configuration.

    Args:
        app: FastAPI application instance
        config: Runtime configuration with CORS settings
    """
    logger = logging.getLogger(f"{__name__}.setup_cors_middleware")

    if not config.cors_origins:
        logger.info("CORS origins not configured, skipping CORS middleware")
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Request-ID",
            "Accept",
            "Accept-Language",
            "Cache-Control",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time",
        ],
    )

    logger.info(f"CORS middleware configured with origins: {config.cors_origins}")


def setup_logging_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup request logging middleware.

    Args:
        app: FastAPI application instance
        config: Runtime configuration
    """
    logger = logging.getLogger(f"{__name__}.setup_logging_middleware")

    app.add_middleware(RequestLoggingMiddleware, runtime_config=config)

    logger.info("Request logging middleware configured")


def setup_error_handling_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup comprehensive error handling middleware.

    Args:
        app: FastAPI application instance
        config: Runtime configuration
    """
    logger = logging.getLogger(f"{__name__}.setup_error_handling_middleware")

    app.add_middleware(ErrorHandlingMiddleware, runtime_config=config)

    # Also setup FastAPI's built-in exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"Request validation error: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "validation_errors": exc.errors(),
                "event": "validation_error",
            },
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "message": "Request validation failed",
                "request_id": request_id,
                "type": "VALIDATION_ERROR",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent formatting."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"HTTP exception: {request.method} {request.url.path} - {exc.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "event": "http_exception",
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP {exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
                "type": "HTTP_ERROR",
            },
        )

    logger.info("Error handling middleware configured")


def setup_authentication_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup authentication middleware framework.

    Args:
        app: FastAPI application instance
        config: Runtime configuration
    """
    logger = logging.getLogger(f"{__name__}.setup_authentication_middleware")

    app.add_middleware(AuthenticationMiddleware, runtime_config=config)

    logger.info("Authentication middleware framework configured")


def setup_all_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup all middleware components in the correct order.

    Middleware is applied in reverse order of addition, so we add them
    in the reverse of desired execution order.

    Args:
        app: FastAPI application instance
        config: Runtime configuration
    """
    logger = logging.getLogger(f"{__name__}.setup_all_middleware")

    logger.info("Setting up comprehensive middleware stack...")

    # 1. CORS (outermost layer)
    setup_cors_middleware(app, config)

    # 2. Error handling (catch all errors before they bubble up)
    setup_error_handling_middleware(app, config)

    # 3. Authentication (before business logic but after error handling)
    setup_authentication_middleware(app, config)

    # 4. Request logging (innermost layer, logs actual business logic)
    setup_logging_middleware(app, config)

    logger.info("Middleware stack setup completed")

    # Log middleware order for debugging
    middleware_order = [
        "Request Logging (innermost)",
        "Authentication",
        "Error Handling",
        "CORS (outermost)",
    ]

    logger.debug(f"Middleware execution order: {' -> '.join(middleware_order)}")


# Export public interface
__all__ = [
    "RequestLoggingMiddleware",
    "ErrorHandlingMiddleware",
    "AuthenticationMiddleware",
    "setup_cors_middleware",
    "setup_logging_middleware",
    "setup_error_handling_middleware",
    "setup_authentication_middleware",
    "setup_all_middleware",
]
