"""
Abstract AgentProvider interface for pluggable AI frameworks.

This module defines the base AgentProvider class that all AI framework
integrations must implement. It provides a standardized interface for
integrating different agent frameworks (LangGraph, CrewAI, etc.) with
the CopilotKit runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from copilotkit.runtime_py.core.types import (
    AgentDescriptor,
    AgentState,
    Message,
    RuntimeContext,
    RuntimeEvent,
)


class AgentProvider(ABC):
    """
    Abstract base class for AI framework providers.

    All agent providers must implement this interface to integrate with
    the CopilotKit runtime. This provides a pluggable architecture that
    allows different AI frameworks to work seamlessly with the same
    GraphQL frontend interface.

    Example Implementation:
        ```python
        class MyFrameworkProvider(AgentProvider):

            @property
            def name(self) -> str:
                return "my_framework"

            async def list_agents(self) -> List[AgentDescriptor]:
                # Return available agents from your framework
                return [...]

            async def execute_run(
                self,
                messages: List[Message],
                context: RuntimeContext
            ) -> AsyncIterator[RuntimeEvent]:
                # Execute agent and yield events
                yield ...
        ```
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name identifier for this provider.

        Returns:
            A unique string identifying this provider (e.g., "langgraph", "crewai").
        """
        pass

    @property
    def version(self) -> str:
        """
        Version of this provider implementation.

        Returns:
            Version string for this provider.
        """
        return "1.0.0"

    @property
    def description(self) -> str:
        """
        Human-readable description of this provider.

        Returns:
            Description of what this provider does.
        """
        return f"Agent provider for {self.name}"

    @abstractmethod
    async def list_agents(self) -> list[AgentDescriptor]:
        """
        List all available agents from this provider.

        This method should discover and return descriptors for all agents
        that this provider can execute. The runtime will call this during
        agent discovery to populate the available agents list.

        Returns:
            List of agent descriptors available from this provider.

        Raises:
            ProviderError: If agent discovery fails.
        """
        pass

    @abstractmethod
    async def execute_run(
        self,
        agent_name: str,
        messages: list[Message],
        context: RuntimeContext,
    ) -> AsyncIterator[RuntimeEvent]:
        """
        Execute an agent run and stream runtime events.

        This is the core method that executes an agent with the given input
        and streams back runtime events. Events should include message updates,
        state changes, and meta-events as appropriate.

        Args:
            agent_name: Name of the agent to execute.
            messages: List of input messages for the agent.
            context: Runtime context containing thread ID, user info, etc.

        Yields:
            RuntimeEvent: Stream of events during agent execution.

        Raises:
            AgentNotFoundError: If the specified agent doesn't exist.
            AgentExecutionError: If agent execution fails.
        """
        pass

    async def load_state(self, thread_id: str, agent_name: str) -> AgentState | None:
        """
        Load persisted state for an agent in a specific thread.

        Providers can override this to implement custom state loading
        behavior. The default implementation returns None, indicating
        no persisted state.

        Args:
            thread_id: Unique identifier for the conversation thread.
            agent_name: Name of the agent whose state to load.

        Returns:
            The loaded agent state, or None if no state exists.

        Raises:
            StateLoadError: If state loading fails.
        """
        return None

    async def save_state(
        self,
        thread_id: str,
        agent_name: str,
        state: AgentState,
    ) -> None:
        """
        Save agent state for persistence across conversations.

        Providers can override this to implement custom state saving
        behavior. The default implementation is a no-op.

        Args:
            thread_id: Unique identifier for the conversation thread.
            agent_name: Name of the agent whose state to save.
            state: The agent state to persist.

        Raises:
            StateSaveError: If state saving fails.
        """
        pass

    async def get_agent_info(self, agent_name: str) -> AgentDescriptor | None:
        """
        Get detailed information about a specific agent.

        Args:
            agent_name: Name of the agent to get information for.

        Returns:
            Agent descriptor if found, None otherwise.
        """
        agents = await self.list_agents()
        for agent in agents:
            if agent.name == agent_name:
                return agent
        return None

    async def validate_agent_input(self, agent_name: str, messages: list[Message]) -> bool:
        """
        Validate input messages for an agent before execution.

        Providers can override this to implement custom validation logic.
        The default implementation always returns True.

        Args:
            agent_name: Name of the agent to validate input for.
            messages: Input messages to validate.

        Returns:
            True if input is valid, False otherwise.
        """
        return True

    async def initialize(self) -> None:
        """
        Initialize the provider.

        This method is called by the runtime when the provider is registered.
        Providers can override this to perform setup tasks like loading
        configurations, establishing connections, etc.
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up provider resources.

        This method is called by the runtime when shutting down.
        Providers can override this to perform cleanup tasks like
        closing connections, saving state, etc.
        """
        pass

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"


class ProviderError(Exception):
    """Base exception for provider-related errors."""

    def __init__(self, message: str, provider_name: str, cause: Exception | None = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.cause = cause


class AgentNotFoundError(ProviderError):
    """Raised when a requested agent is not found."""

    def __init__(self, agent_name: str, provider_name: str):
        super().__init__(
            f"Agent '{agent_name}' not found in provider '{provider_name}'", provider_name
        )
        self.agent_name = agent_name


class AgentExecutionError(ProviderError):
    """Raised when agent execution fails."""

    def __init__(
        self, message: str, agent_name: str, provider_name: str, cause: Exception | None = None
    ):
        super().__init__(message, provider_name, cause)
        self.agent_name = agent_name


class StateLoadError(ProviderError):
    """Raised when loading agent state fails."""

    pass


class StateSaveError(ProviderError):
    """Raised when saving agent state fails."""

    pass


# Utility functions for provider implementations


async def validate_agent_exists(provider: AgentProvider, agent_name: str) -> AgentDescriptor:
    """
    Validate that an agent exists in a provider and return its descriptor.

    Args:
        provider: The provider to check.
        agent_name: Name of the agent to validate.

    Returns:
        The agent descriptor.

    Raises:
        AgentNotFoundError: If the agent is not found.
    """
    agent_info = await provider.get_agent_info(agent_name)
    if agent_info is None:
        raise AgentNotFoundError(agent_name, provider.name)
    return agent_info


def create_runtime_event(event_type: str, data: Any, sequence: int) -> RuntimeEvent:
    """
    Helper function to create a runtime event.

    Args:
        event_type: Type of the runtime event.
        data: Event payload data.
        sequence: Sequence number for event ordering.

    Returns:
        A new RuntimeEvent instance.
    """
    return RuntimeEvent(event_type=event_type, data=data, sequence=sequence)
