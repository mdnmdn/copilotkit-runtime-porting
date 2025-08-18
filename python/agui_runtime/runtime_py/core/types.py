"""
Core types and enums for CopilotKit Runtime Python.

This module defines all the fundamental types, enums, and data structures
that match the GraphQL schema contract from the TypeScript runtime.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """The role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"


class MessageStatus(str, Enum):
    """The status of a message."""

    PENDING = "pending"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CopilotRequestType(str, Enum):
    """The type of Copilot request."""

    CHAT = "Chat"
    TASK = "Task"
    TEXTAREA_COMPLETION = "TextareaCompletion"
    TEXTAREA_POPOVER = "TextareaPopover"
    SUGGESTION = "Suggestion"


class ActionInputAvailability(str, Enum):
    """The availability of a frontend action."""

    DISABLED = "disabled"
    ENABLED = "enabled"
    REMOTE = "remote"


class ResponseStatus(str, Enum):
    """Status of a runtime response."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


# Base message types
class BaseMessage(BaseModel):
    """Base class for all message types."""

    id: str = Field(..., description="Unique identifier for the message")
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow, description="When the message was created"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime.datetime: lambda v: v.isoformat()}


class TextMessage(BaseMessage):
    """A text message in the conversation."""

    role: MessageRole = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The text content of the message")
    status: MessageStatus = Field(
        default=MessageStatus.COMPLETED, description="The status of the message"
    )


class ActionMessage(BaseMessage):
    """A message representing an action/tool execution."""

    role: MessageRole = Field(default=MessageRole.TOOL, description="Message role")
    action_name: str = Field(..., description="Name of the action being executed")
    action_input: dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for the action"
    )
    action_output: dict[str, Any] | None = Field(
        default=None, description="Output result from the action"
    )
    status: MessageStatus = Field(
        default=MessageStatus.PENDING, description="Current status of the action"
    )


class AgentStateMessage(BaseMessage):
    """A message representing agent state changes."""

    role: MessageRole = Field(default=MessageRole.SYSTEM, description="Message role")
    agent_name: str = Field(..., description="Name of the agent")
    node_name: str | None = Field(default=None, description="Current node in agent execution graph")
    state_data: dict[str, Any] = Field(default_factory=dict, description="Current agent state data")
    running: bool = Field(default=False, description="Whether agent is currently running")
    status: MessageStatus = Field(
        default=MessageStatus.PENDING, description="Current status of the agent"
    )


# Union type for all message types
Message = TextMessage | ActionMessage | AgentStateMessage


class MetaEvent(BaseModel):
    """Meta events for runtime communication."""

    event_type: str = Field(..., description="Type of the meta event")
    data: dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow, description="When the event occurred"
    )


class AgentDescriptor(BaseModel):
    """Descriptor for an available agent."""

    name: str = Field(..., description="Unique name of the agent")
    description: str = Field(..., description="Human-readable description")
    version: str = Field(default="1.0.0", description="Agent version")
    capabilities: list[str] = Field(default_factory=list, description="List of agent capabilities")
    input_schema: dict[str, Any] | None = Field(
        default=None, description="JSON schema for agent input"
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="JSON schema for agent output"
    )


class AgentState(BaseModel):
    """Agent execution state."""

    thread_id: str = Field(..., description="Thread ID this state belongs to")
    agent_name: str = Field(..., description="Name of the agent")
    data: dict[str, Any] = Field(default_factory=dict, description="Agent state data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow, description="Last update timestamp"
    )


class RuntimeEvent(BaseModel):
    """Runtime event for streaming responses."""

    event_type: str = Field(..., description="Type of runtime event")
    data: Message | MetaEvent | AgentState = Field(..., description="Event payload")
    sequence: int = Field(..., description="Sequence number for ordering")


class RuntimeContext(BaseModel):
    """Runtime execution context."""

    thread_id: str = Field(..., description="Conversation thread ID")
    user_id: str | None = Field(default=None, description="User ID if available")
    session_id: str | None = Field(default=None, description="Session ID")
    request_type: CopilotRequestType = Field(
        default=CopilotRequestType.CHAT, description="Type of request"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional context properties"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers from the request"
    )


class RuntimeConfig(BaseModel):
    """Runtime configuration settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    graphql_path: str = Field(default="/api/copilotkit", description="GraphQL endpoint path")

    # Provider configuration
    enabled_providers: list[str] = Field(
        default_factory=lambda: ["langgraph"], description="List of enabled providers"
    )

    # Storage configuration
    state_store_backend: str = Field(
        default="memory", description="State storage backend (memory, redis, postgresql)"
    )
    redis_url: str | None = Field(default=None, description="Redis connection URL")
    database_url: str | None = Field(default=None, description="Database connection URL")

    # Security settings
    api_keys: list[str] = Field(default_factory=list, description="Valid API keys")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"], description="CORS allowed origins"
    )

    # Performance settings
    max_concurrent_requests: int = Field(default=100, description="Maximum concurrent requests")
    request_timeout_seconds: int = Field(default=300, description="Request timeout in seconds")

    # GraphQL configuration
    graphql_playground_enabled: bool = Field(default=True, description="Enable GraphQL Playground")
    graphql_introspection_enabled: bool = Field(
        default=True, description="Enable GraphQL introspection"
    )
    graphql_debug: bool = Field(default=False, description="Enable GraphQL debug mode")

    # Middleware configuration
    middleware_stack_enabled: bool = Field(
        default=True, description="Enable comprehensive middleware stack"
    )
    error_reporting_enabled: bool = Field(
        default=True, description="Enable detailed error reporting"
    )
    request_logging_enabled: bool = Field(
        default=True, description="Enable request logging middleware"
    )
    auth_middleware_enabled: bool = Field(
        default=False, description="Enable authentication middleware"
    )

    # Development/Debug settings
    debug: bool = Field(default=False, description="Enable debug mode with detailed error messages")
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "AGUI_RUNTIME_"
        case_sensitive = False


class CopilotError(BaseModel):
    """Standardized error response."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    trace_id: str | None = Field(default=None, description="Request trace ID for debugging")


# Common error codes
class CopilotErrorCode:
    """Standard error codes for CopilotKit runtime."""

    # Client errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"

    # Agent errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"

    # State errors
    STATE_LOAD_FAILED = "STATE_LOAD_FAILED"
    STATE_SAVE_FAILED = "STATE_SAVE_FAILED"
    INVALID_STATE = "INVALID_STATE"


# Type aliases for convenience
MessageUnion = TextMessage | ActionMessage | AgentStateMessage
EventData = Message | MetaEvent | AgentState
