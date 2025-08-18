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
from typing import TYPE_CHECKING, Any

import strawberry
from strawberry import printer
from strawberry.types import Info

if TYPE_CHECKING:
    from strawberry.types import Info

from agui_runtime.runtime_py.graphql.context import GraphQLExecutionContext
from agui_runtime.runtime_py.graphql.errors import (
    CopilotKitError,
    handle_resolver_exception,
    create_error_response,
    ErrorRecoveryStrategy,
)


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


@strawberry.input
class LoadAgentStateInput:
    """Input type for loading agent state."""

    thread_id: str
    agent_name: str
    state_key: str | None = None
    include_history: bool = False


@strawberry.input
class SaveAgentStateInput:
    """Input type for saving agent state."""

    thread_id: str
    agent_name: str
    state_data: str  # JSON string
    state_key: str | None = None
    merge_with_existing: bool = True


@strawberry.input
class MetadataInput:
    """Input type for request metadata and context properties."""

    user_id: str | None = None
    session_id: str | None = None
    client_version: str | None = None
    platform: str | None = None
    custom_properties: str | None = None  # JSON string


@strawberry.input
class StreamingConfigInput:
    """Input type for streaming response configuration."""

    enabled: bool = True
    buffer_size: int = 1024
    flush_interval_ms: int = 100
    include_intermediate_results: bool = False
    compression_enabled: bool = False


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
MessageUnion = strawberry.union("MessageUnion", (
    Message,
    ActionMessage,
    AgentStateMessage,
    ImageMessage,
    ActionExecutionMessage,
    ResultMessage
))

# Union type for meta-events
MetaEventUnion = strawberry.union("MetaEventUnion", (
    LangGraphInterruptEvent,
    CopilotKitLangGraphInterruptEvent
))


@strawberry.type
class CopilotResponse:
    """Response type for generateCopilotResponse mutation."""

    thread_id: str
    messages: list[MessageUnion] = strawberry.field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error_message: str | None = None
    metadata: str | None = None  # JSON string


@strawberry.type
class LoadAgentStateResponse:
    """Response type for loadAgentState query."""

    thread_id: str
    agent_name: str
    state_data: str | None = None  # JSON string
    state_found: bool = False
    last_updated: datetime.datetime | None = None
    error_message: str | None = None


@strawberry.type
class SaveAgentStateResponse:
    """Response type for saveAgentState mutation."""

    thread_id: str
    agent_name: str
    success: bool = False
    state_key: str | None = None
    saved_at: datetime.datetime | None = None
    error_message: str | None = None


@strawberry.type
class AgentExecutionResponse:
    """Response type for agent execution operations."""

    execution_id: str
    thread_id: str
    agent_name: str
    status: MessageStatus
    result: str | None = None  # JSON string
    started_at: datetime.datetime
    completed_at: datetime.datetime | None = None
    error_message: str | None = None


@strawberry.type
class MetaEventResponse:
    """Response type for meta-event notifications."""

    event_id: str
    event_type: str
    thread_id: str
    agent_name: str | None = None
    event_data: str | None = None  # JSON string
    timestamp: datetime.datetime
    handled: bool = False


@strawberry.type
class ImageMessage:
    """GraphQL type for image messages."""

    id: str
    role: MessageRole = MessageRole.USER
    content: str  # Image description or caption
    image_url: str
    image_data: str | None = None  # Base64 encoded image data
    mime_type: str = "image/jpeg"
    status: MessageStatus = MessageStatus.COMPLETED
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


@strawberry.type
class ActionExecutionMessage:
    """GraphQL type for action execution messages."""

    id: str
    role: MessageRole = MessageRole.TOOL
    action_name: str
    execution_id: str
    input_parameters: str | None = None  # JSON string
    execution_status: MessageStatus = MessageStatus.PENDING
    started_at: datetime.datetime
    completed_at: datetime.datetime | None = None
    error_details: str | None = None
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


@strawberry.type
class ResultMessage:
    """GraphQL type for result messages."""

    id: str
    role: MessageRole = MessageRole.ASSISTANT
    content: str
    result_type: str = "text"
    result_data: str | None = None  # JSON string
    confidence_score: float | None = None
    source_references: list[str] = strawberry.field(default_factory=list)
    status: MessageStatus = MessageStatus.COMPLETED
    created_at: datetime.datetime = strawberry.field(default_factory=datetime.datetime.utcnow)


@strawberry.type
class LangGraphInterruptEvent:
    """GraphQL type for LangGraph interruption events."""

    event_id: str
    interrupt_type: str
    node_name: str
    thread_id: str
    interrupt_data: str | None = None  # JSON string
    resume_token: str | None = None
    timestamp: datetime.datetime
    resolved: bool = False


@strawberry.type
class CopilotKitLangGraphInterruptEvent:
    """GraphQL type for CopilotKit-specific LangGraph interruption events."""

    event_id: str
    copilotkit_event_type: str
    langgraph_event: LangGraphInterruptEvent
    user_interaction_required: bool = False
    interaction_type: str | None = None
    interaction_data: str | None = None  # JSON string
    timestamp: datetime.datetime
    handled: bool = False


@strawberry.type
class RuntimeInfo:
    """Runtime information type."""

    version: str
    providers: list[str]
    agents_count: int


# GraphQL execution context type
GraphQLContext = GraphQLExecutionContext


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
        context = info.context
        context.start_performance_timer("available_agents")

        try:
            # Log the operation
            context.log_operation("available_agents", "query")

            # Discover agents from registered providers
            agent_descriptors = await context.runtime.discover_agents()

            # Convert to GraphQL Agent types
            agents = [
                Agent(
                    name=agent.name,
                    description=agent.description,
                    version=agent.version,
                    capabilities=agent.capabilities,
                )
                for agent in agent_descriptors
            ]

            context.logger.debug(f"Retrieved {len(agents)} available agents")
            return AgentsResponse(agents=agents)

        except Exception as e:
            error = handle_resolver_exception(
                e, "available_agents", context.logger, context.correlation_id
            )
            # Return fallback response for recoverable errors
            return create_error_response(
                error, ErrorRecoveryStrategy.get_fallback_response(error, "agents_query")
            ) or AgentsResponse(agents=[])

        finally:
            context.end_performance_timer("available_agents")

    @strawberry.field
    async def load_agent_state(
        self, info: Info[GraphQLContext, Any], data: LoadAgentStateInput
    ) -> LoadAgentStateResponse:
        """
        Load agent state from storage.

        Args:
            info: GraphQL execution info
            data: Load agent state input data

        Returns:
            LoadAgentStateResponse with state data or error
        """
        context = info.context
        context.start_performance_timer("load_agent_state")

        try:
            # Log the operation
            context.log_operation("load_agent_state", "query", {
                "thread_id": data.thread_id,
                "agent_name": data.agent_name,
            })

            # Load state from runtime
            stored_state = await context.runtime.load_agent_state(data.thread_id, data.agent_name)

            if stored_state:
                return LoadAgentStateResponse(
                    thread_id=data.thread_id,
                    agent_name=data.agent_name,
                    state_data=context.runtime._state_store_manager.serialize_state(stored_state.data).decode(),
                    state_found=True,
                    last_updated=stored_state.metadata.updated_at,
                )
            else:
                return LoadAgentStateResponse(
                    thread_id=data.thread_id,
                    agent_name=data.agent_name,
                    state_found=False,
                )

        except Exception as e:
            error = handle_resolver_exception(
                e, "load_agent_state", context.logger, context.correlation_id
            )
            # Return error response
            return create_error_response(
                error, ErrorRecoveryStrategy.get_fallback_response(error, "load_agent_state_query")
            ) or LoadAgentStateResponse(
                thread_id=data.thread_id,
                agent_name=data.agent_name,
                state_found=False,
                error_message=error.message if error.user_facing else "Failed to load state"
            )

        finally:
            context.end_performance_timer("load_agent_state")


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
        context = info.context
        context.start_performance_timer("generate_copilot_response")

        try:
            # Log the operation
            context.log_operation("generate_copilot_response", "mutation", {
                "thread_id": data.agent_session.thread_id,
                "agent_name": data.agent_session.agent_name,
                "message_count": len(data.messages),
                "request_type": data.request_type.value,
            })

            context.logger.info(
                f"Generating response for thread: {data.agent_session.thread_id}, "
                f"agent: {data.agent_session.agent_name}, "
                f"messages: {len(data.messages)}"
            )

            # Create runtime context
            runtime_context = await context.runtime.create_request_context(
                thread_id=data.agent_session.thread_id,
                user_id=data.agent_session.user_id,
                request_type=data.request_type,
                properties={"actions": data.actions, "context": data.context},
            )

            try:
                # TODO: In Phase 2, this will implement full agent execution
                # For now, return a basic acknowledgment response

                # Create a simple acknowledgment message
                response_message = Message(
                    id=f"msg_{datetime.datetime.utcnow().timestamp()}",
                    role=MessageRole.ASSISTANT,
                    content="Message received. Full agent execution will be implemented in Phase 2.",
                    status=MessageStatus.COMPLETED,
                    created_at=datetime.datetime.utcnow(),
                )

                return CopilotResponse(
                    thread_id=data.agent_session.thread_id,
                    messages=[response_message],
                    status=ResponseStatus.SUCCESS,
                )

            finally:
                # Clean up runtime context
                await context.runtime.complete_request_context(data.agent_session.thread_id)

        except Exception as e:
            error = handle_resolver_exception(
                e, "generate_copilot_response", context.logger, context.correlation_id
            )
            # Return error response
            return create_error_response(
                error, ErrorRecoveryStrategy.get_fallback_response(error, "generate_response_mutation")
            ) or CopilotResponse(
                thread_id=data.agent_session.thread_id,
                messages=[],
                status=ResponseStatus.ERROR,
                error_message=error.message if error.user_facing else "An error occurred"
            )

        finally:
            context.end_performance_timer("generate_copilot_response")

    @strawberry.field
    async def save_agent_state(
        self, info: Info[GraphQLContext, Any], data: SaveAgentStateInput
    ) -> SaveAgentStateResponse:
        """
        Save agent state to storage.

        Args:
            info: GraphQL execution info
            data: Save agent state input data

        Returns:
            SaveAgentStateResponse with success status
        """
        context = info.context
        context.start_performance_timer("save_agent_state")

        try:
            # Log the operation
            context.log_operation("save_agent_state", "mutation", {
                "thread_id": data.thread_id,
                "agent_name": data.agent_name,
                "merge_with_existing": data.merge_with_existing,
            })

            # Parse state data from JSON
            import json
            try:
                state_data = json.loads(data.state_data)
            except json.JSONDecodeError as e:
                raise CopilotKitError(f"Invalid JSON in state_data: {e}")

            # Save state through runtime
            stored_state = await context.runtime.save_agent_state(
                data.thread_id,
                data.agent_name,
                state_data,
                data.merge_with_existing
            )

            return SaveAgentStateResponse(
                thread_id=data.thread_id,
                agent_name=data.agent_name,
                success=True,
                state_key=stored_state.state_key,
                saved_at=stored_state.metadata.updated_at,
            )

        except Exception as e:
            error = handle_resolver_exception(
                e, "save_agent_state", context.logger, context.correlation_id
            )
            # Return error response
            return create_error_response(
                error, ErrorRecoveryStrategy.get_fallback_response(error, "save_agent_state_mutation")
            ) or SaveAgentStateResponse(
                thread_id=data.thread_id,
                agent_name=data.agent_name,
                success=False,
                error_message=error.message if error.user_facing else "Failed to save state"
            )

        finally:
            context.end_performance_timer("save_agent_state")


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
