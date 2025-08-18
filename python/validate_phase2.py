#!/usr/bin/env python3
"""
Phase 2 Validation Script for CopilotKit Python Runtime

This script validates that all Phase 2 requirements have been successfully
implemented, including:

1. Complete GraphQL Type System Implementation
2. GraphQL Context and Error Handling
3. State Store Interface and Implementation
4. State Store Manager
5. Enhanced CopilotRuntime Integration

Usage:
    python validate_phase2.py

Returns:
    Exit code 0 if all validations pass
    Exit code 1 if any validation fails
"""

import asyncio
import datetime
import json
import logging
import sys
import traceback
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class Phase2Validator:
    """Comprehensive Phase 2 validation suite."""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    async def test(self, test_name: str, test_func):
        """Execute a test and track results."""
        logger.info(f"Testing: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()

            logger.info(f"✅ PASSED: {test_name}")
            self.passed_tests += 1
            self.test_results.append({"name": test_name, "status": "PASSED", "error": None})
        except Exception as e:
            logger.error(f"❌ FAILED: {test_name} - {str(e)}")
            self.failed_tests += 1
            self.test_results.append({
                "name": test_name,
                "status": "FAILED",
                "error": str(e),
            })
            return False

    async def validate_all(self) -> bool:
        """Run all Phase 2 validations."""
        logger.info("🚀 Starting Phase 2 Validation Suite")
        logger.info("=" * 60)

        # Task 1: GraphQL Type System Implementation
        await self.validate_graphql_types()

        # Task 2: GraphQL Context and Error Handling
        await self.validate_graphql_context_and_errors()

        # Task 3: State Store Implementation
        await self.validate_state_store()

        # Task 4: Runtime Integration
        await self.validate_runtime_integration()

        # Task 5: End-to-End Integration
        await self.validate_e2e_integration()

        # Summary
        self.print_summary()

        return self.failed_tests == 0

    async def validate_graphql_types(self):
        """Validate GraphQL type system implementation."""
        logger.info("\n📋 Task 1: GraphQL Type System Implementation")

        # Test 1.1: Input Types
        await self.test("GraphQL Input Types Creation", self.test_graphql_input_types)

        # Test 1.2: Output Types
        await self.test("GraphQL Output Types Creation", self.test_graphql_output_types)

        # Test 1.3: Message Union Types
        await self.test("GraphQL Message Union Types", self.test_graphql_message_unions)

        # Test 1.4: Meta-Event Union Types
        await self.test("GraphQL Meta-Event Union Types", self.test_graphql_meta_events)

        # Test 1.5: Schema Generation
        await self.test("GraphQL Schema Generation", self.test_graphql_schema_generation)

    async def validate_graphql_context_and_errors(self):
        """Validate GraphQL context and error handling."""
        logger.info("\n🔧 Task 2: GraphQL Context and Error Handling")

        # Test 2.1: Context Creation
        await self.test("GraphQL Context Creation", self.test_graphql_context_creation)

        # Test 2.2: Error Handling
        await self.test("GraphQL Error Handling", self.test_graphql_error_handling)

        # Test 2.3: Resolver Integration
        await self.test("GraphQL Resolver Integration", self.test_graphql_resolver_integration)

    async def validate_state_store(self):
        """Validate state store implementation."""
        logger.info("\n🗄️ Task 3: State Store Implementation")

        # Test 3.1: Storage Backend
        # Test 3.1: Memory Storage Backend
        await self.test("Memory Storage Backend", self.test_memory_storage_backend)

        # Test 3.2: State Store Operations
        await self.test("State Store Operations", self.test_state_store_operations)

        # Test 3.3: State Store Manager
        await self.test("State Store Manager", self.test_state_store_manager)

        # Test 3.4: Concurrent Operations
        await self.test("Concurrent State Operations", self.test_concurrent_state_operations)

    async def validate_runtime_integration(self):
        """Validate runtime integration."""
        logger.info("\n🎯 Task 4: Runtime Integration")

        # Test 4.1: Runtime State Integration
        await self.test("Runtime State Integration", self.test_runtime_state_integration)

        # Test 4.2: Request Context Management
        await self.test("Runtime Request Context", self.test_runtime_request_context)

        # Test 4.3: Health and Metrics
        await self.test("Runtime Health and Metrics", self.test_runtime_health_metrics)

    async def validate_e2e_integration(self):
        """Validate end-to-end integration."""
        logger.info("\n🔄 Task 5: End-to-End Integration")

        # Test 5.1: Complete GraphQL Operations
        await self.test("End-to-End GraphQL Operations", self.test_e2e_graphql_operations)

        # Test 5.2: State Persistence Workflow
        await self.test("End-to-End State Persistence", self.test_e2e_state_persistence)

    # Test Implementations

    def test_graphql_input_types(self):
        """Test GraphQL input types creation."""
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
        assert load_input.include_history is True

        # Test SaveAgentStateInput
        save_input = SaveAgentStateInput(
            thread_id="test-thread-123",
            agent_name="test-agent",
            state_data='{"test": "data"}',
            merge_with_existing=True,
        )
        assert save_input.state_data == '{"test": "data"}'

        # Test MetadataInput
        metadata_input = MetadataInput(
            user_id="test-user",
            session_id="test-session",
            custom_properties='{"key": "value"}',
        )
        assert metadata_input.user_id == "test-user"

        # Test StreamingConfigInput
        streaming_input = StreamingConfigInput(
            enabled=True,
            buffer_size=2048,
            flush_interval_ms=50,
        )
        assert streaming_input.buffer_size == 2048

    def test_graphql_output_types(self):
        """Test GraphQL output types creation."""
        from agui_runtime.runtime_py.graphql.schema import (
            LoadAgentStateResponse,
            SaveAgentStateResponse,
            AgentExecutionResponse,
            MetaEventResponse,
            MessageStatus,
        )

        now = datetime.datetime.utcnow()

        # Test LoadAgentStateResponse
        load_response = LoadAgentStateResponse(
            thread_id="test-thread",
            agent_name="test-agent",
            state_data='{"loaded": true}',
            state_found=True,
            last_updated=now,
        )
        assert load_response.state_found is True

        # Test SaveAgentStateResponse
        save_response = SaveAgentStateResponse(
            thread_id="test-thread",
            agent_name="test-agent",
            success=True,
            saved_at=now,
        )
        assert save_response.success is True

        # Test AgentExecutionResponse
        exec_response = AgentExecutionResponse(
            execution_id="exec-123",
            thread_id="test-thread",
            agent_name="test-agent",
            status=MessageStatus.COMPLETED,
            started_at=now,
        )
        assert exec_response.status == MessageStatus.COMPLETED

    def test_graphql_message_unions(self):
        """Test GraphQL message union types."""
        from agui_runtime.runtime_py.graphql.schema import (
            Message,
            ActionMessage,
            AgentStateMessage,
            ImageMessage,
            ActionExecutionMessage,
            ResultMessage,
            MessageUnion,
            MessageRole,
            MessageStatus,
        )

        # Test basic Message
        message = Message(
            id="msg-123",
            role=MessageRole.USER,
            content="Hello world",
            status=MessageStatus.COMPLETED,
        )
        assert message.role == MessageRole.USER

        # Test ActionMessage
        action_msg = ActionMessage(
            id="action-123",
            action_name="search",
            status=MessageStatus.PENDING,
        )
        assert action_msg.action_name == "search"

        # Test ImageMessage
        image_msg = ImageMessage(
            id="img-123",
            content="Image description",
            image_url="https://example.com/image.jpg",
            mime_type="image/jpeg",
        )
        assert image_msg.image_url == "https://example.com/image.jpg"

        # Test ActionExecutionMessage
        exec_msg = ActionExecutionMessage(
            id="exec-123",
            action_name="analyze",
            execution_id="exec-456",
            started_at=datetime.datetime.utcnow(),
        )
        assert exec_msg.action_name == "analyze"

        # Test ResultMessage
        result_msg = ResultMessage(
            id="result-123",
            content="Analysis complete",
            result_type="analysis",
            confidence_score=0.95,
        )
        assert result_msg.confidence_score == 0.95

    def test_graphql_meta_events(self):
        """Test GraphQL meta-event union types."""
        from agui_runtime.runtime_py.graphql.schema import (
            LangGraphInterruptEvent,
            CopilotKitLangGraphInterruptEvent,
            MetaEventUnion,
        )

        now = datetime.datetime.utcnow()

        # Test LangGraphInterruptEvent
        interrupt_event = LangGraphInterruptEvent(
            event_id="interrupt-123",
            interrupt_type="user_input",
            node_name="wait_for_input",
            thread_id="thread-123",
            timestamp=now,
        )
        assert interrupt_event.interrupt_type == "user_input"

        # Test CopilotKitLangGraphInterruptEvent
        ck_interrupt = CopilotKitLangGraphInterruptEvent(
            event_id="ck-interrupt-123",
            copilotkit_event_type="action_required",
            langgraph_event=interrupt_event,
            user_interaction_required=True,
            timestamp=now,
        )
        assert ck_interrupt.user_interaction_required is True

    def test_graphql_schema_generation(self):
        """Test GraphQL schema generation."""
        from agui_runtime.runtime_py.graphql.schema import schema, get_schema_sdl

        # Schema should exist
        assert schema is not None
        assert hasattr(schema, 'query')
        assert hasattr(schema, 'mutation')

        # SDL generation should work
        sdl = get_schema_sdl()
        assert sdl is not None
        assert "type Query" in sdl
        assert "type Mutation" in sdl
        assert "availableAgents" in sdl
        assert "generateCopilotResponse" in sdl
        assert "loadAgentState" in sdl
        assert "saveAgentState" in sdl

    def test_graphql_context_creation(self):
        """Test GraphQL context creation."""
        from agui_runtime.runtime_py.graphql.context import (
            GraphQLExecutionContext,
            create_graphql_context,
        )
        from unittest.mock import MagicMock

        mock_runtime = MagicMock()

        # Test context creation
        context = create_graphql_context(
            runtime=mock_runtime,
            user_id="test-user",
            session_id="test-session",
        )

        assert isinstance(context, GraphQLExecutionContext)
        assert context.runtime == mock_runtime
        assert context.user_id == "test-user"
        assert context.session_id == "test-session"
        assert context.is_authenticated is True
        assert len(context.correlation_id) > 0

        # Test operation logging
        context.log_operation("test_op", "query", {"test": "data"})
        assert len(context.operations_logged) == 1

        # Test performance timing
        context.start_performance_timer("test_timer")
        duration = context.end_performance_timer("test_timer")
        assert duration >= 0.0

    def test_graphql_error_handling(self):
        """Test GraphQL error handling."""
        from agui_runtime.runtime_py.graphql.errors import (
            CopilotKitError,
            CopilotErrorCode,
            map_exception_to_error,
            create_graphql_error,
            handle_resolver_exception,
        )
        import logging

        # Test CopilotKitError creation
        error = CopilotKitError(
            message="Test error",
            error_code=CopilotErrorCode.AGENT_EXECUTION_FAILED,
            details={"agent": "test"},
            recoverable=True,
        )

        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "AGENT_EXECUTION_FAILED"
        assert error_dict["recoverable"] is True

        # Test exception mapping
        value_error = ValueError("Invalid input")
        mapped_error = map_exception_to_error(value_error)
        assert mapped_error.error_code == CopilotErrorCode.INVALID_INPUT

        # Test GraphQL error creation
        graphql_error = create_graphql_error(error)
        assert graphql_error["message"] == "Test error"
        assert graphql_error["extensions"]["code"] == "AGENT_EXECUTION_FAILED"

    async def test_graphql_resolver_integration(self):
        """Test GraphQL resolver integration."""
        from agui_runtime.runtime_py.graphql.schema import Query, Mutation
        from agui_runtime.runtime_py.graphql.context import create_graphql_context
        from unittest.mock import AsyncMock

        mock_runtime = AsyncMock()
        mock_runtime.discover_agents.return_value = []
        mock_runtime.load_agent_state.return_value = None

        context = create_graphql_context(runtime=mock_runtime)

        # Test Query resolver
        query = Query()

        # Mock info object
        class MockInfo:
            def __init__(self, context):
                self.context = context

        info = MockInfo(context)

        # Test availableAgents query
        agents_response = await query.available_agents(info)
        assert hasattr(agents_response, 'agents')
        assert mock_runtime.discover_agents.called

    async def test_memory_storage_backend(self):
        """Test memory storage backend."""
        from agui_runtime.runtime_py.storage.memory import MemoryStorageBackend

        backend = MemoryStorageBackend(max_size_mb=1)

        try:
            # Test basic operations
            await backend.set("test_key", b"test_value")
            value = await backend.get("test_key")
            assert value == b"test_value"

            # Test exists
            exists = await backend.exists("test_key")
            assert exists is True

            # Test list keys
            keys = await backend.list_keys()
            assert "test_key" in keys

            # Test delete
            deleted = await backend.delete("test_key")
            assert deleted is True

            # Test health check
            health = await backend.health_check()
            assert health is True

        finally:
            await backend.cleanup()

    async def test_state_store_operations(self):
        """Test state store operations."""
        from agui_runtime.runtime_py.storage.memory import MemoryStateStore

        store = MemoryStateStore(max_size_mb=1)

        try:
            test_state = {"counter": 42, "name": "test"}
            thread_id = "test_thread"
            agent_name = "test_agent"

            # Save state
            stored_state = await store.save_agent_state(thread_id, agent_name, test_state)
            assert stored_state.data == test_state
            assert stored_state.metadata.version == 1

            # Load state
            loaded_state = await store.load_agent_state(thread_id, agent_name)
            assert loaded_state is not None
            assert loaded_state.data == test_state

            # Update state with merge
            update_state = {"counter": 100, "status": "updated"}
            updated_stored = await store.save_agent_state(
                thread_id, agent_name, update_state, merge_with_existing=True
            )
            assert updated_stored.data["counter"] == 100
            assert updated_stored.data["name"] == "test"  # Should be preserved
            assert updated_stored.metadata.version == 2

            # Delete state
            deleted = await store.delete_agent_state(thread_id, agent_name)
            assert deleted is True

            # Verify deletion
            loaded_after_delete = await store.load_agent_state(thread_id, agent_name)
            assert loaded_after_delete is None

        finally:
            await store.cleanup()

    async def test_state_store_manager(self):
        """Test state store manager."""
        from agui_runtime.runtime_py.storage.manager import (
            StateStoreManager,
            StateStoreConfig,
            StorageBackendType,
        )

        config = StateStoreConfig(
            backend_type=StorageBackendType.MEMORY,
            max_size_mb=1,
        )

        manager = StateStoreManager(config=config)

        try:
            await manager.initialize()

            test_state = {"test": "data", "counter": 1}
            thread_id = "manager_thread"
            agent_name = "manager_agent"

            # Save through manager
            stored_state = await manager.save_agent_state(thread_id, agent_name, test_state)
            assert stored_state.data == test_state

            # Load through manager
            loaded_state = await manager.load_agent_state(thread_id, agent_name)
            assert loaded_state is not None
            assert loaded_state.data == test_state

            # Get metrics
            metrics = manager.get_metrics()
            assert metrics is not None
            assert "operations_count" in metrics

        finally:
            await manager.shutdown()

    async def test_concurrent_state_operations(self):
        """Test concurrent state operations."""
        from agui_runtime.runtime_py.storage.memory import MemoryStateStore

        store = MemoryStateStore(max_size_mb=1)

        try:
            async def save_state(agent_id):
                thread_id = f"concurrent_thread_{agent_id % 3}"
                agent_name = f"agent_{agent_id}"
                state_data = {"id": agent_id, "data": f"test_{agent_id}"}
                return await store.save_agent_state(thread_id, agent_name, state_data)

            # Run concurrent operations
            results = await asyncio.gather(*[save_state(i) for i in range(10)])

            # All should succeed
            assert len(results) == 10
            assert all(result is not None for result in results)

            # Verify data integrity
            for i in range(10):
                thread_id = f"concurrent_thread_{i % 3}"
                agent_name = f"agent_{i}"
                loaded_state = await store.load_agent_state(thread_id, agent_name)
                assert loaded_state is not None
                assert loaded_state.data["id"] == i

        finally:
            await store.cleanup()

    async def test_runtime_state_integration(self):
        """Test runtime state integration."""
        from agui_runtime.runtime_py.core.runtime import CopilotRuntime
        from agui_runtime.runtime_py.core.types import RuntimeConfig
        from agui_runtime.runtime_py.storage.manager import StateStoreManager, StateStoreConfig, StorageBackendType

        # Create runtime with state store
        config = RuntimeConfig(state_store_backend="memory")
        runtime = CopilotRuntime(config=config)

        try:
            await runtime.start()

            test_state = {"runtime_test": True, "counter": 42}
            thread_id = "runtime_thread"
            agent_name = "runtime_agent"

            # Save state through runtime
            stored_state = await runtime.save_agent_state(thread_id, agent_name, test_state)
            assert stored_state.data == test_state

            # Load state through runtime
            loaded_state = await runtime.load_agent_state(thread_id, agent_name)
            assert loaded_state is not None
            assert loaded_state.data == test_state

            # Delete state through runtime
            deleted = await runtime.delete_agent_state(thread_id, agent_name)
            assert deleted is True

        finally:
            await runtime.stop()

    async def test_runtime_request_context(self):
        """Test runtime request context management."""
        from agui_runtime.runtime_py.core.runtime import CopilotRuntime
        from agui_runtime.runtime_py.core.types import RuntimeConfig, CopilotRequestType

        config = RuntimeConfig()
        runtime = CopilotRuntime(config=config)

        try:
            await runtime.start()

            # Create request context
            context = await runtime.create_request_context(
                thread_id="ctx_thread",
                user_id="ctx_user",
                request_type=CopilotRequestType.CHAT,
                properties={"test": "data"},
            )

            assert context.thread_id == "ctx_thread"
            assert context.user_id == "ctx_user"
            assert context.request_type == CopilotRequestType.CHAT

            # Get context
            retrieved_context = await runtime.get_request_context("ctx_thread")
            assert retrieved_context is not None
            assert retrieved_context.user_id == "ctx_user"

            # Complete context
            await runtime.complete_request_context("ctx_thread")

            # Should be removed
            completed_context = await runtime.get_request_context("ctx_thread")
            assert completed_context is None

        finally:
            await runtime.stop()

    async def test_runtime_health_metrics(self):
        """Test runtime health and metrics."""
        from agui_runtime.runtime_py.core.runtime import CopilotRuntime
        from agui_runtime.runtime_py.core.types import RuntimeConfig

        config = RuntimeConfig()
        runtime = CopilotRuntime(config=config)

        try:
            await runtime.start()

            # Get metrics
            metrics = await runtime.get_runtime_metrics()
            assert metrics is not None
            assert "providers" in metrics
            assert "agents" in metrics
            assert "requests" in metrics

            # Health check through state store
            if runtime._state_store_manager:
                health = await runtime._state_store_manager.health_check()
                assert health is True

        finally:
            await runtime.stop()

    async def test_e2e_graphql_operations(self):
        """Test end-to-end GraphQL operations."""
        from agui_runtime.runtime_py.graphql.schema import schema
        from agui_runtime.runtime_py.graphql.context import create_graphql_context
        from agui_runtime.runtime_py.core.runtime import CopilotRuntime
        from agui_runtime.runtime_py.core.types import RuntimeConfig
        from unittest.mock import AsyncMock

        # Create mock runtime with basic functionality
        runtime = AsyncMock(spec=CopilotRuntime)
        runtime.discover_agents.return_value = []
        runtime.create_request_context.return_value = AsyncMock()
        runtime.complete_request_context.return_value = None
        runtime._state_store_manager = AsyncMock()

        # Create context
        context = create_graphql_context(runtime=runtime)

        # Test availableAgents query
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

        result = await schema.execute(query, context_value=context)
        assert result.errors is None
        assert result.data is not None
        assert "availableAgents" in result.data
        assert "agents" in result.data["availableAgents"]
        assert isinstance(result.data["availableAgents"]["agents"], list)

        # Test health check query
        health_query = """
        query {
            hello
        }
        """

        health_result = await schema.execute(health_query, context_value=context)
        assert health_result.errors is None
        assert health_result.data is not None
        assert health_result.data["hello"] == "Hello from CopilotKit Python Runtime!"

    async def test_e2e_state_persistence(self):
        """Test end-to-end state persistence workflow."""
        from agui_runtime.runtime_py.core.runtime import CopilotRuntime
        from agui_runtime.runtime_py.core.types import RuntimeConfig

        config = RuntimeConfig(state_store_backend="memory")
        runtime = CopilotRuntime(config=config)

        try:
            await runtime.start()

            # Full workflow: save -> load -> update -> delete
            thread_id = "e2e_thread"
            agent_name = "e2e_agent"

            # Step 1: Save initial state
            initial_state = {"step": 1, "data": "initial"}
            stored1 = await runtime.save_agent_state(thread_id, agent_name, initial_state)
            assert stored1.data == initial_state
            assert stored1.metadata.version == 1

            # Step 2: Load state
            loaded1 = await runtime.load_agent_state(thread_id, agent_name)
            assert loaded1 is not None
            assert loaded1.data == initial_state

            # Step 3: Update with merge
            update_state = {"step": 2, "new_field": "added"}
            stored2 = await runtime.save_agent_state(
                thread_id, agent_name, update_state, merge_with_existing=True
            )
            assert stored2.data["step"] == 2
            assert stored2.data["data"] == "initial"  # Preserved
            assert stored2.data["new_field"] == "added"
            assert stored2.metadata.version == 2

            # Step 4: Load updated state
            loaded2 = await runtime.load_agent_state(thread_id, agent_name)
            assert loaded2 is not None
            assert loaded2.data["step"] == 2
            assert loaded2.metadata.version == 2

            # Step 5: Clear thread state
            cleared_count = await runtime.clear_thread_state(thread_id)
            assert cleared_count == 1

            # Step 6: Verify deletion
            loaded3 = await runtime.load_agent_state(thread_id, agent_name)
            assert loaded3 is None

        finally:
            await runtime.stop()

    def print_summary(self):
        """Print validation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 PHASE 2 VALIDATION SUMMARY")
        logger.info("=" * 60)

        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {self.passed_tests} ✅")
        logger.info(f"Failed: {self.failed_tests} ❌")
        logger.info(f"Success Rate: {success_rate:.1f}%")

        if self.failed_tests > 0:
            logger.error("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    logger.error(f"  - {result['name']}: {result['error']}")

        if self.failed_tests == 0:
            logger.info("\n🎉 ALL PHASE 2 REQUIREMENTS VALIDATED SUCCESSFULLY!")
            logger.info("✅ Phase 2 is ready for production use")
        else:
            logger.error(f"\n⚠️  PHASE 2 VALIDATION INCOMPLETE: {self.failed_tests} failures")
            logger.error("❌ Phase 2 requires fixes before proceeding to Phase 3")


async def main():
    """Main validation entry point."""
    validator = Phase2Validator()

    try:
        success = await validator.validate_all()
        return 0 if success else 1

    except Exception as e:
        logger.error(f"💥 VALIDATION SUITE CRASHED: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
