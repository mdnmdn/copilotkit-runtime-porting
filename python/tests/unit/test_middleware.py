"""
Unit tests for middleware functionality.

This module tests all middleware components including:
- Request logging middleware
- Error handling middleware
- Authentication middleware
- CORS middleware setup
- Middleware stack configuration
"""

import json
import logging
import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from agui_runtime.runtime_py.app.middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    AuthenticationMiddleware,
    setup_cors_middleware,
    setup_logging_middleware,
    setup_error_handling_middleware,
    setup_authentication_middleware,
    setup_all_middleware,
)
from agui_runtime.runtime_py.core.types import RuntimeConfig


class TestRequestLoggingMiddleware:
    """Test RequestLoggingMiddleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        app = FastAPI()
        config = RuntimeConfig()

        middleware = RequestLoggingMiddleware(app, config)

        assert middleware.config == config
        assert hasattr(middleware, "logger")

    @pytest.mark.asyncio
    async def test_request_processing_success(self):
        """Test successful request processing with logging."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = RequestLoggingMiddleware(app, config)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.query_params = {}
        request.headers = {"user-agent": "test-agent"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        # Mock call_next
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        with patch.object(middleware, "logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Verify response
            assert response == mock_response
            assert response.headers["X-Request-ID"] is not None
            assert "X-Response-Time" in response.headers

            # Verify logging was called
            assert mock_logger.info.call_count >= 2  # Start and complete logs

            # Check log calls
            log_calls = mock_logger.info.call_args_list
            start_call = log_calls[0]
            complete_call = log_calls[1]

            assert "Request started" in start_call[0][0]
            assert "Request completed" in complete_call[0][0]

    @pytest.mark.asyncio
    async def test_request_processing_with_error(self):
        """Test request processing when an error occurs."""
        app = FastAPI()
        config = RuntimeConfig(debug=True)
        middleware = RequestLoggingMiddleware(app, config)

        # Mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/test"
        request.query_params = {}
        request.headers = {"user-agent": "test-agent"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        # Mock call_next to raise exception
        test_error = Exception("Test error")
        call_next = AsyncMock(side_effect=test_error)

        with patch.object(middleware, "logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Verify error response was created
            assert response.status_code == 500
            assert "X-Request-ID" in response.headers

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Request error" in error_call[0][0]

    def test_get_client_ip_with_forwarded_header(self):
        """Test client IP extraction with X-Forwarded-For."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = RequestLoggingMiddleware(app, config)

        request = Mock()
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_with_real_ip_header(self):
        """Test client IP extraction with X-Real-IP."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = RequestLoggingMiddleware(app, config)

        request = Mock()
        request.headers = {"x-real-ip": "192.168.1.2"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.2"

    def test_get_client_ip_fallback(self):
        """Test client IP extraction fallback to client.host."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = RequestLoggingMiddleware(app, config)

        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_get_client_ip_unknown(self):
        """Test client IP extraction when no client info available."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = RequestLoggingMiddleware(app, config)

        request = Mock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        app = FastAPI()
        config = RuntimeConfig()

        middleware = ErrorHandlingMiddleware(app, config)

        assert middleware.config == config
        assert hasattr(middleware, "logger")

    @pytest.mark.asyncio
    async def test_successful_request_passthrough(self):
        """Test that successful requests pass through unchanged."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = ErrorHandlingMiddleware(app, config)

        request = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)

        assert response == mock_response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_http_exception_reraise(self):
        """Test that HTTPExceptions are re-raised for FastAPI to handle."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = ErrorHandlingMiddleware(app, config)

        request = Mock(spec=Request)
        http_exc = HTTPException(status_code=404, detail="Not found")
        call_next = AsyncMock(side_effect=http_exc)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value == http_exc

    @pytest.mark.asyncio
    async def test_validation_error_reraise(self):
        """Test that RequestValidationErrors are re-raised."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = ErrorHandlingMiddleware(app, config)

        request = Mock(spec=Request)
        validation_exc = RequestValidationError([])
        call_next = AsyncMock(side_effect=validation_exc)

        with pytest.raises(RequestValidationError):
            await middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_unhandled_exception_debug_mode(self):
        """Test unhandled exception handling in debug mode."""
        app = FastAPI()
        config = RuntimeConfig(debug=True)
        middleware = ErrorHandlingMiddleware(app, config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-123"
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"

        test_error = Exception("Test error")
        call_next = AsyncMock(side_effect=test_error)

        with patch.object(middleware, "logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Verify error response
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            # Verify error logging
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_unhandled_exception_production_mode(self):
        """Test unhandled exception handling in production mode."""
        app = FastAPI()
        config = RuntimeConfig(debug=False)
        middleware = ErrorHandlingMiddleware(app, config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-123"
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"

        test_error = Exception("Test error")
        call_next = AsyncMock(side_effect=test_error)

        with patch.object(middleware, "logger") as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Verify generic error message in production
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            # Response should not contain sensitive error details
            body = json.loads(response.body)
            assert body["message"] == "An unexpected error occurred"


class TestAuthenticationMiddleware:
    """Test AuthenticationMiddleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        app = FastAPI()
        config = RuntimeConfig()

        middleware = AuthenticationMiddleware(app, config)

        assert middleware.config == config
        assert hasattr(middleware, "logger")

    @pytest.mark.asyncio
    async def test_auth_header_extraction(self):
        """Test authentication header extraction."""
        app = FastAPI()
        config = RuntimeConfig()
        middleware = AuthenticationMiddleware(app, config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = {"authorization": "Bearer test-token", "x-api-key": "api-key-123"}

        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)

        # Verify auth context was set
        assert request.state.auth_header == "Bearer test-token"
        assert request.state.api_key == "api-key-123"
        assert request.state.user_id is None  # Not implemented yet
        assert request.state.authenticated is False

    @pytest.mark.asyncio
    async def test_debug_mode_authentication(self):
        """Test authentication in debug mode."""
        app = FastAPI()
        config = RuntimeConfig(debug=True)
        middleware = AuthenticationMiddleware(app, config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = {}

        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)

        # In debug mode, should allow all requests
        assert request.state.authenticated is True
        assert request.state.user_id == "dev_user"


class TestMiddlewareSetupFunctions:
    """Test middleware setup functions."""

    def test_setup_cors_middleware_with_origins(self):
        """Test CORS middleware setup with configured origins."""
        app = FastAPI()
        config = RuntimeConfig(cors_origins=["http://localhost:3000", "https://example.com"])

        with patch.object(app, "add_middleware") as mock_add_middleware:
            setup_cors_middleware(app, config)

            # Verify middleware was added
            mock_add_middleware.assert_called_once()
            call_args = mock_add_middleware.call_args

            # Check that CORSMiddleware was added with correct config
            from fastapi.middleware.cors import CORSMiddleware

            assert call_args[0][0] == CORSMiddleware

            kwargs = call_args[1]
            assert kwargs["allow_origins"] == ["http://localhost:3000", "https://example.com"]
            assert kwargs["allow_credentials"] is True
            assert "GET" in kwargs["allow_methods"]
            assert "POST" in kwargs["allow_methods"]

    def test_setup_cors_middleware_no_origins(self):
        """Test CORS middleware setup with no origins configured."""
        app = FastAPI()
        config = RuntimeConfig(cors_origins=[])

        with patch.object(app, "add_middleware") as mock_add_middleware:
            setup_cors_middleware(app, config)

            # Middleware should not be added
            mock_add_middleware.assert_not_called()

    def test_setup_logging_middleware(self):
        """Test logging middleware setup."""
        app = FastAPI()
        config = RuntimeConfig()

        with patch.object(app, "add_middleware") as mock_add_middleware:
            setup_logging_middleware(app, config)

            mock_add_middleware.assert_called_once()
            call_args = mock_add_middleware.call_args
            assert call_args[0][0] == RequestLoggingMiddleware

    def test_setup_error_handling_middleware(self):
        """Test error handling middleware setup."""
        app = FastAPI()
        config = RuntimeConfig()

        with (
            patch.object(app, "add_middleware") as mock_add_middleware,
            patch.object(app, "exception_handler") as mock_exception_handler,
        ):

            setup_error_handling_middleware(app, config)

            # Verify middleware was added
            mock_add_middleware.assert_called_once()
            call_args = mock_add_middleware.call_args
            assert call_args[0][0] == ErrorHandlingMiddleware

            # Verify exception handlers were added
            assert (
                mock_exception_handler.call_count >= 2
            )  # At least ValidationError and HTTPException

    def test_setup_authentication_middleware(self):
        """Test authentication middleware setup."""
        app = FastAPI()
        config = RuntimeConfig()

        with patch.object(app, "add_middleware") as mock_add_middleware:
            setup_authentication_middleware(app, config)

            mock_add_middleware.assert_called_once()
            call_args = mock_add_middleware.call_args
            assert call_args[0][0] == AuthenticationMiddleware

    def test_setup_all_middleware(self):
        """Test comprehensive middleware stack setup."""
        app = FastAPI()
        config = RuntimeConfig(cors_origins=["*"])

        with (
            patch("agui_runtime.runtime_py.app.middleware.setup_cors_middleware") as mock_cors,
            patch(
                "agui_runtime.runtime_py.app.middleware.setup_error_handling_middleware"
            ) as mock_error,
            patch(
                "agui_runtime.runtime_py.app.middleware.setup_authentication_middleware"
            ) as mock_auth,
            patch("agui_runtime.runtime_py.app.middleware.setup_logging_middleware") as mock_logging,
        ):

            setup_all_middleware(app, config)

            # Verify all middleware setup functions were called
            mock_cors.assert_called_once_with(app, config)
            mock_error.assert_called_once_with(app, config)
            mock_auth.assert_called_once_with(app, config)
            mock_logging.assert_called_once_with(app, config)


class TestMiddlewareIntegration:
    """Test middleware integration with FastAPI."""

    def test_middleware_order_in_fastapi_app(self):
        """Test that middleware is added in correct order."""
        app = FastAPI()
        config = RuntimeConfig(cors_origins=["*"])

        # This should not raise any exceptions
        setup_all_middleware(app, config)

        # Verify that middleware stack exists
        # Note: Detailed middleware order testing would require more complex integration tests
        assert len(app.user_middleware) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_middleware_flow(self):
        """Test end-to-end middleware processing flow."""
        app = FastAPI()
        config = RuntimeConfig(cors_origins=["http://localhost:3000"], debug=True)

        # Add a simple test endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Setup middleware
        setup_all_middleware(app, config)

        # Test with TestClient
        client = TestClient(app)
        response = client.get("/test", headers={"Origin": "http://localhost:3000"})

        # Verify successful response
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

        # Verify CORS headers are present
        assert "access-control-allow-origin" in response.headers

        # Verify custom headers from middleware
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers

    @pytest.mark.asyncio
    async def test_error_handling_in_middleware_stack(self):
        """Test error handling through the middleware stack."""
        app = FastAPI()
        config = RuntimeConfig(debug=False)

        # Add an endpoint that raises an error
        @app.get("/error")
        async def error_endpoint():
            raise Exception("Test error")

        # Setup middleware
        setup_all_middleware(app, config)

        client = TestClient(app)
        response = client.get("/error")

        # Verify error response
        assert response.status_code == 500

        data = response.json()
        assert data["error"] == "Internal server error"
        assert data["message"] == "An unexpected error occurred"  # Production mode message
        assert "request_id" in data


if __name__ == "__main__":
    pytest.main([__file__])
