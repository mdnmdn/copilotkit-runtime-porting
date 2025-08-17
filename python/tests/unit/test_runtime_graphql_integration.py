"""
Unit tests for GraphQL integration with CopilotRuntime.

This module tests the GraphQL integration components including:
- GraphQL context creation and injection
- GraphQL router setup and configuration
- Schema resolvers functionality
- Error handling in GraphQL operations
"""

import datetime
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from copilotkit.runtime_py.app.runtime_mount import (
    GraphQLContext,
    get_graphql_context,
    create_graphql_router,
    mount_graphql_to_fastapi,
    setup_graphql_middleware,
)
from copilotkit.runtime_py.core.runtime import CopilotRuntime
from copilotkit.runtime_py.core.types import RuntimeConfig, AgentDescriptor
from copilotkit.runtime_py.graphql.schema import schema, Query, Mutation


class TestGraphQLContext:
    """Test GraphQLContext functionality."""

    def test_context_creation(self):
        """Test GraphQL context creation."""
        # Create mock objects
        runtime = Mock(spec=CopilotRuntime)
        request = Mock(spec=Request)
        response = Mock(spec=Response)

        # Mock request attributes
        request.state = Mock()
        request.state.request_id = "test-request-123"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"User-Agent": "test-agent"}

        # Create context
        context = GraphQLContext(runtime, request, response)

        # Verify initialization
        assert context.runtime == runtime
        assert context.request == request
        assert context.response == response
        assert context.request_id == "test-request-123"
        assert context.user_id is None
        assert context.trace_id is None

    def test_get_client_ip_with_forwarded_header(self):
        """Test client IP extraction with X-Forwarded-For header."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        context = GraphQLContext(runtime, request, response)

        assert context.get_client_ip() == "192.168.1.1"

    def test_get_client_ip_fallback(self):
        """Test client IP extraction fallback to client.host."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        context = GraphQLContext(runtime, request, response)

        assert context.get_client_ip() == "127.0.0.1"

    def test_get_client_ip_unknown(self):
        """Test client IP extraction when no client info available."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.headers = {}
        request.client = None

        context = GraphQLContext(runtime, request, response)

        assert context.get_client_ip() == "unknown"

    def test_get_user_agent(self):
        """Test User-Agent header extraction."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.headers = {"User-Agent": "Mozilla/5.0 Test Browser"}
        request.client = Mock()

        context = GraphQLContext(runtime, request, response)

        assert context.get_user_agent() == "Mozilla/5.0 Test Browser"

    def test_get_user_agent_unknown(self):
        """Test User-Agent header extraction when header is missing."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.headers = {}
        request.client = Mock()

        context = GraphQLContext(runtime, request, response)

        assert context.get_user_agent() == "unknown"

    @patch("logging.getLogger")
    def test_log_operation(self, mock_get_logger):
        """Test operation logging functionality."""
        runtime = Mock()
        request = Mock(spec=Request)
        response = Mock()

        request.state = Mock()
        request.state.request_id = "test-123"
        request.headers = {"User-Agent": "test-agent"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        context = GraphQLContext(runtime, request, response)
        context.user_id = "user-123"

        # Mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        context.log_operation("test_query", "query")

        # Verify logging was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "GraphQL query: test_query" in call_args[0][0]


class TestGraphQLContextGetter:
    """Test GraphQL context getter function."""

    @pytest.mark.asyncio
    async def test_get_graphql_context(self):
        """Test GraphQL context creation function."""
        runtime = Mock(spec=CopilotRuntime)
        request = Mock(spec=Request)
        response = Mock(spec=Response)

        request.state = Mock()
        request.client = Mock()
        request.headers = {}

        context = await get_graphql_context(runtime, request, response)

        assert isinstance(context, GraphQLContext)
        assert context.runtime == runtime
        assert context.request == request
        assert context.response == response


class TestGraphQLRouterCreation:
    """Test GraphQL router creation and configuration."""

    def test_create_graphql_router(self):
        """Test GraphQL router creation."""
        runtime = Mock(spec=CopilotRuntime)

        with patch("copilotkit.runtime_py.app.runtime_mount.GraphQLRouter") as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router

            router = create_graphql_router(runtime, "/test-graphql", True)

            # Verify router was created with correct parameters
            mock_router_class.assert_called_once()
            call_args = mock_router_class.call_args
            assert call_args[0][0] == schema  # First arg should be schema

            # Verify keyword arguments
            kwargs = call_args[1]
            assert kwargs["path"] == "/test-graphql"
            assert kwargs["graphql_ide"] == "playground"
            assert "context_getter" in kwargs

            assert router == mock_router

    def test_create_graphql_router_no_playground(self):
        """Test GraphQL router creation without playground."""
        runtime = Mock(spec=CopilotRuntime)

        with patch("copilotkit.runtime_py.app.runtime_mount.GraphQLRouter") as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router

            router = create_graphql_router(runtime, "/graphql", False)

            kwargs = mock_router_class.call_args[1]
            assert kwargs["graphql_ide"] is None


class TestGraphQLMounting:
    """Test GraphQL mounting to FastAPI applications."""

    def test_mount_graphql_to_fastapi(self):
        """Test mounting GraphQL to FastAPI application."""
        app = FastAPI()
        runtime = Mock(spec=CopilotRuntime)

        # Mock agent discovery for health check
        runtime.discover_agents = AsyncMock(return_value=[])
        runtime.list_providers.return_value = ["test-provider"]

        with patch(
            "copilotkit.runtime_py.app.runtime_mount.create_graphql_router"
        ) as mock_create_router:
            # Create a mock router with all required FastAPI router attributes
            mock_router = Mock()
            mock_router.routes = []  # Empty routes list for FastAPI compatibility
            mock_router.on_startup = []  # Required by FastAPI router
            mock_router.on_shutdown = []  # Required by FastAPI router
            mock_router.lifespan = None  # Required by FastAPI router
            mock_create_router.return_value = mock_router

            mount_graphql_to_fastapi(app, runtime, "/test-graphql", True, True)

            # Verify router creation was called
            mock_create_router.assert_called_once_with(
                runtime=runtime, path="/test-graphql", include_playground=True
            )

    @pytest.mark.asyncio
    async def test_graphql_health_endpoint(self):
        """Test GraphQL health check endpoint."""
        app = FastAPI()
        runtime = Mock(spec=CopilotRuntime)

        # Mock runtime methods
        runtime.discover_agents = AsyncMock(
            return_value=[AgentDescriptor(name="test-agent", description="Test agent")]
        )
        runtime.list_providers.return_value = ["test-provider"]

        with (
            patch(
                "copilotkit.runtime_py.app.runtime_mount.create_graphql_router"
            ) as mock_create_router,
            patch("copilotkit.runtime_py.graphql.schema.get_schema_sdl") as mock_get_sdl,
        ):

            # Create a mock router with all required FastAPI router attributes
            mock_router = Mock()
            mock_router.routes = []
            mock_router.on_startup = []
            mock_router.on_shutdown = []
            mock_router.lifespan = None
            mock_create_router.return_value = mock_router

            mock_get_sdl.return_value = "schema { query: Query }"

            mount_graphql_to_fastapi(app, runtime, "/graphql", True, True)

            # Test the health endpoint
            client = TestClient(app)
            response = client.get("/graphql/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "graphql"
            assert data["schema_valid"] is True
            assert data["agents_available"] == 1
            assert data["endpoint"] == "/graphql"
            assert data["playground_enabled"] is True

    @pytest.mark.asyncio
    async def test_graphql_health_endpoint_error(self):
        """Test GraphQL health check endpoint with error."""
        app = FastAPI()
        runtime = Mock(spec=CopilotRuntime)

        # Mock runtime to raise exception
        runtime.discover_agents = AsyncMock(side_effect=Exception("Test error"))
        runtime.list_providers.return_value = ["test-provider"]

        with patch(
            "copilotkit.runtime_py.app.runtime_mount.create_graphql_router"
        ) as mock_create_router:
            # Create a mock router with all required FastAPI router attributes
            mock_router = Mock()
            mock_router.routes = []
            mock_router.on_startup = []
            mock_router.on_shutdown = []
            mock_router.lifespan = None
            mock_create_router.return_value = mock_router

            mount_graphql_to_fastapi(app, runtime, "/graphql", True, True)

            client = TestClient(app)
            response = client.get("/graphql/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["service"] == "graphql"
            assert "error" in data
            assert data["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_graphql_schema_endpoint(self):
        """Test GraphQL schema introspection endpoint."""
        app = FastAPI()
        runtime = Mock(spec=CopilotRuntime)

        runtime.discover_agents = AsyncMock(return_value=[])
        runtime.list_providers.return_value = []

        with (
            patch(
                "copilotkit.runtime_py.app.runtime_mount.create_graphql_router"
            ) as mock_create_router,
            patch("copilotkit.runtime_py.graphql.schema.get_schema_sdl") as mock_get_sdl,
        ):

            # Create a mock router with all required FastAPI router attributes
            mock_router = Mock()
            mock_router.routes = []
            mock_router.on_startup = []
            mock_router.on_shutdown = []
            mock_router.lifespan = None
            mock_create_router.return_value = mock_router

            mock_get_sdl.return_value = "schema { query: Query }"

            mount_graphql_to_fastapi(app, runtime, "/graphql", True, True)

            client = TestClient(app)
            response = client.get("/graphql/schema")

            assert response.status_code == 200
            data = response.json()
            assert data["schema"] == "schema { query: Query }"
            assert data["format"] == "SDL"


class TestGraphQLMiddleware:
    """Test GraphQL-specific middleware setup."""

    def test_setup_graphql_middleware(self):
        """Test GraphQL middleware setup."""
        app = FastAPI()
        runtime = Mock(spec=CopilotRuntime)

        # This should not raise any exceptions
        setup_graphql_middleware(app, runtime)

        # Verify middleware was added (app.middleware should have entries)
        # Note: In a real test, we'd need to check that the middleware functions correctly
        # but that would require more complex integration testing


class TestGraphQLResolvers:
    """Test GraphQL resolver functionality."""

    @pytest.mark.asyncio
    async def test_available_agents_resolver_success(self):
        """Test successful available_agents resolver."""
        # Create mock info object with context
        mock_runtime = Mock(spec=CopilotRuntime)
        mock_runtime.discover_agents = AsyncMock(
            return_value=[
                AgentDescriptor(
                    name="test-agent",
                    description="Test agent",
                    version="1.0.0",
                    capabilities=["chat", "search"],
                )
            ]
        )

        mock_context = Mock()
        mock_context.runtime = mock_runtime
        mock_context.log_operation = Mock()

        mock_info = Mock()
        mock_info.context = mock_context

        query = Query()
        result = await query.available_agents(mock_info)

        # Verify result
        assert len(result.agents) == 1
        assert result.agents[0].name == "test-agent"
        assert result.agents[0].description == "Test agent"
        assert result.agents[0].version == "1.0.0"
        assert result.agents[0].capabilities == ["chat", "search"]

        # Verify runtime was called
        mock_runtime.discover_agents.assert_called_once()
        mock_context.log_operation.assert_called_once_with("available_agents", "query")

    @pytest.mark.asyncio
    async def test_available_agents_resolver_error(self):
        """Test available_agents resolver with error."""
        # Create mock info object with failing runtime
        mock_runtime = Mock(spec=CopilotRuntime)
        mock_runtime.discover_agents = AsyncMock(side_effect=Exception("Test error"))

        mock_context = Mock()
        mock_context.runtime = mock_runtime
        mock_context.log_operation = Mock()

        mock_info = Mock()
        mock_info.context = mock_context

        query = Query()
        result = await query.available_agents(mock_info)

        # Should return empty result instead of raising
        assert len(result.agents) == 0

    @pytest.mark.asyncio
    async def test_runtime_info_resolver_success(self):
        """Test successful runtime_info resolver."""
        mock_runtime = Mock(spec=CopilotRuntime)
        mock_runtime.list_providers.return_value = ["langgraph", "crewai"]
        mock_runtime.discover_agents = AsyncMock(
            return_value=[
                AgentDescriptor(name="agent1", description="Agent 1"),
                AgentDescriptor(name="agent2", description="Agent 2"),
            ]
        )

        mock_context = Mock()
        mock_context.runtime = mock_runtime
        mock_context.log_operation = Mock()

        mock_info = Mock()
        mock_info.context = mock_context

        query = Query()
        result = await query.runtime_info(mock_info)

        # Verify result
        assert result.version == "0.1.0"
        assert result.providers == ["langgraph", "crewai"]
        assert result.agents_count == 2

        # Verify runtime was called
        mock_runtime.list_providers.assert_called_once()
        mock_runtime.discover_agents.assert_called_once()
        mock_context.log_operation.assert_called_once_with("runtime_info", "query")

    @pytest.mark.asyncio
    async def test_runtime_info_resolver_error(self):
        """Test runtime_info resolver with error."""
        mock_runtime = Mock(spec=CopilotRuntime)
        mock_runtime.list_providers.side_effect = Exception("Test error")

        mock_context = Mock()
        mock_context.runtime = mock_runtime
        mock_context.log_operation = Mock()

        mock_info = Mock()
        mock_info.context = mock_context

        query = Query()
        result = await query.runtime_info(mock_info)

        # Should return default values instead of raising
        assert result.version == "0.1.0"
        assert result.providers == []
        assert result.agents_count == 0


class TestGraphQLSchema:
    """Test GraphQL schema functionality."""

    def test_schema_creation(self):
        """Test that the GraphQL schema can be created."""
        from copilotkit.runtime_py.graphql.schema import schema

        # Schema should be created without errors
        assert schema is not None
        # Check for schema attributes that exist in Strawberry schema
        assert hasattr(schema, "_schema")

    def test_get_schema_sdl(self):
        """Test getting schema SDL."""
        from copilotkit.runtime_py.graphql.schema import get_schema_sdl

        sdl = get_schema_sdl()
        assert isinstance(sdl, str)
        assert len(sdl) > 0
        assert "Query" in sdl
        assert "Mutation" in sdl

    def test_validate_schema_compatibility(self):
        """Test schema compatibility validation."""
        from copilotkit.runtime_py.graphql.schema import validate_schema_compatibility

        # Should return True for now (stub implementation)
        result = validate_schema_compatibility()
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
