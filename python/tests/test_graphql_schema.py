"""
Comprehensive tests for Phase 2 GraphQL schema implementation.

This module tests all GraphQL types, resolvers, context handling, and error
management implemented in Phase 2 of the CopilotKit Python Runtime port.
"""

import datetime
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import strawberry
from strawberry.test import BaseGraphQLTestClient

from agui_runtime.runtime_py.core.runtime import CopilotRuntime
from agui_runtime.runtime_py.core.types import RuntimeConfig, AgentDescriptor
from agui_runtime.runtime_py.graphql.schema import schema
from agui_runtime.runtime_py.graphql.context import GraphQLExecutionContext, create_graphql_context
from agui_runtime.runtime_py.graphql.errors import CopilotKitError, CopilotErrorCode
from agui_runtime.runtime_py.storage import (
    StateStoreManager,
    StateStoreConfig,
    StorageBackendType,
    StoredState,
    StateMetadata,
)


class TestGraphQLTestClient(BaseGraphQLTestClient):
    """Custom GraphQL test client with context support."""

    def __init__(self, schema: Any, context: GraphQLExecutionContext):
        super().__init__(schema)
        self.context = context

    async def query(
        self,
        query: str,
        variables: Dict[str, Any] | None = None,
        context_value: Any = None,
        root_value: Any = None,
    ):
        """Execute GraphQL query with custom context."""
        return await super().query(
            query=query,
            variables=variables,
            context_value=context_value or self.context,
            root_value=root_value,
        )


@pytest.fixture
async def mock_runtime():
    """Create a mock CopilotRuntime for testing."""
    runtime = AsyncMock(spec=CopilotRuntime)

    # Mock agent discovery
    test_agents = [
        AgentDescriptor(
            name="test-agent-1",
            description="Test agent 1",
            version="1.0.0",
            capabilities=["chat", "search"],
        ),
        AgentDescriptor(
            name="test-agent-2",
            description="Test agent 2",
            version="2.0.0",
            capabilities=["analysis"],
        ),
    ]
    runtime.discover_agents.return_value = test_agents
    runtime.list_providers.return_value = ["langgraph", "openai"]

    # Mock state management
    test_state_metadata = StateMetadata(
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
        version=1,
        size_bytes=256,
        checksum="test-checksum",
    )

    test_stored_state = StoredState(
        state_key="test:thread:agent",
        data={"test_key": "test_value", "counter": 42},
        metadata=test_state_metadata,
    )

    runtime.load_agent_state.return_value = test_stored_state
    runtime.save_agent_state.return_value = test_stored_state
    runtime.delete_agent_state.return_value = True
    runtime.clear_thread_state.return_value = 2

    # Mock request context management
    runtime.create_request_context.return_value = MagicMock()
    runtime.complete_request_context.return_value = None

    # Mock state store manager
    mock_state_store = AsyncMock(spec=StateStoreManager)
    runtime._state_store_manager = mock_state_store

    return runtime


@pytest.fixture
async def graphql_context(mock_runtime):
    """Create a GraphQL execution context for testing."""
    return create_graphql_context(
        runtime=mock_runtime,
        user_id="test-user-123",
        session_id="test-session-456",
    )


@pytest.fixture
async def graphql_client(graphql_context):
    """Create a GraphQL test client."""
    return TestGraphQLTestClient(schema, graphql_context)


class TestGraphQLSchema:
    """Test GraphQL schema structure and validation."""

    def test_schema_creation(self):
        """Test that the GraphQL schema can be created successfully."""
        assert schema is not None
        assert hasattr(schema, 'query')
        assert hasattr(schema, 'mutation')

    def test_schema_introspection(self):
        """Test GraphQL schema introspection."""
        from agui_runtime.runtime_py.graphql.schema import get_schema_sdl

        sdl = get_schema_sdl()
        assert sdl is not None
        assert "type Query" in sdl
        assert "type Mutation" in sdl
        assert "availableAgents" in sdl
        assert "generateCopilotResponse" in sdl

    def test_schema_compatibility_validation(self):
        """Test schema compatibility validation."""
        from agui_runtime.runtime_py.graphql.schema import validate_schema_compatibility

        # This should pass for now (placeholder implementation)
        assert validate_schema_compatibility() is True


class TestGraphQLTypes:
    """Test GraphQL type definitions and serialization."""

    def test_message_role_enum(self):
        """Test MessageRole enum values."""
        from agui_runtime.runtime_py.graphql.schema import MessageRole

        expected_values = {"user", "assistant", "system", "tool", "developer"}
        actual_values = {role.value for role in MessageRole}
        assert actual_values == expected_values

    def test_message_status_enum(self):
        """Test MessageStatus enum values."""
        from agui_runtime.runtime_py.graphql.schema import MessageStatus

        expected_values = {"pending", "inProgress", "completed", "failed", "cancelled"}
        actual_values = {status.value for status in MessageStatus}
        assert actual_values == expected_values

    def test_input_types_creation(self):
        """Test that all input types can be created with valid data."""
        from agui_runtime.runtime_py.graphql.schema import (
            LoadAgentStateInput,
            SaveAgentStateInput,
            MetadataInput,
            StreamingConfigInput,
            GenerateCopilotResponseInput,
            MessageInput,
            AgentSessionInput,
        )

        # Test LoadAgentStateInput
        load_input = LoadAgentStateInput(
            thread_id="test-thread-123",
            agent_name="test-agent",
            state_key="test-key",
            include_history=True,
        )
        assert load_input.thread_id == "test-thread-123"
        assert load_input.agent_name == "test-agent"
        assert load_input.include_history is True

        # Test SaveAgentStateInput
        save_input = SaveAgentStateInput(
            thread_id="test-thread-123",
            agent_name="test-agent",
            state_data='{"test": "data"}',
            merge_with_existing=True,
        )
        assert save_input.thread_id == "test-thread-123"
        assert save_input.state_data == '{"test": "data"}'

        # Test StreamingConfigInput
        streaming_input = StreamingConfigInput(
            enabled=True,
            buffer_size=2048,
            flush_interval_ms=50,
        )
        assert streaming_input.enabled is True
        assert streaming_input.buffer_size == 2048

    def test_output_types_creation(self):
        """Test that all output types can be created with valid data."""
        from agui_runtime.runtime_py.graphql.schema import (
            LoadAgentStateResponse,
            SaveAgentStateResponse,
            AgentExecutionResponse,
            MessageStatus,
        )

        now = datetime.datetime.utcnow()

        # Test LoadAgentStateResponse
        load_response = LoadAgentStateResponse(
            thread_id="test-thread-123",
            agent_name="test-agent",
            state_data='{"loaded": true}',
            state_found=True,
            last_updated=now,
        )
        assert load_response.state_found is True
        assert load_response.state_data == '{"loaded": true}'

        # Test SaveAgentStateResponse
        save_response = SaveAgentStateResponse(
            thread_id="test-thread-123",
            agent_name="test-agent",
            success=True,
            saved_at=now,
        )
        assert save_response.success is True
        assert save_response.saved_at == now


class TestGraphQLQueries:
    """Test GraphQL query resolvers."""

    @pytest.mark.asyncio
    async def test_available_agents_query(self, graphql_client, mock_runtime):
        """Test availableAgents query resolver."""
        query = """
        query {
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

        result = await graphql_client.query(query)

        assert result.errors is None
        assert "data" in result.data
        agents_data = result.data["availableAgents"]["agents"]

        assert len(agents_data) == 2
        assert agents_data[0]["name"] == "test-agent-1"
        assert agents_data[0]["capabilities"] == ["chat", "search"]
        assert agents_data[1]["name"] == "test-agent-2"

        # Verify runtime was called
        mock_runtime.discover_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_agent_state_query(self, graphql_client, mock_runtime):
        """Test loadAgentState query resolver."""
        query = """
        query LoadAgentState($data: LoadAgentStateInput!) {
            loadAgentState(data: $data) {
                threadId
                agentName
                stateData
                stateFound
                lastUpdated
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "threadId": "test-thread-123",
                "agentName": "test-agent",
                "includeHistory": False,
            }
        }

        result = await graphql_client.query(query, variables=variables)

        assert result.errors is None
        state_data = result.data["loadAgentState"]

        assert state_data["threadId"] == "test-thread-123"
        assert state_data["agentName"] == "test-agent"
        assert state_data["stateFound"] is True
        assert state_data["errorMessage"] is None

        # Verify runtime was called
        mock_runtime.load_agent_state.assert_called_once_with(
            "test-thread-123", "test-agent"
        )

    @pytest.mark.asyncio
    async def test_load_agent_state_not_found(self, graphql_client, mock_runtime):
        """Test loadAgentState query when state is not found."""
        # Configure mock to return None (state not found)
        mock_runtime.load_agent_state.return_value = None

        query = """
        query LoadAgentState($data: LoadAgentStateInput!) {
            loadAgentState(data: $data) {
                threadId
                agentName
                stateFound
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "threadId": "nonexistent-thread",
                "agentName": "nonexistent-agent",
            }
        }

        result = await graphql_client.query(query, variables=variables)

        assert result.errors is None
        state_data = result.data["loadAgentState"]

        assert state_data["stateFound"] is False
        assert state_data["errorMessage"] is None


class TestGraphQLMutations:
    """Test GraphQL mutation resolvers."""

    @pytest.mark.asyncio
    async def test_generate_copilot_response_mutation(self, graphql_client, mock_runtime):
        """Test generateCopilotResponse mutation resolver."""
        mutation = """
        mutation GenerateResponse($data: GenerateCopilotResponseInput!) {
            generateCopilotResponse(data: $data) {
                threadId
                messages {
                    __typename
                    ... on Message {
                        id
                        role
                        content
                        status
                    }
                }
                status
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "messages": [
                    {
                        "role": "USER",
                        "content": "Hello, test message",
                    }
                ],
                "agentSession": {
                    "threadId": "test-thread-123",
                    "agentName": "test-agent",
                    "userId": "test-user",
                },
                "requestType": "CHAT",
            }
        }

        result = await graphql_client.query(mutation, variables=variables)

        assert result.errors is None
        response_data = result.data["generateCopilotResponse"]

        assert response_data["threadId"] == "test-thread-123"
        assert response_data["status"] == "SUCCESS"
        assert len(response_data["messages"]) == 1
        assert response_data["messages"][0]["role"] == "ASSISTANT"
        assert "Phase 2" in response_data["messages"][0]["content"]

        # Verify runtime context was created and completed
        mock_runtime.create_request_context.assert_called_once()
        mock_runtime.complete_request_context.assert_called_once_with("test-thread-123")

    @pytest.mark.asyncio
    async def test_save_agent_state_mutation(self, graphql_client, mock_runtime):
        """Test saveAgentState mutation resolver."""
        mutation = """
        mutation SaveAgentState($data: SaveAgentStateInput!) {
            saveAgentState(data: $data) {
                threadId
                agentName
                success
                stateKey
                savedAt
                errorMessage
            }
        }
        """

        test_state = {"counter": 10, "status": "active"}
        variables = {
            "data": {
                "threadId": "test-thread-123",
                "agentName": "test-agent",
                "stateData": json.dumps(test_state),
                "mergeWithExisting": True,
            }
        }

        result = await graphql_client.query(mutation, variables=variables)

        assert result.errors is None
        save_data = result.data["saveAgentState"]

        assert save_data["threadId"] == "test-thread-123"
        assert save_data["agentName"] == "test-agent"
        assert save_data["success"] is True
        assert save_data["stateKey"] == "test:thread:agent"
        assert save_data["errorMessage"] is None

        # Verify runtime was called with correct parameters
        mock_runtime.save_agent_state.assert_called_once_with(
            "test-thread-123",
            "test-agent",
            test_state,
            True
        )

    @pytest.mark.asyncio
    async def test_save_agent_state_invalid_json(self, graphql_client, mock_runtime):
        """Test saveAgentState mutation with invalid JSON."""
        mutation = """
        mutation SaveAgentState($data: SaveAgentStateInput!) {
            saveAgentState(data: $data) {
                threadId
                agentName
                success
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "threadId": "test-thread-123",
                "agentName": "test-agent",
                "stateData": "invalid json {",
                "mergeWithExisting": False,
            }
        }

        result = await graphql_client.query(mutation, variables=variables)

        assert result.errors is None
        save_data = result.data["saveAgentState"]

        assert save_data["success"] is False
        assert "Invalid JSON" in save_data["errorMessage"] or "Failed to save state" in save_data["errorMessage"]


class TestGraphQLContext:
    """Test GraphQL execution context functionality."""

    def test_context_creation(self, mock_runtime):
        """Test GraphQL context creation."""
        context = create_graphql_context(
            runtime=mock_runtime,
            user_id="test-user",
            session_id="test-session",
        )

        assert context.runtime == mock_runtime
        assert context.user_id == "test-user"
        assert context.session_id == "test-session"
        assert context.is_authenticated is True
        assert len(context.correlation_id) > 0

    def test_context_operation_logging(self, mock_runtime):
        """Test context operation logging."""
        context = create_graphql_context(runtime=mock_runtime)

        context.log_operation("test_operation", "query", {"test": "data"})

        assert len(context.operations_logged) == 1
        logged_op = context.operations_logged[0]
        assert logged_op["operation_name"] == "test_operation"
        assert logged_op["operation_type"] == "query"
        assert logged_op["details"]["test"] == "data"

    def test_context_performance_timing(self, mock_runtime):
        """Test context performance timing."""
        context = create_graphql_context(runtime=mock_runtime)

        context.start_performance_timer("test_operation")
        duration = context.end_performance_timer("test_operation")

        assert duration >= 0.0
        assert "test_operation_duration" in context.performance_metrics

    def test_context_metadata_management(self, mock_runtime):
        """Test context metadata management."""
        context = create_graphql_context(runtime=mock_runtime)

        context.add_request_metadata("test_key", "test_value")
        value = context.get_request_metadata("test_key")

        assert value == "test_value"
        assert context.get_request_metadata("nonexistent", "default") == "default"

    def test_child_context_creation(self, mock_runtime):
        """Test child context creation."""
        parent_context = create_graphql_context(
            runtime=mock_runtime,
            user_id="test-user",
        )
        parent_context.add_request_metadata("parent_data", "value")

        child_context = parent_context.create_child_context("child_operation")

        assert child_context.runtime == parent_context.runtime
        assert child_context.user_id == parent_context.user_id
        assert child_context.correlation_id.startswith(parent_context.correlation_id)
        assert child_context.get_request_metadata("parent_data") == "value"


class TestGraphQLErrorHandling:
    """Test GraphQL error handling and recovery."""

    @pytest.mark.asyncio
    async def test_available_agents_error_recovery(self, graphql_client, mock_runtime):
        """Test error recovery in availableAgents query."""
        # Configure mock to raise an exception
        mock_runtime.discover_agents.side_effect = Exception("Provider connection failed")

        query = """
        query {
            availableAgents {
                agents {
                    name
                    description
                }
            }
        }
        """

        result = await graphql_client.query(query)

        # Should return empty agents list instead of failing
        assert result.errors is None
        agents_data = result.data["availableAgents"]["agents"]
        assert agents_data == []

    @pytest.mark.asyncio
    async def test_runtime_error_handling(self, graphql_client, mock_runtime):
        """Test runtime error handling in state operations."""
        # Configure mock to raise a state store error
        from agui_runtime.runtime_py.storage.base import StorageError
        mock_runtime.load_agent_state.side_effect = StorageError("State store unavailable")

        query = """
        query LoadAgentState($data: LoadAgentStateInput!) {
            loadAgentState(data: $data) {
                threadId
                agentName
                stateFound
                errorMessage
            }
        }
        """

        variables = {
            "data": {
                "threadId": "test-thread",
                "agentName": "test-agent",
            }
        }

        result = await graphql_client.query(query, variables=variables)

        # Should handle the error gracefully
        assert result.errors is None
        state_data = result.data["loadAgentState"]
        assert state_data["stateFound"] is False
        assert state_data["errorMessage"] is not None

    def test_copilotkit_error_creation(self):
        """Test CopilotKitError creation and serialization."""
        error = CopilotKitError(
            message="Test error message",
            error_code=CopilotErrorCode.AGENT_EXECUTION_FAILED,
            details={"agent": "test-agent"},
            correlation_id="test-correlation",
            recoverable=True,
        )

        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error message"
        assert error_dict["error_code"] == "AGENT_EXECUTION_FAILED"
        assert error_dict["details"]["agent"] == "test-agent"
        assert error_dict["recoverable"] is True

    def test_exception_mapping(self):
        """Test exception mapping to CopilotKitError."""
        from agui_runtime.runtime_py.graphql.errors import map_exception_to_error

        # Test ValueError mapping
        value_error = ValueError("Invalid input value")
        mapped_error = map_exception_to_error(value_error, correlation_id="test-123")

        assert mapped_error.error_code == CopilotErrorCode.INVALID_INPUT
        assert "Invalid input provided" in mapped_error.message
        assert mapped_error.correlation_id == "test-123"

        # Test existing CopilotKitError (should return as-is)
        copilot_error = CopilotKitError("Test error")
        mapped_same = map_exception_to_error(copilot_error)

        assert mapped_same is copilot_error


class TestGraphQLIntegration:
    """Test end-to-end GraphQL integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_agent_workflow(self, graphql_client, mock_runtime):
        """Test a complete agent workflow: save state, generate response, load state."""
        # Step 1: Save initial state
        save_mutation = """
        mutation SaveState($data: SaveAgentStateInput!) {
            saveAgentState(data: $data) {
                success
                stateKey
            }
        }
        """

        initial_state = {"workflow_step": "started", "data": {"user_input": "Hello"}}
        save_variables = {
            "data": {
                "threadId": "workflow-thread",
                "agentName": "workflow-agent",
                "stateData": json.dumps(initial_state),
            }
        }

        save_result = await graphql_client.query(save_mutation, variables=save_variables)
        assert save_result.errors is None
        assert save_result.data["saveAgentState"]["success"] is True

        # Step 2: Generate response
        response_mutation = """
        mutation GenerateResponse($data: GenerateCopilotResponseInput!) {
            generateCopilotResponse(data: $data) {
                threadId
                status
            }
        }
        """

        response_variables = {
            "data": {
                "messages": [{"role": "USER", "content": "Process my request"}],
                "agentSession": {
                    "threadId": "workflow-thread",
                    "agentName": "workflow-agent",
                },
            }
        }

        response_result = await graphql_client.query(
            response_mutation, variables=response_variables
        )
        assert response_result.errors is None
        assert response_result.data["generateCopilotResponse"]["status"] == "SUCCESS"

        # Step 3: Load state (verify it still exists)
        load_query = """
        query LoadState($data: LoadAgentStateInput!) {
            loadAgentState(data: $data) {
                stateFound
                stateData
            }
        }
        """

        load_variables = {
            "data": {
                "threadId": "workflow-thread",
                "agentName": "workflow-agent",
            }
        }

        load_result = await graphql_client.query(load_query, variables=load_variables)
        assert load_result.errors is None
        assert load_result.data["loadAgentState"]["stateFound"] is True

        # Verify all runtime methods were called
        mock_runtime.save_agent_state.assert_called()
        mock_runtime.create_request_context.assert_called()
        mock_runtime.complete_request_context.assert_called()
        mock_runtime.load_agent_state.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, mock_runtime):
        """Test handling of concurrent GraphQL requests."""
        import asyncio

        # Create multiple clients with different contexts
        context1 = create_graphql_context(runtime=mock_runtime, user_id="user1")
        context2 = create_graphql_context(runtime=mock_runtime, user_id="user2")

        client1 = TestGraphQLTestClient(schema, context1)
        client2 = TestGraphQLTestClient(schema, context2)

        # Execute concurrent queries
        query = """
        query {
            availableAgents {
                agents {
                    name
                }
            }
        }
        """

        results = await asyncio.gather(
            client1.query(query),
            client2.query(query),
            return_exceptions=True,
        )

        # Both requests should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert result.errors is None
            assert "availableAgents" in result.data

        # Runtime should have been called twice
        assert mock_runtime.discover_agents.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
