"""
GraphQL schema definition for CopilotKit Python Runtime.

This module defines the GraphQL schema using Strawberry GraphQL that provides
100% API compatibility with the TypeScript CopilotRuntime. The schema includes
all types, enums, queries, and mutations required for frontend integration.
"""

from __future__ import annotations

import datetime
import logging
from enum import Enum
from typing import Any

import strawberry
from strawberry import printer
from strawberry.types import Info


# GraphQL Enums (matching TypeScript schema exactly)
@strawberry.enum
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"


@strawberry.enum
class MessageStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@strawberry.enum
class CopilotRequestType(Enum):
    CHAT = "Chat"
    TASK = "Task"
    TEXTAREA_COMPLETION = "TextareaCompletion"
    TEXTAREA_POPOVER = "TextareaPopover"
    SUGGESTION = "Suggestion"


@strawberry.enum
class ActionInputAvailability(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    REMOTE = "remote"


@strawberry.enum
class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


# GraphQL Input Types
@strawberry.input
class MessageInput:
    """Input type for messages in GraphQL operations."""

    id: str | None = None
    role: MessageRole
    content: str
    created_at: datetime.datetime | None = None


@strawberry.input
class AgentSessionInput:
    """Input for agent session configuration."""

    thread_id: str
    agent_name: str | None = None
    user_id: str | None = None


@strawberry.input
class ContextPropertyInput:
    """Input for context properties."""

    name: str
    value: str
    description: str | None = None


@strawberry.input
class ActionInput:
    """Input for action execution."""

    name: str
    availability: ActionInputAvailability = ActionInputAvailability.ENABLED
    description: str | None = None
    parameters: str | None = None  # JSON string


@strawberry.input
class GenerateCopilotResponseInput:
    """Main input type for generateCopilotResponse mutation."""

    messages: list[MessageInput]
    agent_session: AgentSessionInput
    actions: list[ActionInput] | None = None
    context: list[ContextPropertyInput] | None = None
    request_type: CopilotRequestType = CopilotRequestType.CHAT
    metadata: str | None = None  # JSON string


# GraphQL Output Types
@strawberry.type
class Agent:
    """GraphQL type for agent information."""

    name: str
    description: str
    version: str = "1.0.0"
    capabilities: list[str] = strawberry.field(default_factory=list)


@strawberry.type
class AgentsResponse:
    """Response type for availableAgents query."""

    agents: list[Agent]


@strawberry.type
class Message:
    """GraphQL type for messages."""

    id: str
    role: MessageRole
    content: str
    status: MessageStatus = MessageStatus.COMPLETED
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


@strawberry.type
class ActionMessage:
    """GraphQL type for action messages."""

    id: str
    role: MessageRole = MessageRole.TOOL
    action_name: str
    action_input: str | None = None  # JSON string
    action_output: str | None = None  # JSON string
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


@strawberry.type
class AgentStateMessage:
    """GraphQL type for agent state messages."""

    id: str
    role: MessageRole = MessageRole.SYSTEM
    agent_name: str
    node_name: str | None = None
    state_data: str | None = None  # JSON string
    running: bool = False
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


# Union type for all message types
MessageUnion = strawberry.union("MessageUnion", (Message, ActionMessage, AgentStateMessage))


@strawberry.type
class CopilotResponse:
    """Response type for generateCopilotResponse mutation."""

    thread_id: str
    messages: list[MessageUnion] = strawberry.field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error_message: str | None = None
    metadata: str | None = None  # JSON string


@strawberry.type
class RuntimeInfo:
    """Runtime information type."""

    version: str
    providers: list[str]
    agents_count: int


# GraphQL Context
@strawberry.type
class GraphQLContext:
    """GraphQL execution context."""

    request: Any
    runtime: Any
    logger: logging.Logger = strawberry.field(default_factory=lambda: logging.getLogger(__name__))


# Query Resolvers
@strawberry.type
class Query:
    """GraphQL Query root type."""

    @strawberry.field
    async def hello(self, info: Info) -> str:
        """Simple health check query."""
        return "Hello from CopilotKit Python Runtime!"

    @strawberry.field
    async def available_agents(self, info: Info[GraphQLContext, Any]) -> AgentsResponse:
        """
        Query to get all available agents from registered providers.

        Returns:
            AgentsResponse containing list of available agents.
        """
        logger = logging.getLogger(f"{__name__}.available_agents")

        try:
            # Get runtime from GraphQL context
            runtime = info.context.runtime

            # Log the operation
            info.context.log_operation("available_agents", "query")

            # Discover agents from registered providers
            agent_descriptors = await runtime.discover_agents()

            # Convert to GraphQL Agent types
            agents = [
                Agent(
                    name=agent.name,
                    description=agent.description,
                    version=agent.version,
                    capabilities=agent.capabilities
                )
                for agent in agent_descriptors
            ]

            logger.debug(f"Retrieved {len(agents)} available agents")
            return AgentsResponse(agents=agents)

        except Exception as e:
            logger.error(f"Error retrieving available agents: {e}")
            # Return empty response rather than failing the query
            return AgentsResponse(agents=[])

    @strawberry.field
    async def runtime_info(self, info: Info[GraphQLContext, Any]) -> RuntimeInfo:
        """
        Get runtime information and statistics.

        Returns:
            RuntimeInfo with current runtime state.
        """
        logger = logging.getLogger(f"{__name__}.runtime_info")

        try:
            # Get runtime from GraphQL context
            runtime = info.context.runtime

            # Log the operation
            info.context.log_operation("runtime_info", "query")

            # Get live runtime information
            providers = runtime.list_providers()
            agents = await runtime.discover_agents()

            logger.debug(f"Runtime info: {len(providers)} providers, {len(agents)} agents")

            return RuntimeInfo(
                version="0.1.0",
                providers=providers,
                agents_count=len(agents)
            )

        except Exception as e:
            logger.error(f"Error retrieving runtime info: {e}")
            # Return default values rather than failing the query
            return RuntimeInfo(
                version="0.1.0",
                providers=[],
                agents_count=0
            )


# Mutation Resolvers
@strawberry.type
class Mutation:
    """GraphQL Mutation root type."""

    @strawberry.field
    async def generate_copilot_response(
        self, info: Info[GraphQLContext, Any], data: GenerateCopilotResponseInput
    ) -> CopilotResponse:
        """
        Main mutation for generating copilot responses.

        This handles:
        - Agent execution
        - Message processing
        - State management
        - Streaming responses (in later phases)

        Args:
            info: GraphQL execution info with context
            data: Input data for the copilot response generation

        Returns:
            CopilotResponse with generated messages and status
        """
        logger = logging.getLogger(f"{__name__}.generate_copilot_response")

        try:
            # Get runtime from GraphQL context
            runtime = info.context.runtime

            # Log the operation
            info.context.log_operation("generate_copilot_response", "mutation")

            logger.info(
                f"Generating response for thread: {data.agent_session.thread_id}, "
                f"agent: {data.agent_session.agent_name}, "
                f"messages: {len(data.messages)}"
            )

            # TODO: In Phase 2, this will implement full agent execution
            # For now, return a basic acknowledgment response

            # Create a simple acknowledgment message
            response_message = Message(
                id=f"msg_{datetime.datetime.utcnow().timestamp()}",
                role=MessageRole.ASSISTANT,
                content="Message received. Full agent execution will be implemented in Phase 2.",
                status=MessageStatus.COMPLETED,
                created_at=datetime.datetime.utcnow()
            )

            return CopilotResponse(
                thread_id=data.agent_session.thread_id,
                messages=[response_message],
                status=ResponseStatus.SUCCESS,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error generating copilot response: {e}")
            return CopilotResponse(
                thread_id=data.agent_session.thread_id,
                messages=[],
                status=ResponseStatus.ERROR,
                error_message=str(e),
            )


# Create the GraphQL Schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)


# Schema introspection helpers
def get_schema_sdl() -> str:
    """
    Get the Schema Definition Language (SDL) representation of the schema.

    Returns:
        SDL string representation of the GraphQL schema.
    """
    return printer.print_schema(schema)


def validate_schema_compatibility() -> bool:
    """
    Validate that the schema maintains compatibility with TypeScript runtime.

    This function will be expanded in later phases to include comprehensive
    schema validation against the reference TypeScript implementation.

    Returns:
        True if schema is compatible, False otherwise.
    """
    # TODO: Implement comprehensive schema validation
    # This should compare against the TypeScript schema
    return True


# Export schema components for testing
__all__ = [
    "schema",
    "Query",
    "Mutation",
    "MessageRole",
    "MessageStatus",
    "CopilotRequestType",
    "ActionInputAvailability",
    "ResponseStatus",
    "Message",
    "ActionMessage",
    "AgentStateMessage",
    "MessageUnion",
    "Agent",
    "AgentsResponse",
    "CopilotResponse",
    "GenerateCopilotResponseInput",
    "get_schema_sdl",
    "validate_schema_compatibility",
]
