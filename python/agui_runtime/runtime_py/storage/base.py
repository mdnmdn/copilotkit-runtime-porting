"""
State store base interfaces and abstract classes for CopilotKit Python Runtime.

This module defines the core interfaces and abstract base classes for the
storage system, providing pluggable state persistence with thread-scoped
and agent-scoped storage capabilities.
"""

from __future__ import annotations

import abc
import datetime
import json
from typing import Any, Dict, List, Optional, Protocol, Union

# Type aliases for better readability
StateData = Dict[str, Any]
ThreadId = str
AgentName = str
StateKey = str


class StorageError(Exception):
    """Base exception for storage-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "STORAGE_ERROR",
        details: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class StateNotFoundError(StorageError):
    """Raised when requested state is not found."""

    def __init__(self, state_key: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            f"State not found for key: {state_key}",
            error_code="STATE_NOT_FOUND",
            details=details or {"state_key": state_key},
        )


class StateCorruptionError(StorageError):
    """Raised when state data is corrupted or invalid."""

    def __init__(self, state_key: str, reason: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            f"State corruption detected for key {state_key}: {reason}",
            error_code="STATE_CORRUPTION",
            details=details or {"state_key": state_key, "reason": reason},
        )


class StorageBackendUnavailableError(StorageError):
    """Raised when storage backend is unavailable."""

    def __init__(self, backend_name: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            f"Storage backend '{backend_name}' is unavailable",
            error_code="STORAGE_BACKEND_UNAVAILABLE",
            details=details or {"backend_name": backend_name},
        )


class StateMetadata:
    """Metadata associated with stored state."""

    def __init__(
        self,
        created_at: datetime.datetime,
        updated_at: datetime.datetime,
        version: int = 1,
        size_bytes: int = 0,
        checksum: str | None = None,
        tags: Dict[str, str] | None = None,
    ) -> None:
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version
        self.size_bytes = size_bytes
        self.checksum = checksum
        self.tags = tags or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateMetadata:
        """Create metadata from dictionary."""
        return cls(
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum"),
            tags=data.get("tags", {}),
        )


class StoredState:
    """Container for state data with metadata."""

    def __init__(
        self,
        state_key: str,
        data: StateData,
        metadata: StateMetadata,
    ) -> None:
        self.state_key = state_key
        self.data = data
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert stored state to dictionary."""
        return {
            "state_key": self.state_key,
            "data": self.data,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StoredState:
        """Create stored state from dictionary."""
        return cls(
            state_key=data["state_key"],
            data=data["data"],
            metadata=StateMetadata.from_dict(data["metadata"]),
        )


class StorageBackend(abc.ABC):
    """
    Abstract base class for storage backends.

    This interface defines the basic operations that any storage backend
    must implement to be compatible with the CopilotKit runtime.
    """

    @abc.abstractmethod
    async def get(self, key: str) -> bytes | None:
        """
        Get raw data by key.

        Args:
            key: Storage key

        Returns:
            Raw data bytes or None if not found

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: bytes, ttl_seconds: int | None = None) -> None:
        """
        Set raw data by key.

        Args:
            key: Storage key
            value: Raw data bytes
            ttl_seconds: Optional time-to-live in seconds

        Raises:
            StorageError: If storage fails
        """
        pass

    @abc.abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data by key.

        Args:
            key: Storage key

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Storage key

        Returns:
            True if key exists, False otherwise

        Raises:
            StorageError: If check fails
        """
        pass

    @abc.abstractmethod
    async def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys with optional prefix filter.

        Args:
            prefix: Optional key prefix filter

        Returns:
            List of matching keys

        Raises:
            StorageError: If listing fails
        """
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """
        Check if storage backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abc.abstractmethod
    async def cleanup(self) -> None:
        """
        Cleanup storage backend resources.

        Raises:
            StorageError: If cleanup fails
        """
        pass


class StateStore(abc.ABC):
    """
    Abstract base class for state stores.

    This interface provides high-level state management operations
    with built-in serialization, metadata handling, and key management.
    """

    def __init__(self, backend: StorageBackend) -> None:
        """
        Initialize state store with backend.

        Args:
            backend: Storage backend implementation
        """
        self.backend = backend

    @abc.abstractmethod
    async def save_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
        state_data: StateData,
        merge_with_existing: bool = True,
        tags: Dict[str, str] | None = None,
    ) -> StoredState:
        """
        Save agent state data.

        Args:
            thread_id: Thread identifier
            agent_name: Agent name
            state_data: State data to save
            merge_with_existing: Whether to merge with existing state
            tags: Optional metadata tags

        Returns:
            Stored state with metadata

        Raises:
            StateStoreError: If save operation fails
        """
        pass

    @abc.abstractmethod
    async def load_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StoredState | None:
        """
        Load agent state data.

        Args:
            thread_id: Thread identifier
            agent_name: Agent name

        Returns:
            Stored state or None if not found

        Raises:
            StateStoreError: If load operation fails
            StateCorruptionError: If state data is corrupted
        """
        pass

    @abc.abstractmethod
    async def delete_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> bool:
        """
        Delete agent state data.

        Args:
            thread_id: Thread identifier
            agent_name: Agent name

        Returns:
            True if state was deleted, False if not found

        Raises:
            StateStoreError: If delete operation fails
        """
        pass

    @abc.abstractmethod
    async def list_thread_agents(self, thread_id: ThreadId) -> List[AgentName]:
        """
        List all agents with state in a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            List of agent names

        Raises:
            StateStoreError: If listing fails
        """
        pass

    @abc.abstractmethod
    async def list_agent_threads(self, agent_name: AgentName) -> List[ThreadId]:
        """
        List all threads where an agent has state.

        Args:
            agent_name: Agent name

        Returns:
            List of thread IDs

        Raises:
            StateStoreError: If listing fails
        """
        pass

    @abc.abstractmethod
    async def clear_thread_state(self, thread_id: ThreadId) -> int:
        """
        Clear all agent state for a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Number of state entries deleted

        Raises:
            StateStoreError: If clear operation fails
        """
        pass

    @abc.abstractmethod
    async def get_state_metadata(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StateMetadata | None:
        """
        Get metadata for agent state without loading data.

        Args:
            thread_id: Thread identifier
            agent_name: Agent name

        Returns:
            State metadata or None if not found

        Raises:
            StateStoreError: If metadata retrieval fails
        """
        pass

    def generate_state_key(self, thread_id: ThreadId, agent_name: AgentName) -> StateKey:
        """
        Generate standardized state key.

        Args:
            thread_id: Thread identifier
            agent_name: Agent name

        Returns:
            Standardized state key
        """
        return f"copilotkit:state:{thread_id}:{agent_name}"

    def generate_thread_key(self, thread_id: ThreadId) -> StateKey:
        """
        Generate standardized thread key.

        Args:
            thread_id: Thread identifier

        Returns:
            Standardized thread key
        """
        return f"copilotkit:thread:{thread_id}"

    def serialize_state(self, state_data: StateData) -> bytes:
        """
        Serialize state data to bytes.

        Args:
            state_data: State data dictionary

        Returns:
            Serialized state data

        Raises:
            StateCorruptionError: If serialization fails
        """
        try:
            json_str = json.dumps(state_data, default=str, ensure_ascii=False)
            return json_str.encode('utf-8')
        except (TypeError, ValueError) as e:
            raise StateCorruptionError(
                "serialization",
                f"Failed to serialize state data: {e}",
                {"error": str(e)}
            ) from e

    def deserialize_state(self, state_bytes: bytes) -> StateData:
        """
        Deserialize state data from bytes.

        Args:
            state_bytes: Serialized state data

        Returns:
            Deserialized state data dictionary

        Raises:
            StateCorruptionError: If deserialization fails
        """
        try:
            json_str = state_bytes.decode('utf-8')
            return json.loads(json_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise StateCorruptionError(
                "deserialization",
                f"Failed to deserialize state data: {e}",
                {"error": str(e)}
            ) from e

    async def health_check(self) -> bool:
        """
        Check if state store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        return await self.backend.health_check()

    async def cleanup(self) -> None:
        """
        Cleanup state store resources.

        Raises:
            StateStoreError: If cleanup fails
        """
        await self.backend.cleanup()


class TransactionalStateStore(StateStore):
    """
    Abstract base class for transactional state stores.

    Provides atomic operations across multiple state changes.
    """

    @abc.abstractmethod
    async def begin_transaction(self) -> str:
        """
        Begin a new transaction.

        Returns:
            Transaction ID
        """
        pass

    @abc.abstractmethod
    async def commit_transaction(self, transaction_id: str) -> None:
        """
        Commit a transaction.

        Args:
            transaction_id: Transaction to commit

        Raises:
            StateStoreError: If commit fails
        """
        pass

    @abc.abstractmethod
    async def rollback_transaction(self, transaction_id: str) -> None:
        """
        Rollback a transaction.

        Args:
            transaction_id: Transaction to rollback

        Raises:
            StateStoreError: If rollback fails
        """
        pass


# Utility functions
def validate_thread_id(thread_id: str) -> bool:
    """
    Validate thread ID format.

    Args:
        thread_id: Thread ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not thread_id or not isinstance(thread_id, str):
        return False

    if len(thread_id) > 255 or len(thread_id) < 1:
        return False

    # Basic format validation - alphanumeric, hyphens, underscores
    import re
    return bool(re.match(r'^[a-zA-Z0-9\-_]+$', thread_id))


def validate_agent_name(agent_name: str) -> bool:
    """
    Validate agent name format.

    Args:
        agent_name: Agent name to validate

    Returns:
        True if valid, False otherwise
    """
    if not agent_name or not isinstance(agent_name, str):
        return False

    if len(agent_name) > 100 or len(agent_name) < 1:
        return False

    # Basic format validation - alphanumeric, hyphens, underscores
    import re
    return bool(re.match(r'^[a-zA-Z0-9\-_]+$', agent_name))


# Export public API
__all__ = [
    # Base classes and interfaces
    "StorageBackend",
    "StateStore",
    "TransactionalStateStore",

    # Data classes
    "StoredState",
    "StateMetadata",

    # Exceptions
    "StorageError",
    "StateNotFoundError",
    "StateCorruptionError",
    "StorageBackendUnavailableError",

    # Type aliases
    "StateData",
    "ThreadId",
    "AgentName",
    "StateKey",

    # Utility functions
    "validate_thread_id",
    "validate_agent_name",
]
