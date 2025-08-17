"""
Unit tests for CopilotRuntime core functionality.

This module contains comprehensive unit tests for the CopilotRuntime class,
covering provider management, agent discovery, FastAPI integration, and
configuration handling.
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from copilotkit.runtime_py.core.provider import AgentProvider
from copilotkit.runtime_py.core.runtime import CopilotRuntime
from copilotkit.runtime_py.core.types import (
    AgentDescriptor,
    AgentState,
    Message,
    RuntimeConfig,
    RuntimeContext,
    RuntimeEvent,
)


class MockProvider(AgentProvider):
    """Mock provider for testing."""

    def __init__(self, name: str = "mock_provider", agents: list[AgentDescriptor] = None):
        self._name = name
        self._agents = agents or []
        self.initialized = False
        self.cleaned_up = False

    @property
    def name(self) -> str:
        return self._name

    async def list_agents(self) -> list[AgentDescriptor]:
        return self._agents.copy()

    async def execute_run(
        self,
        agent_name: str,
        messages: list[Message],
        context: RuntimeContext,
    ) -> AsyncIterator[RuntimeEvent]:
        # Mock implementation
        yield RuntimeEvent(
            event_type="test_event",
            data=AgentState(
                thread_id=context.thread_id, agent_name=agent_name, data={"test": "data"}
            ),
            sequence=1,
        )

    async def initialize(self):
        self.initialized = True

    async def cleanup(self):
        self.cleaned_up = True


@pytest.fixture
def runtime_config():
    """Create a test runtime configuration."""
    return RuntimeConfig(
        host="127.0.0.1",
        port=8080,
        graphql_path="/test/graphql",
        enabled_providers=["test_provider"],
    )


@pytest.fixture
def mock_agent():
    """Create a mock agent descriptor."""
    return AgentDescriptor(
        name="test_agent",
        description="A test agent",
        version="1.0.0",
        capabilities=["test_capability"],
    )


@pytest.fixture
def mock_provider(mock_agent):
    """Create a mock provider with a test agent."""
    return MockProvider("test_provider", [mock_agent])


class TestCopilotRuntime:
    """Test suite for CopilotRuntime class."""

    def test_initialization_default_config(self):
        """Test runtime initialization with default configuration."""
        runtime = CopilotRuntime()

        assert runtime.config is not None
        assert isinstance(runtime.config, RuntimeConfig)
        assert runtime.config.host == "0.0.0.0"
        assert runtime.config.port == 8000
        assert len(runtime._providers) == 0
        assert runtime._cache_dirty is True

    def test_initialization_custom_config(self, runtime_config):
        """Test runtime initialization with custom configuration."""
        runtime = CopilotRuntime(config=runtime_config)

        assert runtime.config == runtime_config
        assert runtime.config.host == "127.0.0.1"
        assert runtime.config.port == 8080

    def test_initialization_with_providers(self, mock_provider):
        """Test runtime initialization with initial providers."""
        runtime = CopilotRuntime(providers=[mock_provider])

        assert len(runtime._providers) == 1
        assert "test_provider" in runtime._providers
        assert runtime._providers["test_provider"] == mock_provider

    def test_add_provider_success(self, mock_provider):
        """Test successful provider addition."""
        runtime = CopilotRuntime()

        runtime.add_provider(mock_provider)

        assert "test_provider" in runtime._providers
        assert runtime._providers["test_provider"] == mock_provider
        assert runtime._cache_dirty is True

    def test_add_provider_duplicate_name(self, mock_provider):
        """Test adding provider with duplicate name raises error."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        duplicate_provider = MockProvider("test_provider")

        with pytest.raises(ValueError, match="Provider 'test_provider' is already registered"):
            runtime.add_provider(duplicate_provider)

    def test_add_provider_invalid_type(self):
        """Test adding invalid provider type raises error."""
        runtime = CopilotRuntime()

        with pytest.raises(TypeError, match="Provider must implement AgentProvider interface"):
            runtime.add_provider("not_a_provider")

    def test_remove_provider_success(self, mock_provider):
        """Test successful provider removal."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        runtime.remove_provider("test_provider")

        assert "test_provider" not in runtime._providers
        assert runtime._cache_dirty is True

    def test_remove_provider_not_found(self):
        """Test removing non-existent provider raises error."""
        runtime = CopilotRuntime()

        with pytest.raises(KeyError, match="Provider 'nonexistent' is not registered"):
            runtime.remove_provider("nonexistent")

    def test_get_provider_success(self, mock_provider):
        """Test successful provider retrieval."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        retrieved_provider = runtime.get_provider("test_provider")

        assert retrieved_provider == mock_provider

    def test_get_provider_not_found(self):
        """Test retrieving non-existent provider raises error."""
        runtime = CopilotRuntime()

        with pytest.raises(KeyError, match="Provider 'nonexistent' is not registered"):
            runtime.get_provider("nonexistent")

    def test_list_providers(self, mock_provider):
        """Test listing registered providers."""
        runtime = CopilotRuntime()

        # Initially empty
        assert runtime.list_providers() == []

        # After adding provider
        runtime.add_provider(mock_provider)
        assert runtime.list_providers() == ["test_provider"]

        # Add another provider
        another_provider = MockProvider("another_provider")
        runtime.add_provider(another_provider)
        assert set(runtime.list_providers()) == {"test_provider", "another_provider"}

    @pytest.mark.asyncio
    async def test_discover_agents_success(self, mock_provider, mock_agent):
        """Test successful agent discovery."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        agents = await runtime.discover_agents()

        assert len(agents) == 1
        assert agents[0] == mock_agent
        assert runtime._cache_dirty is False

    @pytest.mark.asyncio
    async def test_discover_agents_cached(self, mock_provider, mock_agent):
        """Test agent discovery uses cache when not dirty."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        # First call - should hit provider
        agents1 = await runtime.discover_agents()

        # Modify provider's agents (but cache is not dirty)
        mock_provider._agents = []

        # Second call - should use cache
        agents2 = await runtime.discover_agents()

        assert agents1 == agents2
        assert len(agents2) == 1  # Still returns cached result

    @pytest.mark.asyncio
    async def test_discover_agents_refresh_cache(self, mock_provider, mock_agent):
        """Test agent discovery with cache refresh."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        # First call
        agents1 = await runtime.discover_agents()

        # Modify provider's agents
        new_agent = AgentDescriptor(name="new_agent", description="New agent")
        mock_provider._agents = [new_agent]

        # Call with refresh_cache=True
        agents2 = await runtime.discover_agents(refresh_cache=True)

        assert len(agents2) == 1
        assert agents2[0] == new_agent

    @pytest.mark.asyncio
    async def test_discover_agents_provider_error(self):
        """Test agent discovery handles provider errors gracefully."""
        runtime = CopilotRuntime()

        # Create a provider that raises an error
        error_provider = MockProvider("error_provider")
        error_provider.list_agents = AsyncMock(side_effect=Exception("Provider error"))

        runtime.add_provider(error_provider)

        with pytest.raises(RuntimeError, match="Failed to discover agents"):
            await runtime.discover_agents()

    @pytest.mark.asyncio
    async def test_discover_agents_multiple_providers(self, mock_agent):
        """Test agent discovery with multiple providers."""
        runtime = CopilotRuntime()

        # Add multiple providers with different agents
        provider1 = MockProvider("provider1", [mock_agent])
        agent2 = AgentDescriptor(name="agent2", description="Second agent")
        provider2 = MockProvider("provider2", [agent2])

        runtime.add_provider(provider1)
        runtime.add_provider(provider2)

        agents = await runtime.discover_agents()

        assert len(agents) == 2
        agent_names = [agent.name for agent in agents]
        assert "test_agent" in agent_names
        assert "agent2" in agent_names

    def test_mount_to_fastapi_success(self, mock_provider):
        """Test successful mounting to FastAPI app."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)
        app = FastAPI()

        runtime.mount_to_fastapi(app, path="/api/test")

        assert runtime._mounted_app == app
        assert runtime._mount_path == "/api/test"

    def test_mount_to_fastapi_already_mounted(self, mock_provider):
        """Test mounting to FastAPI when already mounted raises error."""
        runtime = CopilotRuntime()
        app1 = FastAPI()
        app2 = FastAPI()

        runtime.mount_to_fastapi(app1)

        with pytest.raises(RuntimeError, match="Runtime is already mounted to a FastAPI app"):
            runtime.mount_to_fastapi(app2)

    def test_create_fastapi_app(self, mock_provider):
        """Test creating standalone FastAPI app."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        app = runtime.create_fastapi_app()

        assert isinstance(app, FastAPI)
        assert app.title == "CopilotKit Python Runtime"
        assert runtime._mounted_app == app
        assert runtime._mount_path == "/api/copilotkit"

    @pytest.mark.asyncio
    async def test_start_runtime(self, mock_provider):
        """Test runtime startup."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        await runtime.start()

        assert mock_provider.initialized is True

    @pytest.mark.asyncio
    async def test_stop_runtime(self, mock_provider):
        """Test runtime shutdown."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        await runtime.start()
        await runtime.stop()

        assert mock_provider.cleaned_up is True

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_provider):
        """Test runtime as async context manager."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        async with runtime:
            assert mock_provider.initialized is True

        assert mock_provider.cleaned_up is True

    def test_repr(self, mock_provider):
        """Test string representation of runtime."""
        runtime = CopilotRuntime()
        runtime.add_provider(mock_provider)

        repr_str = repr(runtime)

        assert "CopilotRuntime" in repr_str
        assert "providers=1" in repr_str
        assert "mounted=no" in repr_str

        # Mount to app and test again
        app = FastAPI()
        runtime.mount_to_fastapi(app)

        repr_str = repr(runtime)
        assert "mounted=yes" in repr_str


class TestRuntimeIntegration:
    """Integration tests for runtime functionality."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, runtime_config, mock_agent):
        """Test a complete workflow from initialization to execution."""
        # Create runtime with config
        runtime = CopilotRuntime(config=runtime_config)

        # Create and add provider
        provider = MockProvider("workflow_provider", [mock_agent])
        runtime.add_provider(provider)

        # Start runtime
        await runtime.start()

        # Discover agents
        agents = await runtime.discover_agents()
        assert len(agents) == 1
        assert agents[0].name == "test_agent"

        # Create FastAPI app
        app = runtime.create_fastapi_app()
        assert isinstance(app, FastAPI)

        # Stop runtime
        await runtime.stop()

        assert provider.initialized is True
        assert provider.cleaned_up is True
