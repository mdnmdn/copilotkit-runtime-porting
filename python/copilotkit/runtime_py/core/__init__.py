"""
CopilotKit Runtime Core - Core runtime components and interfaces.

This module contains the essential components for the CopilotKit Python Runtime:
- CopilotRuntime: Main orchestrator class
- AgentProvider: Abstract provider interface for AI frameworks
- Type definitions: Core types, enums, and data structures
- Configuration: Runtime configuration management

Example Usage:
    ```python
    from copilotkit.runtime_py.core import CopilotRuntime, RuntimeConfig

    config = RuntimeConfig(host="0.0.0.0", port=8000)
    runtime = CopilotRuntime(config=config)
    ```
"""

from copilotkit.runtime_py.core.provider import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentProvider,
    ProviderError,
    StateLoadError,
    StateSaveError,
    create_runtime_event,
    validate_agent_exists,
)
from copilotkit.runtime_py.core.runtime import CopilotRuntime
from copilotkit.runtime_py.core.types import (
    ActionInputAvailability,
    ActionMessage,
    # Agent Types
    AgentDescriptor,
    AgentState,
    AgentStateMessage,
    # Message Types
    BaseMessage,
    # Error Types
    CopilotError,
    CopilotErrorCode,
    CopilotRequestType,
    # Type Aliases
    EventData,
    Message,
    # Enums
    MessageRole,
    MessageStatus,
    MessageUnion,
    # Event Types
    MetaEvent,
    ResponseStatus,
    RuntimeConfig,
    # Context Types
    RuntimeContext,
    RuntimeEvent,
    TextMessage,
)

__version__ = "0.1.0"

# Public API
__all__ = [
    # Main Classes
    "CopilotRuntime",
    "AgentProvider",
    # Enums
    "MessageRole",
    "MessageStatus",
    "CopilotRequestType",
    "ActionInputAvailability",
    "ResponseStatus",
    # Message Types
    "BaseMessage",
    "TextMessage",
    "ActionMessage",
    "AgentStateMessage",
    "Message",
    "MessageUnion",
    # Event Types
    "MetaEvent",
    "RuntimeEvent",
    # Agent Types
    "AgentDescriptor",
    "AgentState",
    # Context Types
    "RuntimeContext",
    "RuntimeConfig",
    # Error Types
    "CopilotError",
    "CopilotErrorCode",
    "ProviderError",
    "AgentNotFoundError",
    "AgentExecutionError",
    "StateLoadError",
    "StateSaveError",
    # Utilities
    "validate_agent_exists",
    "create_runtime_event",
    # Type Aliases
    "EventData",
]
