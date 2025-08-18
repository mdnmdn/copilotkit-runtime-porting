"""
In-memory state store implementation for CopilotKit Python Runtime.

This module provides a thread-safe, in-memory implementation of the StateStore
interface, suitable for development, testing, and single-instance deployments.
Features include automatic cleanup, size limits, and state export/import.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import hashlib
import logging
from typing import Any

from .base import (
    AgentName,
    StateData,
    StateMetadata,
    StateNotFoundError,
    StateStore,
    StorageBackend,
    StorageError,
    StoredState,
    ThreadId,
    validate_agent_name,
    validate_thread_id,
)


class MemoryStorageBackend(StorageBackend):
    """
    In-memory storage backend implementation.

    Provides thread-safe storage operations using asyncio locks
    with optional TTL and size limiting capabilities.
    """

    def __init__(
        self,
        max_size_mb: int = 100,
        default_ttl_seconds: int | None = None,
        cleanup_interval_seconds: int = 60,
    ) -> None:
        """
        Initialize memory storage backend.

        Args:
            max_size_mb: Maximum memory usage in megabytes
            default_ttl_seconds: Default TTL for stored items
            cleanup_interval_seconds: Interval for cleanup operations
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Storage containers
        self._storage: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._access_times: dict[str, datetime.datetime] = {}

        # Thread safety
        self._lock = asyncio.Lock()

        # Statistics
        self._total_size_bytes = 0
        self._access_count = 0
        self._eviction_count = 0

        # Cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown = False

        # Logger
        self.logger = logging.getLogger(f"{__name__}.MemoryStorageBackend")

        self.logger.info(
            f"Initialized memory storage backend: "
            f"max_size={max_size_mb}MB, "
            f"default_ttl={default_ttl_seconds}s"
        )

    async def get(self, key: str) -> bytes | None:
        """Get raw data by key."""
        async with self._lock:
            # Check if key exists
            if key not in self._storage:
                return None

            # Check TTL
            metadata = self._metadata.get(key, {})
            expires_at = metadata.get("expires_at")
            if expires_at and datetime.datetime.utcnow() > expires_at:
                # Expired - remove it
                await self._remove_key_unsafe(key)
                return None

            # Update access time
            self._access_times[key] = datetime.datetime.utcnow()
            self._access_count += 1

            return self._storage[key]

    async def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None:
        """Set raw data by key."""
        async with self._lock:
            # Calculate expiration
            expires_at = None
            effective_ttl = ttl_seconds or self.default_ttl_seconds
            if effective_ttl:
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=effective_ttl)

            # Check if we need to make space
            value_size = len(value)
            await self._ensure_space_unsafe(value_size, exclude_key=key)

            # Store the data
            old_size = len(self._storage.get(key, b""))
            self._storage[key] = value
            self._metadata[key] = {
                "created_at": datetime.datetime.utcnow(),
                "expires_at": expires_at,
                "size": value_size,
            }
            self._access_times[key] = datetime.datetime.utcnow()

            # Update total size
            self._total_size_bytes += value_size - old_size

            self.logger.debug(f"Stored {value_size} bytes for key: {key}")

    async def delete(self, key: str) -> bool:
        """Delete data by key."""
        async with self._lock:
            if key in self._storage:
                await self._remove_key_unsafe(key)
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        async with self._lock:
            if key not in self._storage:
                return False

            # Check TTL
            metadata = self._metadata.get(key, {})
            expires_at = metadata.get("expires_at")
            if expires_at and datetime.datetime.utcnow() > expires_at:
                await self._remove_key_unsafe(key)
                return False

            return True

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with optional prefix filter."""
        async with self._lock:
            # Clean up expired keys first
            await self._cleanup_expired_unsafe()

            # Filter by prefix
            if prefix:
                return [key for key in self._storage if key.startswith(prefix)]
            else:
                return list(self._storage.keys())

    async def health_check(self) -> bool:
        """Check if storage backend is healthy."""
        try:
            # Simple health check - try to store and retrieve a test value
            test_key = "__health_check__"
            test_value = b"health_check_test"

            await self.set(test_key, test_value)
            retrieved = await self.get(test_key)
            await self.delete(test_key)

            return retrieved == test_value
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup storage backend resources."""
        self._shutdown = True

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Clear all data
        async with self._lock:
            self._storage.clear()
            self._metadata.clear()
            self._access_times.clear()
            self._total_size_bytes = 0

        self.logger.info("Memory storage backend cleaned up")

    async def _remove_key_unsafe(self, key: str) -> None:
        """Remove key without acquiring lock (unsafe - lock must be held)."""
        if key in self._storage:
            size = len(self._storage[key])
            del self._storage[key]
            self._total_size_bytes -= size

        self._metadata.pop(key, None)
        self._access_times.pop(key, None)

    async def _ensure_space_unsafe(self, required_bytes: int, exclude_key: str = "") -> None:
        """Ensure there's enough space, evicting items if necessary."""
        # First, clean up expired items
        await self._cleanup_expired_unsafe()

        # Check if we have enough space
        current_usage = self._total_size_bytes
        if exclude_key and exclude_key in self._storage:
            current_usage -= len(self._storage[exclude_key])

        if current_usage + required_bytes <= self.max_size_bytes:
            return

        # Need to evict items - use LRU strategy
        space_needed = (current_usage + required_bytes) - self.max_size_bytes

        # Sort keys by access time (oldest first)
        keys_by_access = sorted(self._access_times.items(), key=lambda x: x[1])

        evicted_bytes = 0
        for key, _ in keys_by_access:
            if key == exclude_key:
                continue

            if key in self._storage:
                size = len(self._storage[key])
                await self._remove_key_unsafe(key)
                evicted_bytes += size
                self._eviction_count += 1

                self.logger.debug(f"Evicted key: {key} ({size} bytes)")

                if evicted_bytes >= space_needed:
                    break

    async def _cleanup_expired_unsafe(self) -> None:
        """Clean up expired keys without acquiring lock."""
        now = datetime.datetime.utcnow()
        expired_keys = []

        for key, metadata in self._metadata.items():
            expires_at = metadata.get("expires_at")
            if expires_at and now > expires_at:
                expired_keys.append(key)

        for key in expired_keys:
            await self._remove_key_unsafe(key)

        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired keys")

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return {
            "total_keys": len(self._storage),
            "total_size_bytes": self._total_size_bytes,
            "max_size_bytes": self.max_size_bytes,
            "usage_percentage": (self._total_size_bytes / self.max_size_bytes) * 100,
            "access_count": self._access_count,
            "eviction_count": self._eviction_count,
        }

    async def export_data(self) -> dict[str, Any]:
        """Export all data for backup/testing."""
        async with self._lock:
            return {
                "storage": {k: v.hex() for k, v in self._storage.items()},
                "metadata": self._metadata.copy(),
                "access_times": {k: v.isoformat() for k, v in self._access_times.items()},
                "stats": self.get_stats(),
            }

    async def import_data(self, data: dict[str, Any]) -> None:
        """Import data from backup/testing."""
        async with self._lock:
            self._storage.clear()
            self._metadata.clear()
            self._access_times.clear()

            # Import storage data
            for k, v in data.get("storage", {}).items():
                self._storage[k] = bytes.fromhex(v)

            # Import metadata
            self._metadata.update(data.get("metadata", {}))

            # Import access times
            for k, v in data.get("access_times", {}).items():
                self._access_times[k] = datetime.datetime.fromisoformat(v)

            # Recalculate total size
            self._total_size_bytes = sum(len(v) for v in self._storage.values())


class MemoryStateStore(StateStore):
    """
    In-memory state store implementation.

    Provides thread-safe agent state storage with automatic cleanup,
    size limits, and comprehensive state management capabilities.
    """

    def __init__(
        self,
        max_size_mb: int = 100,
        default_ttl_seconds: int | None = 3600,  # 1 hour default
        cleanup_interval_seconds: int = 300,  # 5 minutes
        max_states_per_thread: int = 50,
    ) -> None:
        """
        Initialize memory state store.

        Args:
            max_size_mb: Maximum memory usage in megabytes
            default_ttl_seconds: Default TTL for stored states
            cleanup_interval_seconds: Interval for cleanup operations
            max_states_per_thread: Maximum states per thread
        """
        # Create backend
        backend = MemoryStorageBackend(
            max_size_mb=max_size_mb,
            default_ttl_seconds=default_ttl_seconds,
            cleanup_interval_seconds=cleanup_interval_seconds,
        )

        super().__init__(backend)

        self.max_states_per_thread = max_states_per_thread
        self.logger = logging.getLogger(f"{__name__}.MemoryStateStore")

        # Start cleanup task
        self._start_cleanup_task()

        self.logger.info("Memory state store initialized")

    async def save_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
        state_data: StateData,
        merge_with_existing: bool = True,
        tags: dict[str, str] | None = None,
    ) -> StoredState:
        """Save agent state data."""
        # Validate inputs
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        if not validate_agent_name(agent_name):
            raise StorageError(f"Invalid agent name: {agent_name}")

        if not isinstance(state_data, dict):
            raise StorageError("State data must be a dictionary")

        try:
            # Generate state key
            state_key = self.generate_state_key(thread_id, agent_name)

            # Merge with existing state if requested
            final_state_data = state_data.copy()
            existing_state = None

            if merge_with_existing:
                try:
                    existing_state = await self.load_agent_state(thread_id, agent_name)
                    if existing_state:
                        # Deep merge the states
                        merged_data = existing_state.data.copy()
                        merged_data.update(final_state_data)
                        final_state_data = merged_data
                except StateNotFoundError:
                    # No existing state to merge - that's fine
                    pass

            # Create metadata
            now = datetime.datetime.utcnow()
            metadata = StateMetadata(
                created_at=existing_state.metadata.created_at if existing_state else now,
                updated_at=now,
                version=existing_state.metadata.version + 1 if existing_state else 1,
                tags=tags or {},
            )

            # Serialize state
            state_bytes = self.serialize_state(final_state_data)
            metadata.size_bytes = len(state_bytes)

            # Calculate checksum
            metadata.checksum = hashlib.sha256(state_bytes).hexdigest()

            # Check thread state limits
            await self._enforce_thread_limits(thread_id, exclude_agent=agent_name)

            # Create stored state container
            stored_state_data = {
                "data": final_state_data,
                "metadata": metadata.to_dict(),
            }

            # Store the complete state container
            container_bytes = self.serialize_state(stored_state_data)
            await self.backend.set(state_key, container_bytes)

            # Create result
            stored_state = StoredState(state_key, final_state_data, metadata)

            self.logger.info(
                f"Saved state for agent '{agent_name}' in thread '{thread_id}' "
                f"({metadata.size_bytes} bytes, version {metadata.version})"
            )

            return stored_state

        except Exception as e:
            self.logger.error(
                f"Failed to save state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise StorageError(f"Failed to save agent state: {e}") from e

    async def load_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StoredState | None:
        """Load agent state data."""
        # Validate inputs
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        if not validate_agent_name(agent_name):
            raise StorageError(f"Invalid agent name: {agent_name}")

        try:
            # Generate state key
            state_key = self.generate_state_key(thread_id, agent_name)

            # Load raw data
            raw_data = await self.backend.get(state_key)
            if raw_data is None:
                return None

            # Deserialize container
            container_data = self.deserialize_state(raw_data)

            # Extract components
            state_data = container_data["data"]
            metadata_dict = container_data["metadata"]
            metadata = StateMetadata.from_dict(metadata_dict)

            # Create stored state
            stored_state = StoredState(state_key, state_data, metadata)

            self.logger.debug(
                f"Loaded state for agent '{agent_name}' in thread '{thread_id}' "
                f"({metadata.size_bytes} bytes, version {metadata.version})"
            )

            return stored_state

        except Exception as e:
            self.logger.error(
                f"Failed to load state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise StorageError(f"Failed to load agent state: {e}") from e

    async def delete_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> bool:
        """Delete agent state data."""
        # Validate inputs
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        if not validate_agent_name(agent_name):
            raise StorageError(f"Invalid agent name: {agent_name}")

        try:
            # Generate state key
            state_key = self.generate_state_key(thread_id, agent_name)

            # Delete from backend
            deleted = await self.backend.delete(state_key)

            if deleted:
                self.logger.info(f"Deleted state for agent '{agent_name}' in thread '{thread_id}'")

            return deleted

        except Exception as e:
            self.logger.error(
                f"Failed to delete state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise StorageError(f"Failed to delete agent state: {e}") from e

    async def list_thread_agents(self, thread_id: ThreadId) -> list[AgentName]:
        """List all agents with state in a thread."""
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        try:
            # Get thread prefix
            thread_prefix = f"copilotkit:state:{thread_id}:"

            # List all keys with thread prefix
            keys = await self.backend.list_keys(thread_prefix)

            # Extract agent names
            agents = []
            for key in keys:
                if key.startswith(thread_prefix):
                    agent_name = key[len(thread_prefix) :]
                    if validate_agent_name(agent_name):
                        agents.append(agent_name)

            return sorted(agents)

        except Exception as e:
            self.logger.error(f"Failed to list agents for thread '{thread_id}': {e}")
            raise StorageError(f"Failed to list thread agents: {e}") from e

    async def list_agent_threads(self, agent_name: AgentName) -> list[ThreadId]:
        """List all threads where an agent has state."""
        if not validate_agent_name(agent_name):
            raise StorageError(f"Invalid agent name: {agent_name}")

        try:
            # Get all state keys
            keys = await self.backend.list_keys("copilotkit:state:")

            # Extract thread IDs for this agent
            threads = []
            agent_suffix = f":{agent_name}"

            for key in keys:
                if key.endswith(agent_suffix) and key.startswith("copilotkit:state:"):
                    # Extract thread ID: copilotkit:state:{thread_id}:{agent_name}
                    prefix_len = len("copilotkit:state:")
                    suffix_len = len(agent_suffix)
                    thread_id = key[prefix_len:-suffix_len]

                    if validate_thread_id(thread_id):
                        threads.append(thread_id)

            return sorted(threads)

        except Exception as e:
            self.logger.error(f"Failed to list threads for agent '{agent_name}': {e}")
            raise StorageError(f"Failed to list agent threads: {e}") from e

    async def clear_thread_state(self, thread_id: ThreadId) -> int:
        """Clear all agent state for a thread."""
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        try:
            # Get all agents in thread
            agents = await self.list_thread_agents(thread_id)

            # Delete each agent's state
            deleted_count = 0
            for agent_name in agents:
                if await self.delete_agent_state(thread_id, agent_name):
                    deleted_count += 1

            self.logger.info(f"Cleared {deleted_count} agent states from thread '{thread_id}'")

            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to clear state for thread '{thread_id}': {e}")
            raise StorageError(f"Failed to clear thread state: {e}") from e

    async def get_state_metadata(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StateMetadata | None:
        """Get metadata for agent state without loading data."""
        if not validate_thread_id(thread_id):
            raise StorageError(f"Invalid thread ID: {thread_id}")

        if not validate_agent_name(agent_name):
            raise StorageError(f"Invalid agent name: {agent_name}")

        try:
            # Load the full state (we need to deserialize to get metadata)
            stored_state = await self.load_agent_state(thread_id, agent_name)
            return stored_state.metadata if stored_state else None

        except Exception as e:
            self.logger.error(
                f"Failed to get metadata for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise StorageError(f"Failed to get state metadata: {e}") from e

    async def _enforce_thread_limits(self, thread_id: ThreadId, exclude_agent: str = "") -> None:
        """Enforce maximum states per thread limit."""
        agents = await self.list_thread_agents(thread_id)

        # Filter out the agent we're about to save/update
        if exclude_agent:
            agents = [a for a in agents if a != exclude_agent]

        if len(agents) >= self.max_states_per_thread:
            # Need to remove oldest states
            states_to_remove = len(agents) - self.max_states_per_thread + 1

            # Load metadata for all agents to find oldest
            agent_metadata = []
            for agent_name in agents:
                metadata = await self.get_state_metadata(thread_id, agent_name)
                if metadata:
                    agent_metadata.append((agent_name, metadata.updated_at))

            # Sort by update time (oldest first)
            agent_metadata.sort(key=lambda x: x[1])

            # Remove oldest states
            for i in range(min(states_to_remove, len(agent_metadata))):
                agent_name, _ = agent_metadata[i]
                await self.delete_agent_state(thread_id, agent_name)
                self.logger.info(
                    f"Evicted old state for agent '{agent_name}' in thread '{thread_id}' "
                    f"(thread limit: {self.max_states_per_thread})"
                )

    def _start_cleanup_task(self) -> None:
        """Start the periodic cleanup task."""

        async def cleanup_loop():
            while not getattr(self.backend, "_shutdown", False):
                try:
                    await asyncio.sleep(self.backend.cleanup_interval_seconds)
                    # The cleanup happens automatically in the backend
                    self.logger.debug("Periodic cleanup completed")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in cleanup task: {e}")

        self.backend._cleanup_task = asyncio.create_task(cleanup_loop())

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive state store statistics."""
        backend_stats = self.backend.get_stats()

        # Count threads and agents
        all_keys = await self.backend.list_keys("copilotkit:state:")
        threads = set()
        agents = set()

        for key in all_keys:
            if key.startswith("copilotkit:state:"):
                parts = key.split(":")
                if len(parts) >= 4:
                    thread_id = parts[2]
                    agent_name = parts[3]
                    threads.add(thread_id)
                    agents.add(agent_name)

        return {
            **backend_stats,
            "unique_threads": len(threads),
            "unique_agents": len(agents),
            "max_states_per_thread": self.max_states_per_thread,
        }

    async def export_states(self) -> dict[str, Any]:
        """Export all states for backup/testing."""
        return await self.backend.export_data()

    async def import_states(self, data: dict[str, Any]) -> None:
        """Import states from backup/testing."""
        await self.backend.import_data(data)
