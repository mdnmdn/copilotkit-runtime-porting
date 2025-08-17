"""
CopilotKit Runtime Storage - State persistence backends.

This module provides pluggable storage backends for persisting agent state,
conversation threads, and runtime data across sessions. It supports multiple
storage backends with a unified interface.

Supported Backends:
- Memory: In-memory storage for development and testing
- Redis: Distributed caching and state storage
- PostgreSQL: Persistent relational database storage

Key Components:
- StorageBackend: Abstract interface for storage implementations
- MemoryStorage: In-memory storage backend
- RedisStorage: Redis-based distributed storage
- PostgreSQLStorage: Database-backed persistent storage
- StorageManager: Unified storage management interface
- State serialization and deserialization utilities

Example Usage:
    ```python
    from copilotkit.runtime_py.storage import StorageManager, MemoryStorage

    # Create storage backend
    storage = MemoryStorage()

    # Create storage manager
    manager = StorageManager(storage)

    # Store agent state
    await manager.save_agent_state(thread_id, agent_name, state)

    # Load agent state
    state = await manager.load_agent_state(thread_id, agent_name)
    ```

Configuration:
    Storage backends are configured through RuntimeConfig:
    - state_store_backend: "memory" | "redis" | "postgresql"
    - redis_url: Redis connection string
    - database_url: PostgreSQL connection string
"""

import json
from abc import ABC, abstractmethod
from typing import Any


# Basic StorageBackend interface for type annotations
class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def get(self, key: str) -> Any:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        """Set value by key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        pass


# Import base interfaces (will be implemented in later phases)
# from copilotkit.runtime_py.storage.base import (
#     StorageError,
#     StateNotFoundError,
#     StorageManager,
# )
# from copilotkit.runtime_py.storage.memory import MemoryStorage
# from copilotkit.runtime_py.storage.redis import RedisStorage
# from copilotkit.runtime_py.storage.postgresql import PostgreSQLStorage

__version__ = "0.1.0"

# Storage backend registry for dynamic loading
STORAGE_BACKENDS: dict[str, str] = {
    # Will be populated as backends are implemented
    # "memory": "copilotkit.runtime_py.storage.memory:MemoryStorage",
    # "redis": "copilotkit.runtime_py.storage.redis:RedisStorage",
    # "postgresql": "copilotkit.runtime_py.storage.postgresql:PostgreSQLStorage",
}


def get_available_backends() -> dict[str, str]:
    """
    Get a dictionary of available storage backend names and their import paths.

    Returns:
        Dictionary mapping backend names to their import paths.
    """
    return STORAGE_BACKENDS.copy()


def create_storage_backend(backend_name: str, **config: Any) -> StorageBackend:
    """
    Create a storage backend instance by name.

    Args:
        backend_name: Name of the storage backend to create
        **config: Configuration parameters for the backend

    Returns:
        Initialized storage backend instance

    Raises:
        ValueError: If backend is not available
        ImportError: If backend cannot be imported
    """
    if backend_name not in STORAGE_BACKENDS:
        available = list(STORAGE_BACKENDS.keys())
        raise ValueError(f"Storage backend '{backend_name}' not available. Available: {available}")

    import_path = STORAGE_BACKENDS[backend_name]
    module_path, class_name = import_path.split(":")

    try:
        import importlib

        module = importlib.import_module(module_path)
        backend_class = getattr(module, class_name)
        # Type: ignore since we're dynamically importing and can't verify at static analysis time
        return backend_class(**config)  # type: ignore[no-any-return]
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import storage backend '{backend_name}': {e}") from e


# Storage utility functions
def serialize_state(state_data: dict) -> str:
    """
    Serialize state data for storage.

    Args:
        state_data: Dictionary containing state data

    Returns:
        Serialized state as JSON string
    """
    return json.dumps(state_data, default=str, ensure_ascii=False)


def deserialize_state(state_json: str) -> dict[str, Any]:
    """
    Deserialize state data from storage.

    Args:
        state_json: JSON string containing serialized state

    Returns:
        Deserialized state dictionary

    Raises:
        ValueError: If JSON is invalid
    """
    try:
        return json.loads(state_json)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid state JSON: {e}") from e


def generate_state_key(thread_id: str, agent_name: str) -> str:
    """
    Generate a standardized storage key for agent state.

    Args:
        thread_id: Conversation thread identifier
        agent_name: Name of the agent

    Returns:
        Standardized storage key
    """
    return f"copilotkit:state:{thread_id}:{agent_name}"


def generate_thread_key(thread_id: str) -> str:
    """
    Generate a standardized storage key for thread data.

    Args:
        thread_id: Conversation thread identifier

    Returns:
        Standardized storage key for thread data
    """
    return f"copilotkit:thread:{thread_id}"


# Public API
__all__ = [
    # Base interfaces (will be added as they are implemented)
    # "StorageBackend",
    # "StorageError",
    # "StateNotFoundError",
    # "StorageManager",
    # Storage implementations (will be added as they are implemented)
    # "MemoryStorage",
    # "RedisStorage",
    # "PostgreSQLStorage",
    # Utility functions
    "get_available_backends",
    "create_storage_backend",
    "serialize_state",
    "deserialize_state",
    "generate_state_key",
    "generate_thread_key",
    # Backend registry
    "STORAGE_BACKENDS",
]
