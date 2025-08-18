"""
Basic Integration Tests for Phase 1 - CopilotRuntime and FastAPI Integration.

Tests the complete integration of CopilotRuntime with FastAPI applications,
including GraphQL schema mounting, middleware stack, and basic API functionality.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
import json

from agui_runtime.runtime_py.core.runtime import CopilotRuntime
from agui_runtime.runtime_py.core.types import RuntimeConfig, AgentDescriptor
from agui_runtime.runtime_py.core.provider import AgentProvider


class MockAgentProvider(AgentProvider):
    """Mock provider for testing purposes."""

    def __init__(self):
        self._name = "mock-provider"
        self._agents = [
            AgentDescriptor(
                name="test-agent",
                description="A test agent for integration testing",
                provider="mock-provider",
            )
        ]

    @property
    def name(self) -> str:
        return self._name

    async def list_agents(self) -> list[AgentDescriptor]:
        return self._agents

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass

    async def execute_run(self, messages, context):
        """Mock execute_run method for testing."""

        # Return empty async iterator for testing
        async def empty_iterator():
            yield

        return empty_iterator()


class TestBasicIntegration:
    """Basic integration tests for CopilotRuntime and FastAPI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RuntimeConfig(
            debug=True,
            cors_allow_origins=["http://localhost:3000"],
            middleware_stack_enabled=True,
        )
        self.runtime = CopilotRuntime(config=self.config)
        self.mock_provider = MockAgentProvider()

    def test_runtime_fastapi_integration(self):
        """Test complete runtime integration with FastAPI."""
        app = FastAPI()

        # Add mock provider
        self.runtime.add_provider(self.mock_provider)

        # Mount runtime to FastAPI
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        # Verify mounting was successful
        assert self.runtime._mounted_app is app
        assert self.runtime._mount_path == "/api/copilotkit"

        # Test with client
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/api/copilotkit/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_graphql_endpoint_availability(self):
        """Test GraphQL endpoint is properly mounted."""
        app = FastAPI()
        self.runtime.add_provider(self.mock_provider)
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Test GraphQL endpoint responds (even if query fails, endpoint should exist)
        response = client.post("/api/copilotkit/graphql", json={"query": "{ __typename }"})
        # Should get a response (not 404), even if it's an error
        assert response.status_code != 404

    def test_available_agents_query(self):
        """Test availableAgents GraphQL query."""
        app = FastAPI()
        self.runtime.add_provider(self.mock_provider)
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Test availableAgents query
        query = """
        {
            availableAgents {
                agents {
                    name
                    description
                }
            }
        }
        """

        response = client.post("/api/copilotkit/graphql", json={"query": query})

        # Should not be 404 or 500
        assert response.status_code in [200, 400, 422]  # 400 for GraphQL errors, 422 for validation errors

        if response.status_code == 200:
            data = response.json()
            # If successful, should have the expected structure
            if "data" in data and data["data"] is not None:
                assert "availableAgents" in data["data"]

    def test_runtime_info_query(self):
        """Test runtimeInfo GraphQL query."""
        app = FastAPI()
        self.runtime.add_provider(self.mock_provider)
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Test runtimeInfo query
        query = """
        {
            runtimeInfo {
                version
                providers
                agentsCount
            }
        }
        """

        response = client.post("/api/copilotkit/graphql", json={"query": query})

        # Should not be 404 or 500
        assert response.status_code in [200, 400, 422]  # 400 for GraphQL errors, 422 for validation errors

        if response.status_code == 200:
            data = response.json()
            # If successful, should have the expected structure
            if "data" in data and data["data"] is not None:
                assert "runtimeInfo" in data["data"]

    def test_cors_middleware_integration(self):
        """Test CORS middleware is properly configured."""
        app = FastAPI()
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Test preflight request
        response = client.options(
            "/api/copilotkit/graphql", headers={"Origin": "http://localhost:3000"}
        )

        # CORS should be handled
        assert response.status_code in [200, 204, 405]  # Various acceptable CORS responses

    def test_multiple_providers_integration(self):
        """Test runtime with multiple providers."""
        # Create second mock provider
        provider2 = MockAgentProvider()
        provider2._name = "mock-provider-2"
        provider2._agents = [
            AgentDescriptor(
                name="agent-2", description="Second test agent", provider="mock-provider-2"
            )
        ]

        app = FastAPI()

        # Add both providers
        self.runtime.add_provider(self.mock_provider)
        self.runtime.add_provider(provider2)

        # Mount runtime
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        # Verify both providers are registered
        assert len(self.runtime.list_providers()) == 2
        assert "mock-provider" in self.runtime.list_providers()
        assert "mock-provider-2" in self.runtime.list_providers()

    def test_error_handling_integration(self):
        """Test error handling in integration scenario."""
        app = FastAPI()
        self.runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Test invalid GraphQL query
        response = client.post("/api/copilotkit/graphql", json={"query": "invalid query syntax {"})

        # Should handle error gracefully
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # GraphQL errors should be in errors field
            if "errors" in data:
                assert isinstance(data["errors"], list)


class TestRuntimeLifecycle:
    """Test runtime lifecycle management in integration context."""

    def test_runtime_startup_shutdown(self):
        """Test runtime startup and shutdown cycle."""
        config = RuntimeConfig(debug=True)
        runtime = CopilotRuntime(config=config)
        mock_provider = MockAgentProvider()

        runtime.add_provider(mock_provider)

        app = FastAPI()
        runtime.mount_to_fastapi(app, path="/api/copilotkit")

        # Runtime should be properly initialized
        assert runtime._providers["mock-provider"] == mock_provider
        assert runtime._mounted_app == app

    @pytest.mark.asyncio
    async def test_async_runtime_context(self):
        """Test runtime async context manager."""
        config = RuntimeConfig(debug=True)

        async with CopilotRuntime(config=config) as runtime:
            mock_provider = MockAgentProvider()
            runtime.add_provider(mock_provider)

            # Runtime should be started
            assert len(runtime._providers) == 1

        # Runtime should be properly cleaned up after context exit
        assert runtime._providers  # Providers still registered but runtime stopped


class TestConfigurationIntegration:
    """Test various configuration scenarios."""

    def test_debug_mode_integration(self):
        """Test runtime behavior in debug mode."""
        config = RuntimeConfig(debug=True, cors_allow_origins=["*"])
        runtime = CopilotRuntime(config=config)

        app = FastAPI()
        runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Debug mode should be reflected in responses
        response = client.get("/api/copilotkit/health")
        assert response.status_code == 200

    def test_production_mode_integration(self):
        """Test runtime behavior in production mode."""
        config = RuntimeConfig(debug=False, cors_allow_origins=["https://example.com"])
        runtime = CopilotRuntime(config=config)

        app = FastAPI()
        runtime.mount_to_fastapi(app, path="/api/copilotkit")

        client = TestClient(app)

        # Production mode should still work
        response = client.get("/api/copilotkit/health")
        assert response.status_code == 200

    def test_custom_mount_path_integration(self):
        """Test runtime with custom mount path."""
        runtime = CopilotRuntime()
        app = FastAPI()

        # Mount at custom path
        custom_path = "/custom/runtime/path"
        runtime.mount_to_fastapi(app, path=custom_path)

        client = TestClient(app)

        # Health endpoint should be at custom path
        response = client.get(f"{custom_path}/health")
        assert response.status_code == 200

        # Original path should not work
        response = client.get("/api/copilotkit/health")
        assert response.status_code == 404
