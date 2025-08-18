"""
CopilotKit Runtime GraphQL - GraphQL schema and resolvers.

This module provides the complete GraphQL API implementation for the CopilotKit
Python Runtime, maintaining 100% compatibility with the TypeScript runtime's
GraphQL contract.

Key Components:
- GraphQL schema definition using Strawberry GraphQL
- Query and Mutation resolvers
- Type definitions matching TypeScript schema
- Input and output type mappings
- Schema validation and compatibility checking

The GraphQL API provides:
- availableAgents query for agent discovery
- generateCopilotResponse mutation for agent execution
- Streaming support for real-time message delivery
- Full type safety with Python annotations

Example Usage:
    ```python
    from agui_runtime.runtime_py.graphql import schema
    from strawberry.fastapi import GraphQLRouter

    graphql_app = GraphQLRouter(schema)
    ```
"""

from agui_runtime.runtime_py.graphql.schema import (
    ActionInput,
    ActionInputAvailability,
    ActionMessage,
    # Output types
    Agent,
    AgentSessionInput,
    AgentsResponse,
    AgentStateMessage,
    ContextPropertyInput,
    CopilotRequestType,
    CopilotResponse,
    GenerateCopilotResponseInput,
    # Context types
    GraphQLContext,
    Message,
    # Input types
    MessageInput,
    # GraphQL enums
    MessageRole,
    MessageStatus,
    MessageUnion,
    Mutation,
    # Root types
    Query,
    ResponseStatus,
    RuntimeInfo,
    # Utility functions
    get_schema_sdl,
    # Main schema
    schema,
    validate_schema_compatibility,
)

__version__ = "0.1.0"

# Public API
__all__ = [
    # Main schema
    "schema",
    # Root types
    "Query",
    "Mutation",
    # GraphQL enums
    "MessageRole",
    "MessageStatus",
    "CopilotRequestType",
    "ActionInputAvailability",
    "ResponseStatus",
    # Input types
    "MessageInput",
    "AgentSessionInput",
    "ContextPropertyInput",
    "ActionInput",
    "GenerateCopilotResponseInput",
    # Output types
    "Agent",
    "AgentsResponse",
    "Message",
    "ActionMessage",
    "AgentStateMessage",
    "MessageUnion",
    "CopilotResponse",
    "RuntimeInfo",
    # Context types
    "GraphQLContext",
    # Utility functions
    "get_schema_sdl",
    "validate_schema_compatibility",
]
