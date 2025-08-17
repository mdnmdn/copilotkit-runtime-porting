"""
Integration tests for Phase 1 functionality.

This module provides comprehensive integration tests for all Phase 1 components
working together, including:
- CopilotRuntime with FastAPI integration
- GraphQL schema and resolvers with real runtime
- Middleware stack integration
- Standalone server functionality
- End-to-end GraphQL operations
- Health check and monitoring endpoints
"""

import asyncio
import json
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

from copilotkit.runtime_py.core.runtime import CopilotRuntime
from copilotkit.runtime_py.core.types import RuntimeConfig, AgentDescriptor
from copilotkit.runtime_py.core.provider import AgentProvider
from copilotkit.runtime_py.app.main import create_app
from copilotkit.runtime_py.graphql.schema import get_schema_sdl


class MockAgentProvider(AgentProvider):
    """Mock agent provider for testing."""

    def __init__(self, name: str = "test-provider"):
        self._name = name
        self._agents = [
            AgentDescriptor(
                name="test-agent-1",
                description="Test agent for integration testing",
                version="1.0.0",
                capabilities=["chat", "search", "analysis"]
            ),
            AgentDescriptor(
                name="test-agent-2",
                description="Second test agent",
                version="1.1.0",
                capabilities=["summarization", "translation"]
            )
        ]

    @property
    def name(self) -> str:
        return self._name

    async def list_agents(self) -> list[AgentDescriptor]:
        """Return mock agents."""
        return self._agents.copy()

    async def initialize(self) -> None:
        """Initialize the provider."""
        pass

    async def cleanup(self) -> None:
        """Cleanup the provider."""
        pass


class TestCopilotRuntimeIntegration:
    """Test CopilotRuntime integration with FastAPI."""

    def test_runtime_creation_and_provider_registration(self):
        """Test runtime creation with provider registration."""
        config = RuntimeConfig(
            cors_origins=["http://localhost:3000"],
            debug=True,
            graphql_playground_enabled=True
        )

        # Create runtime with config
        runtime = CopilotRuntime(config=config)

        # Add mock provider
        provider = MockAgentProvider("integration-test")
        runtime.add_provider(provider)

        # Verify provider registration
        assert "integration-test" in runtime.list_providers()
        assert len(runtime.list_providers()) == 1

        provider_retrieved = runtime.get_provider("integration-test")
        assert provider_retrieved == provider

    @pytest.mark.asyncio
    async def test_runtime_agent_discovery(self):
        """Test agent discovery through runtime."""
        runtime = CopilotRuntime()
        provider = MockAgentProvider("test-discovery")
        runtime.add_provider(provider)

        # Test agent discovery
        agents = await runtime.discover_agents()

        assert len(agents) == 2
        assert agents[0].name == "test-agent-1"
        assert agents[0].capabilities == ["chat", "search", "analysis"]
        assert agents[1].name == "test-agent-2"
        assert agents[1].version == "1.1.0"

    @pytest.mark.asyncio
    async def test_runtime_lifecycle_management(self):
        """Test runtime start and stop lifecycle."""
        runtime = CopilotRuntime()
        provider = MockAgentProvider("lifecycle-test")
        runtime.add_provider(provider)

        # Test async context manager
        async with runtime:
            # Runtime should be started
            agents = await runtime.discover_agents()
            assert len(agents) == 2

        # Runtime should be stopped after context exit
        # (In our implementation, this doesn't change functionality yet,
        # but tests the pattern)

    def test_runtime_fastapi_mounting(self):
        """Test runtime mounting to FastAPI application."""
        from fastapi import FastAPI

        app = FastAPI()
        runtime = CopilotRuntime()
        provider = MockAgentProvider("mount-test")
        runtime.add_provider(provider)

        # Mount runtime to FastAPI app
        runtime.mount_to_fastapi(app, path="/api/copilotkit")

        # Verify mounting worked
        assert runtime._mounted_app == app
        assert runtime._mount_path == "/api/copilotkit"

        # Test client to verify endpoints are available
        client = TestClient(app)

        # Test health check endpoint
        response = client.get("/api/copilotkit/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "mount-test" in data["providers"]

    def test_runtime_standalone_app_creation(self):
        """Test creating standalone FastAPI app."""
        runtime = CopilotRuntime()
        provider = MockAgentProvider("standalone-test")
        runtime.add_provider(provider)

        # Create standalone app
        app = runtime.create_fastapi_app()

        # Test with client
        client = TestClient(app)

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CopilotKit Python Runtime"

        # Test runtime info endpoint
        response = client.get("/api/copilotkit/info")
        assert response.status_code == 200
        data = response.json()
        assert data["runtime"] == "copilotkit-python"
        assert "standalone-test" in data["providers"]


class TestGraphQLIntegration:
    """Test GraphQL integration with runtime."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = RuntimeConfig(
            debug=True,
            graphql_playground_enabled=True,
            cors_origins=["*"]
        )
        self.runtime = CopilotRuntime(config=self.config)
        self.provider = MockAgentProvider("graphql-test")
        self.runtime.add_provider(self.provider)

        # Mount to FastAPI app
        from fastapi import FastAPI
        self.app = FastAPI()
        self.runtime.mount_to_fastapi(self.app, path="/api/copilotkit")
        self.client = TestClient(self.app)

    def test_graphql_endpoint_availability(self):
        """Test that GraphQL endpoint is available."""
        # Test GraphQL endpoint responds
        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": "{ hello }"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["hello"] == "Hello from CopilotKit Python Runtime!"

    def test_graphql_playground_endpoint(self):
        """Test GraphQL Playground endpoint."""
        response = self.client.get("/api/copilotkit/graphql/playground")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "GraphQL Playground" in response.text

    def test_graphql_schema_introspection(self):
        """Test GraphQL schema introspection."""
        response = self.client.get("/api/copilotkit/graphql/schema")
        assert response.status_code == 200

        data = response.json()
        assert "schema" in data
        assert "Query" in data["schema"]
        assert "Mutation" in data["schema"]

    def test_available_agents_query(self):
        """Test availableAgents GraphQL query."""
        query = """
        query GetAgents {
            availableAgents {
                agents {
                    name
                    description
                    version
                    capabilities
                }
            }
        }
        """

        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        agents = data["data"]["availableAgents"]["agents"]
        assert len(agents) == 2

        # Verify first agent
        agent1 = agents[0]
        assert agent1["name"] == "test-agent-1"
        assert agent1["description"] == "Test agent for integration testing"
        assert agent1["version"] == "1.0.0"
        assert agent1["capabilities"] == ["chat", "search", "analysis"]

    def test_runtime_info_query(self):
        """Test runtimeInfo GraphQL query."""
        query = """
        query GetRuntimeInfo {
            runtimeInfo {
                version
                providers
                agentsCount
            }
        }
        """

        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        runtime_info = data["data"]["runtimeInfo"]
        assert runtime_info["version"] == "0.1.0"
        assert "graphql-test" in runtime_info["providers"]
        assert runtime_info["agentsCount"] == 2

    def test_generate_copilot_response_mutation(self):
        """Test generateCopilotResponse GraphQL mutation."""
        mutation = """
        mutation GenerateResponse($data: GenerateCopilotResponseInput!) {
            generateCopilotResponse(data: $data) {
                threadId
                status
                messages {
                    ... on Message {
                        id
                        role
                        content
                        status
                    }
                }
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "messages": [
                    {
                        "role": "USER",
                        "content": "Hello, test message!"
                    }
                ],
                "agentSession": {
                    "threadId": "test-thread-123",
                    "agentName": "test-agent-1"
                },
                "requestType": "CHAT"
            }
        }

        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": mutation, "variables": variables}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        result = data["data"]["generateCopilotResponse"]
        assert result["threadId"] == "test-thread-123"
        assert result["status"] == "SUCCESS"
        assert len(result["messages"]) == 1  # Should have acknowledgment message
        assert result["errorMessage"] is None

    def test_graphql_error_handling(self):
        """Test GraphQL error handling."""
        # Test with invalid query
        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": "{ invalidField }"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "errors" in data

    def test_graphql_context_injection(self):
        """Test that GraphQL context is properly injected."""
        # This is tested indirectly through the queries above,
        # which rely on runtime context being available
        query = "{ availableAgents { agents { name } } }"

        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": query}
        )

        # If context injection works, the query should succeed
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]["availableAgents"]["agents"]) > 0


class TestMiddlewareIntegration:
    """Test middleware stack integration."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = RuntimeConfig(
            cors_origins=["http://localhost:3000", "https://example.com"],
            debug=True,
            request_logging_enabled=True,
            error_reporting_enabled=True
        )
        self.runtime = CopilotRuntime(config=self.config)
        self.provider = MockAgentProvider("middleware-test")
        self.runtime.add_provider(self.provider)

        from fastapi import FastAPI
        self.app = FastAPI()
        self.runtime.mount_to_fastapi(self.app, path="/api/copilotkit")
        self.client = TestClient(self.app)

    def test_cors_middleware_functionality(self):
        """Test CORS middleware with allowed origins."""
        # Test with allowed origin
        response = self.client.get(
            "/api/copilotkit/health",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_request_logging_middleware(self):
        """Test request logging middleware adds headers."""
        response = self.client.get("/api/copilotkit/health")

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers

    def test_error_handling_middleware(self):
        """Test error handling middleware."""
        # Add an endpoint that raises an error
        @self.app.get("/test-error")
        async def error_endpoint():
            raise Exception("Test error for middleware")

        response = self.client.get("/test-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert "request_id" in data

        # In debug mode, should show actual error
        assert data["message"] == "Test error for middleware"

    def test_authentication_middleware_context(self):
        """Test authentication middleware sets up auth context."""
        # Test with auth headers
        response = self.client.get(
            "/api/copilotkit/health",
            headers={
                "Authorization": "Bearer test-token",
                "X-API-Key": "test-api-key"
            }
        )

        assert response.status_code == 200
        # Auth middleware should pass through in debug mode

    def test_middleware_order_and_execution(self):
        """Test that middleware executes in correct order."""
        # Make a request that will go through all middleware layers
        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": "{ hello }"},
            headers={
                "Origin": "http://localhost:3000",
                "Authorization": "Bearer test-token",
                "User-Agent": "integration-test"
            }
        )

        assert response.status_code == 200

        # Verify middleware processed request
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers
        assert "access-control-allow-origin" in response.headers

        # Verify GraphQL response
        data = response.json()
        assert data["data"]["hello"] == "Hello from CopilotKit Python Runtime!"


class TestStandaloneServerIntegration:
    """Test standalone server functionality."""

    def test_standalone_server_creation(self):
        """Test creating standalone server from main module."""
        app = create_app()

        # App should be properly configured
        assert app.title == "CopilotKit Python Runtime"
        assert app.version == "0.1.0"

        # Test with client
        client = TestClient(app)

        # Root endpoint should work
        response = client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_server_lifespan_management(self):
        """Test server lifespan management."""
        # This test verifies that the lifespan context manager works
        # In a real scenario, this would test actual server startup/shutdown

        # For now, we test that we can create the app without errors
        app = create_app()

        # The lifespan handler should be set
        assert app.router.lifespan_context is not None


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def setup_method(self):
        """Setup complete system for testing."""
        # Create runtime with multiple providers
        self.config = RuntimeConfig(
            cors_origins=["*"],
            debug=True,
            graphql_playground_enabled=True,
            middleware_stack_enabled=True
        )

        self.runtime = CopilotRuntime(config=self.config)

        # Add multiple providers
        self.provider1 = MockAgentProvider("provider-1")
        self.provider2 = MockAgentProvider("provider-2")
        self.runtime.add_provider(self.provider1)
        self.runtime.add_provider(self.provider2)

        # Create app with full setup
        from fastapi import FastAPI
        self.app = FastAPI()
        self.runtime.mount_to_fastapi(self.app, path="/api/copilotkit")
        self.client = TestClient(self.app)

    def test_complete_graphql_workflow(self):
        """Test complete GraphQL workflow with multiple operations."""
        # 1. Check health
        health_response = self.client.get("/api/copilotkit/health")
        assert health_response.status_code == 200

        # 2. Get runtime info
        runtime_query = "{ runtimeInfo { version providers agentsCount } }"
        runtime_response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": runtime_query}
        )
        assert runtime_response.status_code == 200
        runtime_data = runtime_response.json()["data"]["runtimeInfo"]
        assert len(runtime_data["providers"]) == 2
        assert runtime_data["agentsCount"] == 4  # 2 agents per provider

        # 3. Get available agents
        agents_query = "{ availableAgents { agents { name description } } }"
        agents_response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": agents_query}
        )
        assert agents_response.status_code == 200
        agents_data = agents_response.json()["data"]["availableAgents"]["agents"]
        assert len(agents_data) == 4

        # 4. Generate response
        mutation = """
        mutation {
            generateCopilotResponse(data: {
                messages: [{ role: USER, content: "Hello!" }]
                agentSession: { threadId: "e2e-test-123" }
            }) {
                threadId
                status
                messages {
                    ... on Message {
                        content
                        role
                    }
                }
            }
        }
        """

        mutation_response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": mutation}
        )
        assert mutation_response.status_code == 200
        mutation_data = mutation_response.json()["data"]["generateCopilotResponse"]
        assert mutation_data["threadId"] == "e2e-test-123"
        assert mutation_data["status"] == "SUCCESS"

    def test_concurrent_graphql_requests(self):
        """Test handling multiple concurrent GraphQL requests."""
        import threading
        import time

        results = []

        def make_request():
            response = self.client.post(
                "/api/copilotkit/graphql",
                json={"query": "{ hello }"}
            )
            results.append(response.status_code)

        # Create multiple threads to make concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()

        # Verify all requests succeeded
        assert len(results) == 10
        assert all(status == 200 for status in results)

        # Should complete reasonably quickly (less than 5 seconds)
        assert end_time - start_time < 5.0

    def test_error_resilience(self):
        """Test system resilience to errors."""
        # Test with provider that raises errors
        class FailingProvider(AgentProvider):
            @property
            def name(self) -> str:
                return "failing-provider"

            async def list_agents(self) -> list[AgentDescriptor]:
                raise Exception("Provider error")

        # Add failing provider
        failing_provider = FailingProvider()
        self.runtime.add_provider(failing_provider)

        # System should still work with other providers
        agents_query = "{ availableAgents { agents { name } } }"
        response = self.client.post(
            "/api/copilotkit/graphql",
            json={"query": agents_query}
        )

        assert response.status_code == 200
        # Should still return agents from working providers
        data = response.json()["data"]["availableAgents"]["agents"]
        assert len(data) >= 4  # At least the agents from working providers

    def test_configuration_impact(self):
        """Test that configuration changes affect behavior."""
        # Test with playground disabled
        config_no_playground = RuntimeConfig(
            graphql_playground_enabled=False,
            debug=False
        )

        runtime_no_playground = CopilotRuntime(config=config_no_playground)
        provider = MockAgentProvider("config-test")
        runtime_no_playground.add_provider(provider)

        from fastapi import FastAPI
        app_no_playground = FastAPI()
        runtime_no_playground.mount_to_fastapi(app_no_playground, path="/api/test")

        client_no_playground = TestClient(app_no_playground)

        # Playground endpoint should not exist or return different content
        playground_response = client_no_playground.get("/api/test/graphql/playground")
        # This might be 404 or different content depending on implementation
        assert playground_response.status_code != 200 or "playground" not in playground_response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
