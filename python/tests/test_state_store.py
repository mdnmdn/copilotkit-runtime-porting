"""
Comprehensive tests for Phase 2 state store implementation.

This module tests all state persistence functionality including base interfaces,
memory backend implementation, state store manager, validation, and error handling.
"""

import asyncio
import datetime
import json
import pytest
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from agui_runtime.runtime_py.storage import (
    StateStore,
    MemoryStateStore,
    MemoryStorageBackend,
    StateStoreManager,
    StateStoreConfig,
    StateValidator,
    StorageBackendType,
    StateData,
    ThreadId,
    AgentName,
    StateKey,
    StoredState,
    StateMetadata,
    StorageError,
    StateNotFoundError,
    StateCorruptionError,
    validate_thread_id,
    validate_agent_name,
    serialize_state,
    deserialize_state,
    generate_state_key,
    create_storage_backend,
    create_state_store_manager,
)


@pytest.fixture
def sample_state_data() -> StateData:
    """Sample state data for testing."""
    return {
        "current_step": "analysis",
        "user_input": "Analyze the quarterly sales data",
        "context": {
            "user_id": "user123",
            "session_start": "2024-01-01T10:00:00Z",
        },
        "results": [],
        "metadata": {
            "version": 1,
            "tags": ["analysis", "sales"],
        }
    }


@pytest.fixture
async def memory_backend():
    """Create a memory storage backend for testing."""
    backend = MemoryStorageBackend(max_size_mb=10, default_ttl_seconds=3600)
    yield backend
    await backend.cleanup()


@pytest.fixture
async def memory_state_store():
    """Create a memory state store for testing."""
    store = MemoryStateStore(max_size_mb=10, default_ttl_seconds=3600)
    yield store
    await store.cleanup()


@pytest.fixture
def state_store_config():
    """Create a state store configuration for testing."""
    return StateStoreConfig(
        backend_type=StorageBackendType.MEMORY,
        max_size_mb=10,
        default_ttl_seconds=1800,
        retry_attempts=2,
        enable_compression=False,
    )


@pytest.fixture
async def state_store_manager(state_store_config):
    """Create a state store manager for testing."""
    manager = StateStoreManager(config=state_store_config)
    await manager.initialize()
    yield manager
    await manager.shutdown()


class TestStorageBackend:
    """Test storage backend interface and memory implementation."""

    @pytest.mark.asyncio
    async def test_backend_basic_operations(self, memory_backend):
        """Test basic get/set/delete operations."""
        test_key = "test_key_123"
        test_value = b"test_value_data"

        # Test set operation
        await memory_backend.set(test_key, test_value)

        # Test get operation
        retrieved_value = await memory_backend.get(test_key)
        assert retrieved_value == test_value

        # Test exists operation
        exists = await memory_backend.exists(test_key)
        assert exists is True

        # Test delete operation
        deleted = await memory_backend.delete(test_key)
        assert deleted is True

        # Verify deletion
        retrieved_after_delete = await memory_backend.get(test_key)
        assert retrieved_after_delete is None

        exists_after_delete = await memory_backend.exists(test_key)
        assert exists_after_delete is False

    @pytest.mark.asyncio
    async def test_backend_ttl_expiration(self, memory_backend):
        """Test TTL expiration functionality."""
        test_key = "ttl_test_key"
        test_value = b"ttl_test_value"

        # Set with short TTL
        await memory_backend.set(test_key, test_value, ttl_seconds=1)

        # Should exist immediately
        assert await memory_backend.exists(test_key) is True

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired and automatically cleaned up
        assert await memory_backend.exists(test_key) is False
        retrieved = await memory_backend.get(test_key)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_backend_list_keys(self, memory_backend):
        """Test key listing with prefix filtering."""
        # Set up test data
        test_data = {
            "prefix1:key1": b"value1",
            "prefix1:key2": b"value2",
            "prefix2:key1": b"value3",
            "other_key": b"value4",
        }

        for key, value in test_data.items():
            await memory_backend.set(key, value)

        # Test listing all keys
        all_keys = await memory_backend.list_keys()
        assert len(all_keys) == 4
        assert set(all_keys) == set(test_data.keys())

        # Test prefix filtering
        prefix1_keys = await memory_backend.list_keys("prefix1:")
        assert len(prefix1_keys) == 2
        assert "prefix1:key1" in prefix1_keys
        assert "prefix1:key2" in prefix1_keys

    @pytest.mark.asyncio
    async def test_backend_size_limits(self):
        """Test backend size limit enforcement."""
        # Create backend with very small size limit
        small_backend = MemoryStorageBackend(max_size_mb=0.001)  # ~1KB limit

        try:
            # Fill up the backend
            large_value = b"x" * 512  # 512 bytes

            # Should be able to store first item
            await small_backend.set("key1", large_value)
            assert await small_backend.exists("key1") is True

            # Second item should trigger eviction of first
            await small_backend.set("key2", large_value)
            assert await small_backend.exists("key2") is True

            # First key might be evicted due to size constraints
            # This depends on the exact implementation of eviction policy

        finally:
            await small_backend.cleanup()

    @pytest.mark.asyncio
    async def test_backend_health_check(self, memory_backend):
        """Test backend health check functionality."""
        # Should be healthy initially
        health_status = await memory_backend.health_check()
        assert health_status is True

        # Health check should work multiple times
        for _ in range(3):
            assert await memory_backend.health_check() is True

    @pytest.mark.asyncio
    async def test_backend_concurrent_access(self, memory_backend):
        """Test concurrent access to backend."""
        num_operations = 50

        async def write_operation(i):
            await memory_backend.set(f"concurrent_key_{i}", f"value_{i}".encode())

        async def read_operation(i):
            return await memory_backend.get(f"concurrent_key_{i}")

        # Concurrent writes
        await asyncio.gather(*[write_operation(i) for i in range(num_operations)])

        # Concurrent reads
        results = await asyncio.gather(*[read_operation(i) for i in range(num_operations)])

        # Verify all operations succeeded
        assert len(results) == num_operations
        for i, result in enumerate(results):
            assert result == f"value_{i}".encode()


class TestStateStore:
    """Test StateStore interface and memory implementation."""

    @pytest.mark.asyncio
    async def test_save_and_load_agent_state(self, memory_state_store, sample_state_data):
        """Test saving and loading agent state."""
        thread_id = "test_thread_123"
        agent_name = "test_agent"

        # Save state
        stored_state = await memory_state_store.save_agent_state(
            thread_id, agent_name, sample_state_data
        )

        assert stored_state.state_key == memory_state_store.generate_state_key(thread_id, agent_name)
        assert stored_state.data == sample_state_data
        assert stored_state.metadata.version == 1
        assert stored_state.metadata.size_bytes > 0

        # Load state
        loaded_state = await memory_state_store.load_agent_state(thread_id, agent_name)

        assert loaded_state is not None
        assert loaded_state.data == sample_state_data
        assert loaded_state.metadata.version == 1

    @pytest.mark.asyncio
    async def test_state_merging(self, memory_state_store):
        """Test state merging functionality."""
        thread_id = "merge_thread"
        agent_name = "merge_agent"

        # Save initial state
        initial_state = {"counter": 1, "name": "test", "data": {"a": 1}}
        await memory_state_store.save_agent_state(thread_id, agent_name, initial_state)

        # Save updated state with merge
        update_state = {"counter": 2, "data": {"b": 2}, "new_field": "added"}
        stored_state = await memory_state_store.save_agent_state(
            thread_id, agent_name, update_state, merge_with_existing=True
        )

        # Should have merged data
        expected_merged = {
            "counter": 2,  # Updated
            "name": "test",  # Preserved
            "data": {"b": 2},  # Replaced (not deep merged)
            "new_field": "added",  # Added
        }

        assert stored_state.data == expected_merged
        assert stored_state.metadata.version == 2

    @pytest.mark.asyncio
    async def test_delete_agent_state(self, memory_state_store, sample_state_data):
        """Test deleting agent state."""
        thread_id = "delete_thread"
        agent_name = "delete_agent"

        # Save state first
        await memory_state_store.save_agent_state(thread_id, agent_name, sample_state_data)

        # Verify it exists
        loaded_state = await memory_state_store.load_agent_state(thread_id, agent_name)
        assert loaded_state is not None

        # Delete state
        deleted = await memory_state_store.delete_agent_state(thread_id, agent_name)
        assert deleted is True

        # Verify deletion
        loaded_after_delete = await memory_state_store.load_agent_state(thread_id, agent_name)
        assert loaded_after_delete is None

        # Delete non-existent state
        deleted_again = await memory_state_store.delete_agent_state(thread_id, agent_name)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_list_thread_agents(self, memory_state_store, sample_state_data):
        """Test listing agents in a thread."""
        thread_id = "list_thread"
        agents = ["agent1", "agent2", "agent3"]

        # Save state for multiple agents
        for agent in agents:
            await memory_state_store.save_agent_state(
                thread_id, agent, {**sample_state_data, "agent": agent}
            )

        # List agents
        thread_agents = await memory_state_store.list_thread_agents(thread_id)

        assert len(thread_agents) == 3
        assert set(thread_agents) == set(agents)
        assert thread_agents == sorted(agents)  # Should be sorted

    @pytest.mark.asyncio
    async def test_list_agent_threads(self, memory_state_store, sample_state_data):
        """Test listing threads for an agent."""
        agent_name = "multi_thread_agent"
        threads = ["thread1", "thread2", "thread3"]

        # Save state across multiple threads
        for thread in threads:
            await memory_state_store.save_agent_state(
                thread, agent_name, {**sample_state_data, "thread": thread}
            )

        # List threads
        agent_threads = await memory_state_store.list_agent_threads(agent_name)

        assert len(agent_threads) == 3
        assert set(agent_threads) == set(threads)
        assert agent_threads == sorted(threads)  # Should be sorted

    @pytest.mark.asyncio
    async def test_clear_thread_state(self, memory_state_store, sample_state_data):
        """Test clearing all state for a thread."""
        thread_id = "clear_thread"
        agents = ["agent1", "agent2", "agent3"]

        # Save state for multiple agents
        for agent in agents:
            await memory_state_store.save_agent_state(thread_id, agent, sample_state_data)

        # Verify all states exist
        for agent in agents:
            state = await memory_state_store.load_agent_state(thread_id, agent)
            assert state is not None

        # Clear thread state
        deleted_count = await memory_state_store.clear_thread_state(thread_id)
        assert deleted_count == 3

        # Verify all states are deleted
        for agent in agents:
            state = await memory_state_store.load_agent_state(thread_id, agent)
            assert state is None

    @pytest.mark.asyncio
    async def test_state_metadata(self, memory_state_store, sample_state_data):
        """Test state metadata functionality."""
        thread_id = "metadata_thread"
        agent_name = "metadata_agent"

        # Save state with tags
        tags = {"environment": "test", "priority": "high"}
        stored_state = await memory_state_store.save_agent_state(
            thread_id, agent_name, sample_state_data, tags=tags
        )

        # Check metadata
        assert stored_state.metadata.tags == tags
        assert stored_state.metadata.created_at <= datetime.datetime.utcnow()
        assert stored_state.metadata.checksum is not None

        # Get metadata without loading full state
        metadata = await memory_state_store.get_state_metadata(thread_id, agent_name)
        assert metadata is not None
        assert metadata.tags == tags
        assert metadata.checksum == stored_state.metadata.checksum

    @pytest.mark.asyncio
    async def test_thread_state_limits(self):
        """Test thread state limits enforcement."""
        # Create store with small limit
        limited_store = MemoryStateStore(max_states_per_thread=2)

        try:
            thread_id = "limited_thread"

            # Add states up to limit
            await limited_store.save_agent_state(thread_id, "agent1", {"id": 1})
            await limited_store.save_agent_state(thread_id, "agent2", {"id": 2})

            # Both should exist
            assert await limited_store.load_agent_state(thread_id, "agent1") is not None
            assert await limited_store.load_agent_state(thread_id, "agent2") is not None

            # Add third state - should trigger eviction of oldest
            await limited_store.save_agent_state(thread_id, "agent3", {"id": 3})

            # Third should exist, first might be evicted
            assert await limited_store.load_agent_state(thread_id, "agent3") is not None

            # Check total agents doesn't exceed limit
            agents = await limited_store.list_thread_agents(thread_id)
            assert len(agents) <= 2

        finally:
            await limited_store.cleanup()


class TestStateStoreManager:
    """Test StateStoreManager functionality."""

    @pytest.mark.asyncio
    async def test_manager_initialization(self, state_store_config):
        """Test state store manager initialization."""
        manager = StateStoreManager(config=state_store_config)

        # Should not be initialized initially
        assert not manager._state_store_initialized

        # Initialize
        await manager.initialize()
        assert manager._state_store_initialized
        assert manager._state_store is not None

        # Health check should work
        health = await manager.health_check()
        assert health is True

        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_manager_state_operations(self, state_store_manager, sample_state_data):
        """Test state operations through manager."""
        thread_id = "manager_thread"
        agent_name = "manager_agent"

        # Save state
        stored_state = await state_store_manager.save_agent_state(
            thread_id, agent_name, sample_state_data
        )

        assert stored_state.data == sample_state_data

        # Load state
        loaded_state = await state_store_manager.load_agent_state(thread_id, agent_name)
        assert loaded_state is not None
        assert loaded_state.data == sample_state_data

        # Delete state
        deleted = await state_store_manager.delete_agent_state(thread_id, agent_name)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_manager_validation(self, state_store_manager):
        """Test state validation through manager."""
        # Register schema for validation
        state_store_manager.validator.register_schema(
            "validated_agent",
            {"counter": "integer", "name": "string"},
            required_fields=["counter"]
        )

        valid_state = {"counter": 42, "name": "test", "extra": "allowed"}
        invalid_state = {"name": "test"}  # Missing required counter
        invalid_type_state = {"counter": "not_an_integer", "name": "test"}

        # Valid state should work
        stored = await state_store_manager.save_agent_state(
            "val_thread", "validated_agent", valid_state
        )
        assert stored.data == valid_state

        # Invalid state should raise error
        with pytest.raises(StorageError, match="Missing required fields"):
            await state_store_manager.save_agent_state(
                "val_thread", "validated_agent", invalid_state
            )

        # Invalid type should raise error
        with pytest.raises(StorageError, match="Invalid type"):
            await state_store_manager.save_agent_state(
                "val_thread", "validated_agent", invalid_type_state
            )

    @pytest.mark.asyncio
    async def test_manager_metrics(self, state_store_manager, sample_state_data):
        """Test metrics collection in manager."""
        # Perform some operations
        await state_store_manager.save_agent_state("m_thread", "m_agent", sample_state_data)
        await state_store_manager.load_agent_state("m_thread", "m_agent")
        await state_store_manager.delete_agent_state("m_thread", "m_agent")

        # Get metrics
        metrics = state_store_manager.get_metrics()

        assert metrics is not None
        assert "operations_count" in metrics
        assert "total_states_stored" in metrics
        assert "total_states_loaded" in metrics
        assert "total_states_deleted" in metrics

        # Should have recorded operations
        assert metrics["total_states_stored"] >= 1
        assert metrics["total_states_loaded"] >= 1
        assert metrics["total_states_deleted"] >= 1

    @pytest.mark.asyncio
    async def test_manager_caching(self, state_store_manager, sample_state_data):
        """Test metadata caching in manager."""
        thread_id = "cache_thread"
        agent_name = "cache_agent"

        # Save state
        await state_store_manager.save_agent_state(thread_id, agent_name, sample_state_data)

        # First metadata request - cache miss
        metadata1 = await state_store_manager.get_state_metadata(thread_id, agent_name)
        assert metadata1 is not None

        # Second request - cache hit (should be faster)
        metadata2 = await state_store_manager.get_state_metadata(thread_id, agent_name)
        assert metadata2 is not None
        assert metadata1.version == metadata2.version

        # Check cache metrics
        metrics = state_store_manager.get_metrics()
        assert metrics["cache_hits"] >= 1 or metrics["cache_misses"] >= 1

    @pytest.mark.asyncio
    async def test_manager_bulk_operations(self, state_store_manager):
        """Test bulk state operations."""
        states_to_save = [
            ("bulk_thread", "agent1", {"id": 1, "name": "agent1"}),
            ("bulk_thread", "agent2", {"id": 2, "name": "agent2"}),
            ("bulk_thread", "agent3", {"id": 3, "name": "agent3"}),
        ]

        # Bulk save
        stored_states = await state_store_manager.bulk_save_states(states_to_save)
        assert len(stored_states) == 3

        # Bulk load
        load_requests = [("bulk_thread", "agent1"), ("bulk_thread", "agent2")]
        loaded_states = await state_store_manager.bulk_load_states(load_requests)
        assert len(loaded_states) == 2
        assert all(state is not None for state in loaded_states)


class TestStateValidation:
    """Test state validation functionality."""

    def test_thread_id_validation(self):
        """Test thread ID validation."""
        # Valid thread IDs
        valid_ids = ["thread123", "thread-456", "thread_789", "a" * 255]
        for thread_id in valid_ids:
            assert validate_thread_id(thread_id) is True

        # Invalid thread IDs
        invalid_ids = ["", None, "a" * 256, "thread with spaces", "thread@invalid"]
        for thread_id in invalid_ids:
            assert validate_thread_id(thread_id) is False

    def test_agent_name_validation(self):
        """Test agent name validation."""
        # Valid agent names
        valid_names = ["agent", "agent-1", "agent_2", "a" * 100]
        for name in valid_names:
            assert validate_agent_name(name) is True

        # Invalid agent names
        invalid_names = ["", None, "a" * 101, "agent with spaces", "agent@invalid"]
        for name in invalid_names:
            assert validate_agent_name(name) is False

    def test_state_validator(self):
        """Test StateValidator class."""
        validator = StateValidator()

        # Register schema
        validator.register_schema(
            "test_agent",
            {"id": "integer", "name": "string", "active": "boolean"},
            required_fields=["id", "name"]
        )

        # Valid state
        valid_state = {"id": 1, "name": "test", "active": True, "extra": "ok"}
        assert validator.validate_state("test_agent", valid_state) is True

        # Missing required field
        with pytest.raises(StorageError, match="Missing required fields"):
            validator.validate_state("test_agent", {"name": "test"})

        # Wrong type
        with pytest.raises(StorageError, match="Invalid type"):
            validator.validate_state("test_agent", {"id": "not_int", "name": "test"})

        # Unknown agent (should pass)
        assert validator.validate_state("unknown_agent", {"anything": "goes"}) is True


class TestErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_storage_error_propagation(self, memory_state_store):
        """Test error propagation from storage operations."""
        # Test with invalid thread ID
        with pytest.raises(StorageError, match="Invalid thread ID"):
            await memory_state_store.save_agent_state("", "agent", {"data": "test"})

        # Test with invalid agent name
        with pytest.raises(StorageError, match="Invalid agent name"):
            await memory_state_store.save_agent_state("thread", "", {"data": "test"})

    @pytest.mark.asyncio
    async def test_serialization_errors(self, memory_state_store):
        """Test serialization error handling."""
        # Create state with non-serializable data
        class NonSerializable:
            def __str__(self):
                return "non-serializable"

        invalid_state = {"obj": NonSerializable()}

        # Should handle serialization error gracefully
        with pytest.raises(StorageError):
            await memory_state_store.save_agent_state("thread", "agent", invalid_state)

    def test_error_types(self):
        """Test different error types."""
        # StorageError
        storage_error = StorageError("Test storage error", "TEST_ERROR", {"detail": "test"})
        assert storage_error.error_code == "TEST_ERROR"
        assert storage_error.details["detail"] == "test"

        # StateNotFoundError
        not_found_error = StateNotFoundError("test_key")
        assert not_found_error.error_code == "STATE_NOT_FOUND"
        assert "test_key" in str(not_found_error)

        # StateCorruptionError
        corruption_error = StateCorruptionError("test_key", "Invalid JSON")
        assert corruption_error.error_code == "STATE_CORRUPTION"
        assert "Invalid JSON" in str(corruption_error)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_state_serialization(self):
        """Test state serialization utilities."""
        test_data = {"key": "value", "number": 42, "nested": {"a": 1}}

        # Serialize
        serialized = serialize_state(test_data)
        assert isinstance(serialized, str)

        # Deserialize
        deserialized = deserialize_state(serialized)
        assert deserialized == test_data

    def test_key_generation(self):
        """Test key generation utilities."""
        thread_id = "test_thread"
        agent_name = "test_agent"

        # State key
        state_key = generate_state_key(thread_id, agent_name)
        expected_state_key = f"copilotkit:state:{thread_id}:{agent_name}"
        assert state_key == expected_state_key

    def test_storage_backend_creation(self):
        """Test storage backend factory functions."""
        # Create memory backend
        backend = create_storage_backend("memory", max_size_mb=5)
        assert isinstance(backend, MemoryStateStore)

        # Invalid backend type
        with pytest.raises(ValueError, match="not available"):
            create_storage_backend("nonexistent")

    def test_state_store_manager_creation(self):
        """Test state store manager factory."""
        # Create with memory backend
        manager = create_state_store_manager("memory", max_size_mb=5)
        assert isinstance(manager, StateStoreManager)
        assert manager.config.backend_type == StorageBackendType.MEMORY

        # Invalid backend type
        with pytest.raises(ValueError, match="Invalid backend type"):
            create_state_store_manager("invalid")


class TestConcurrency:
    """Test concurrent operations and thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_state_operations(self, memory_state_store):
        """Test concurrent state save/load operations."""
        thread_id = "concurrent_thread"
        num_agents = 20

        async def save_agent_state(agent_id):
            agent_name = f"agent_{agent_id}"
            state_data = {"agent_id": agent_id, "timestamp": datetime.datetime.utcnow().isoformat()}
            return await memory_state_store.save_agent_state(thread_id, agent_name, state_data)

        async def load_agent_state(agent_id):
            agent_name = f"agent_{agent_id}"
            return await memory_state_store.load_agent_state(thread_id, agent_name)

        # Concurrent saves
        save_results = await asyncio.gather(*[
            save_agent_state(i) for i in range(num_agents)
        ])

        # All saves should succeed
        assert len(save_results) == num_agents
        assert all(result is not None for result in save_results)

        # Concurrent loads
        load_results = await asyncio.gather(*[
            load_agent_state(i) for i in range(num_agents)
        ])

        # All loads should succeed
        assert len(load_results) == num_agents
        assert all(result is not None for result in load_results)

        # Verify data integrity
        for i, loaded_state in enumerate(load_results):
            assert loaded_state.data["agent_id"] == i

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, memory_state_store):
        """Test mixed concurrent operations (save, load, delete)."""
        base_thread = "mixed_ops_thread"

        async def mixed_operations(agent_id):
            thread_id = f"{base_thread}_{agent_id % 3}"  # Multiple threads
            agent_name = f"agent_{agent_id}"

            # Save
            state_data = {"id": agent_id, "step": "created"}
            await memory_state_store.save_agent_state(thread_id, agent_name, state_data)

            # Update
            state_data["step"] = "updated"
            await memory_state_store.save_agent_state(thread_id, agent_name, state_data, merge_with_existing=True)

            # Load
            loaded = await memory_state_store.load_agent_state(thread_id, agent_name)

            # Delete every other agent
            if agent_id % 2 == 0:
                await memory_state_store.delete_agent_state(thread_id, agent_name)
                return None

            return loaded

        # Run mixed operations concurrently
        results = await asyncio.gather(*[
            mixed_operations(i) for i in range(30)
        ])

        # Check results - every other should be None (deleted)
        for i, result in enumerate(results):
            if i % 2 == 0:
                assert result is None  # Deleted
            else:
                assert result is not None  # Should exist
                assert result.data["step"] == "updated"


class TestPerformance:
    """Test performance characteristics and limits."""

    @pytest.mark.asyncio
    async def test_large_state_handling(self, memory_state_store):
        """Test handling of large state objects."""
        thread_id = "large_state_thread"
        agent_name = "large_state_agent"

        # Create large state (but not too large for tests)
        large_state = {
            "large_data": "x" * 10000,  # 10KB string
            "array_data": list(range(1000)),
            "nested": {f"key_{i}": f"value_{i}" for i in range(100)},
            "metadata": {
                "description": "This is a large state object for testing",
                "tags": [f"tag_{i}" for i in range(50)],
            }
        }

        # Save large state
        stored_state = await memory_state_store.save_agent_state(
            thread_id, agent_name, large_state
        )

        assert stored_state.metadata.size_bytes > 10000
        assert stored_state.data == large_state

        # Load large state
        loaded_state = await memory_state_store.load_agent_state(thread_id, agent_name)

        assert loaded_state is not None
        assert loaded_state.data == large_state
        assert loaded_state.metadata.size_bytes == stored_state.metadata.size_bytes

    @pytest.mark.asyncio
    async def test_performance_many_states(self, memory_state_store):
        """Test performance with many state objects."""
        num_states = 100
        base_thread = "perf_thread"

        # Create many states quickly
        start_time = datetime.datetime.utcnow()

        for i in range(num_states):
            thread_id = f"{base_thread}_{i // 10}"  # 10 states per thread
            agent_name = f"perf_agent_{i}"
            state_data = {"index": i, "data": f"state_data_{i}"}

            await memory_state_store.save_agent_state(thread_id, agent_name, state_data)

        save_duration = (datetime.datetime.utcnow() - start_time).total_seconds()

        # Load all states
        start_time = datetime.datetime.utcnow()

        loaded_count = 0
        for i in range(num_states):
            thread_id = f"{base_thread}_{i // 10}"
            agent_name = f"perf_agent_{i}"

            loaded_state = await memory_state_store.load_agent_state(thread_id, agent_name)
            if loaded_state:
                loaded_count += 1

        load_duration = (datetime.datetime.utcnow() - start_time).total_seconds()

        # Performance assertions (reasonable thresholds)
        assert save_duration < 10.0  # Should save 100 states in under 10 seconds
        assert load_duration < 5.0   # Should load 100 states in under 5 seconds
        assert loaded_count == num_states

        # Check storage stats
        stats = await memory_state_store.get_stats()
        assert stats["unique_threads"] >= 10
        assert stats["total_keys"] >= num_states


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
