"""
CopilotKit Runtime Providers - AI framework integrations.

This module contains provider implementations for various AI frameworks,
enabling them to work seamlessly with the CopilotKit Python Runtime.
Each provider implements the AgentProvider interface to provide a
standardized integration layer.

Supported Providers:
- LangGraph: State-based agent orchestration framework (primary)
- CrewAI: Multi-agent collaboration framework (secondary)
- Custom: Extensible interface for additional frameworks

Key Components:
- Provider implementations for each supported AI framework
- Provider registration and discovery utilities
- Framework-specific state management
- Tool and action integration adapters
- Agent lifecycle management

Example Usage:
    ```python
    from copilotkit.runtime_py.providers import LangGraphProvider
    from copilotkit.runtime_py.core import CopilotRuntime

    # Create provider instance
    provider = LangGraphProvider()

    # Register with runtime
    runtime = CopilotRuntime()
    runtime.add_provider(provider)
    ```

Provider Interface:
    All providers must implement the AgentProvider abstract class from
    copilotkit.runtime_py.core.provider, which defines:
    - list_agents(): Discover available agents
    - execute_run(): Execute agent with streaming events
    - load_state()/save_state(): State persistence (optional)
    - initialize()/cleanup(): Lifecycle management (optional)
"""

# Import base provider interface from core
from copilotkit.runtime_py.core.provider import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentProvider,
    ProviderError,
    StateLoadError,
    StateSaveError,
)

# Provider implementations will be imported here as they are implemented
# from copilotkit.runtime_py.providers.langgraph import LangGraphProvider
# from copilotkit.runtime_py.providers.crewai import CrewAIProvider
# from copilotkit.runtime_py.providers.custom import CustomProvider

__version__ = "0.1.0"

# Provider registry for dynamic discovery
AVAILABLE_PROVIDERS = {
    # Will be populated as providers are implemented
    # "langgraph": "copilotkit.runtime_py.providers.langgraph:LangGraphProvider",
    # "crewai": "copilotkit.runtime_py.providers.crewai:CrewAIProvider",
}


def get_available_providers() -> dict[str, str]:
    """
    Get a dictionary of available provider names and their import paths.

    Returns:
        Dictionary mapping provider names to their import paths.
    """
    return AVAILABLE_PROVIDERS.copy()


def load_provider_class(provider_name: str) -> type[AgentProvider]:
    """
    Dynamically load a provider class by name.

    Args:
        provider_name: Name of the provider to load

    Returns:
        The provider class

    Raises:
        ValueError: If provider is not available
        ImportError: If provider cannot be imported
    """
    if provider_name not in AVAILABLE_PROVIDERS:
        available = list(AVAILABLE_PROVIDERS.keys())
        raise ValueError(f"Provider '{provider_name}' not available. Available: {available}")

    import_path = AVAILABLE_PROVIDERS[provider_name]
    module_path, class_name = import_path.split(":")

    try:
        import importlib

        module = importlib.import_module(module_path)
        provider_class = getattr(module, class_name)
        return provider_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import provider '{provider_name}': {e}")


def create_provider(provider_name: str, **kwargs) -> AgentProvider:
    """
    Create a provider instance by name.

    Args:
        provider_name: Name of the provider to create
        **kwargs: Additional arguments to pass to the provider constructor

    Returns:
        Initialized provider instance

    Raises:
        ValueError: If provider is not available
        ImportError: If provider cannot be imported
    """
    provider_class = load_provider_class(provider_name)
    return provider_class(**kwargs)


# Public API
__all__ = [
    # Base interfaces (re-exported from core)
    "AgentProvider",
    "ProviderError",
    "AgentNotFoundError",
    "AgentExecutionError",
    "StateLoadError",
    "StateSaveError",
    # Provider implementations (will be added as they are implemented)
    # "LangGraphProvider",
    # "CrewAIProvider",
    # "CustomProvider",
    # Utility functions
    "get_available_providers",
    "load_provider_class",
    "create_provider",
    # Provider registry
    "AVAILABLE_PROVIDERS",
]
