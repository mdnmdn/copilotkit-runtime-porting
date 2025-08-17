"""
CopilotRuntime - Main orchestrator class for CopilotKit Python Runtime.

This module contains the core CopilotRuntime class that serves as the main
entry point for integrating Python AI frameworks with CopilotKit's frontend
runtime system via GraphQL.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException

from copilotkit.runtime_py.core.provider import AgentProvider
from copilotkit.runtime_py.core.types import (
    AgentDescriptor,
    RuntimeConfig,
)


class CopilotRuntime:
    """
    Main orchestrator class for CopilotKit Python Runtime.

    This class serves as the central coordinator for:
    - AI framework provider management
    - GraphQL schema setup and serving
    - State persistence coordination
    - Streaming message delivery
    - Request lifecycle management

    Example Usage:
        ```python
        from copilotkit.runtime_py import CopilotRuntime
        from fastapi import FastAPI

        app = FastAPI()
        runtime = CopilotRuntime()

        # Mount to FastAPI application
        runtime.mount_to_fastapi(app, path="/api/copilotkit")

        # Or create standalone server
        standalone_app = runtime.create_fastapi_app()
        ```
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        providers: list[AgentProvider] | None = None,
    ) -> None:
        """
        Initialize the CopilotRuntime.

        Args:
            config: Runtime configuration settings. If None, default config is used.
            providers: List of agent providers to register. Can be empty initially.
        """
        self.config = config or RuntimeConfig()
        self.logger = logging.getLogger(f"{__name__}.CopilotRuntime")

        # Provider management
        self._providers: dict[str, AgentProvider] = {}
        self._agents_cache: dict[str, AgentDescriptor] = {}
        self._cache_dirty = True

        # FastAPI app reference (when mounted)
        self._mounted_app: FastAPI | None = None
        self._mount_path: str = ""

        # State management (will be initialized in later phases)
        self._state_store = None

        # Streaming management
        self._active_streams: dict[str, Any] = {}

        # Register initial providers if provided
        if providers:
            for provider in providers:
                self.add_provider(provider)

        self.logger.info(f"CopilotRuntime initialized with {len(self._providers)} providers")

    def add_provider(self, provider: AgentProvider) -> None:
        """
        Register an agent provider with the runtime.

        Args:
            provider: The agent provider to register.

        Raises:
            ValueError: If provider name is already registered.
        """
        if not isinstance(provider, AgentProvider):
            raise TypeError("Provider must implement AgentProvider interface")

        provider_name = provider.name

        if provider_name in self._providers:
            raise ValueError(f"Provider '{provider_name}' is already registered")

        self._providers[provider_name] = provider
        self._cache_dirty = True

        self.logger.info(f"Registered provider: {provider_name}")

    def remove_provider(self, provider_name: str) -> None:
        """
        Remove a registered provider.

        Args:
            provider_name: Name of the provider to remove.

        Raises:
            KeyError: If provider is not registered.
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' is not registered")

        del self._providers[provider_name]
        self._cache_dirty = True

        self.logger.info(f"Removed provider: {provider_name}")

    def get_provider(self, provider_name: str) -> AgentProvider:
        """
        Get a registered provider by name.

        Args:
            provider_name: Name of the provider to retrieve.

        Returns:
            The requested provider.

        Raises:
            KeyError: If provider is not registered.
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' is not registered")

        return self._providers[provider_name]

    def list_providers(self) -> list[str]:
        """
        Get list of registered provider names.

        Returns:
            List of provider names.
        """
        return list(self._providers.keys())

    async def discover_agents(self, refresh_cache: bool = False) -> list[AgentDescriptor]:
        """
        Discover all available agents from registered providers.

        Args:
            refresh_cache: Whether to refresh the agents cache.

        Returns:
            List of all available agent descriptors.
        """
        if not self._cache_dirty and not refresh_cache and self._agents_cache:
            return list(self._agents_cache.values())

        self.logger.debug("Discovering agents from providers")

        discovered_agents = []
        errors = []

        # Discover agents from all providers
        for provider_name, provider in self._providers.items():
            try:
                provider_agents = await provider.list_agents()
                for agent in provider_agents:
                    # Add provider context to agent
                    agent_key = f"{provider_name}:{agent.name}"
                    self._agents_cache[agent_key] = agent
                    discovered_agents.append(agent)

                self.logger.debug(
                    f"Provider '{provider_name}' contributed {len(provider_agents)} agents"
                )

            except Exception as e:
                error_msg = f"Error discovering agents from provider '{provider_name}': {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        self._cache_dirty = False

        if errors and not discovered_agents:
            # If all providers failed and no agents were discovered
            raise RuntimeError(f"Failed to discover agents: {'; '.join(errors)}")

        self.logger.info(f"Discovered {len(discovered_agents)} total agents")
        return discovered_agents

    def mount_to_fastapi(
        self,
        app: FastAPI,
        path: str = "/api/copilotkit",
        include_graphql_playground: bool = True,
    ) -> None:
        """
        Mount the CopilotRuntime to an existing FastAPI application.

        Args:
            app: The FastAPI application to mount to.
            path: The path prefix for mounting (default: "/api/copilotkit").
            include_graphql_playground: Whether to include GraphQL playground.
        """
        if self._mounted_app is not None:
            raise RuntimeError("Runtime is already mounted to a FastAPI app")

        self._mounted_app = app
        self._mount_path = path.rstrip("/")

        # Setup comprehensive middleware stack
        self._setup_middleware_stack(app)

        # Add health check endpoint
        @app.get(f"{self._mount_path}/health")
        async def health_check() -> dict[str, Any]:
            """Health check endpoint for the runtime."""
            return {
                "status": "healthy",
                "version": "0.1.0",
                "providers": self.list_providers(),
                "config": {
                    "graphql_path": f"{self._mount_path}/graphql",
                    "enabled_providers": self.config.enabled_providers,
                },
            }

        # Add basic info endpoint
        @app.get(f"{self._mount_path}/info")
        async def runtime_info() -> dict[str, Any]:
            """Get runtime information."""
            try:
                agents = await self.discover_agents()
                return {
                    "runtime": "copilotkit-python",
                    "version": "0.1.0",
                    "providers": self.list_providers(),
                    "agents_count": len(agents),
                    "agents": [
                        {
                            "name": agent.name,
                            "description": agent.description,
                            "version": agent.version,
                            "capabilities": agent.capabilities,
                        }
                        for agent in agents
                    ],
                }
            except Exception as e:
                self.logger.error(f"Error getting runtime info: {e}")
                raise HTTPException(status_code=500, detail="Internal server error") from e

        # Mount GraphQL endpoints
        self._mount_graphql_endpoints(
            app, f"{self._mount_path}/graphql", include_graphql_playground
        )

        self.logger.info(f"Runtime mounted to FastAPI app at path: {self._mount_path}")
        self.logger.info(f"GraphQL endpoint available at: {self._mount_path}/graphql")

    def _setup_middleware_stack(self, app: FastAPI) -> None:
        """
        Setup comprehensive middleware stack for the FastAPI application.

        Args:
            app: FastAPI application to setup middleware for.
        """
        # Import here to avoid circular imports
        from copilotkit.runtime_py.app.middleware import setup_all_middleware
        from copilotkit.runtime_py.app.runtime_mount import setup_graphql_middleware

        # Setup the comprehensive middleware stack
        setup_all_middleware(app, self.config)

        # Setup GraphQL-specific middleware
        setup_graphql_middleware(app, self)

        self.logger.info("Comprehensive middleware stack setup completed")

    def _mount_graphql_endpoints(
        self, app: FastAPI, graphql_path: str, include_playground: bool
    ) -> None:
        """
        Mount GraphQL endpoints to the FastAPI application.

        Args:
            app: FastAPI application to mount to
            graphql_path: Path for GraphQL endpoint
            include_playground: Whether to include GraphQL playground
        """
        # Import here to avoid circular imports
        from copilotkit.runtime_py.app.runtime_mount import mount_graphql_to_fastapi

        mount_graphql_to_fastapi(
            app=app,
            runtime=self,
            path=graphql_path,
            include_playground=include_playground,
            include_health_checks=True,
        )
        self.logger.info(f"GraphQL endpoints mounted at: {graphql_path}")

    def get_graphql_context(self) -> dict[str, Any]:
        """
        Get context data for GraphQL execution.

        This method provides context data that will be available to all
        GraphQL resolvers via the info.context parameter.

        Returns:
            Dictionary containing context data for GraphQL execution.
        """
        return {
            "runtime": self,
            "providers": self._providers,
            "config": self.config,
            "logger": self.logger,
        }

    def create_fastapi_app(self) -> FastAPI:
        """
        Create a standalone FastAPI application with the runtime mounted.

        Returns:
            A new FastAPI application with the runtime mounted.
        """
        app = FastAPI(
            title="CopilotKit Python Runtime",
            description="Production-ready Python implementation of CopilotKit Runtime",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # Mount the runtime
        self.mount_to_fastapi(app, path="/api/copilotkit")

        return app

    async def start(self) -> None:
        """
        Start the runtime and initialize all components.

        This method should be called before handling any requests.
        """
        self.logger.info("Starting CopilotRuntime")

        # Initialize providers
        for provider_name, provider in self._providers.items():
            try:
                if hasattr(provider, "initialize"):
                    await provider.initialize()
                self.logger.debug(f"Initialized provider: {provider_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize provider '{provider_name}': {e}")

        # Pre-cache agents
        try:
            await self.discover_agents()
        except Exception as e:
            self.logger.warning(f"Failed to pre-cache agents: {e}")

        self.logger.info("CopilotRuntime started successfully")

    async def stop(self) -> None:
        """
        Stop the runtime and cleanup resources.
        """
        self.logger.info("Stopping CopilotRuntime")

        # Close active streams
        for stream_id in list(self._active_streams.keys()):
            try:
                # TODO: Implement proper stream cleanup in later phases
                del self._active_streams[stream_id]
            except Exception as e:
                self.logger.error(f"Error closing stream {stream_id}: {e}")

        # Cleanup providers
        for provider_name, provider in self._providers.items():
            try:
                if hasattr(provider, "cleanup"):
                    await provider.cleanup()
                self.logger.debug(f"Cleaned up provider: {provider_name}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup provider '{provider_name}': {e}")

        self.logger.info("CopilotRuntime stopped")

    async def __aenter__(self) -> CopilotRuntime:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    def __repr__(self) -> str:
        """String representation of the runtime."""
        return (
            f"CopilotRuntime("
            f"providers={len(self._providers)}, "
            f"mounted={'yes' if self._mounted_app else 'no'}"
            f")"
        )
