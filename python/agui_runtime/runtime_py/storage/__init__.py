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
    from agui_runtime.runtime_py.storage import StorageManager, MemoryStorage

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
from typing import Any

# Import all base interfaces and implementations
from .base import (
    StorageBackend,
    StateStore,
    TransactionalStateStore,
    StoredState,
    StateMetadata,
    StorageError,
    StateNotFoundError,
    StateCorruptionError,
    StorageBackendUnavailableError,
    StateData,
    ThreadId,
    AgentName,
    StateKey,
    validate_thread_id,
    validate_agent_name,
)

from .memory import (
    MemoryStorageBackend,
    MemoryStateStore,
)

from .manager import (
    StateStoreManager,
    StateStoreConfig,
    StateValidator,
    StateStoreMetrics,
    StorageBackendType,
)

__version__ = "0.1.0"

# Storage backend registry for dynamic loading
STORAGE_BACKENDS: dict[str, str] = {
    "memory": "agui_runtime.runtime_py.storage.memory:MemoryStateStore",
    # Future backends will be added here
    # "redis": "agui_runtime.runtime_py.storage.redis:RedisStateStore",
    # "postgresql": "agui_runtime.runtime_py.storage.postgresql:PostgreSQLStateStore",
}


def get_available_backends() -> dict[str, str]:
    """
    Get a dictionary of available storage backend names and their import paths.

    Returns:
        Dictionary mapping backend names to their import paths.
    """
    return STORAGE_BACKENDS.copy()


def create_storage_backend(backend_name: str, **config: Any) -> StateStore:
    """
    Create a state store backend instance by name.

    Args:
        backend_name: Name of the storage backend to create
        **config: Configuration parameters for the backend

    Returns:
        Initialized state store instance

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
        return backend_class(**config)  # type: ignore[no-any-return]
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import storage backend '{backend_name}': {e}") from e


def create_state_store_manager(
    backend_type: str = "memory",
    **config: Any
) -> StateStoreManager:
    """
    Create a state store manager with specified backend.

    Args:
        backend_type: Type of storage backend
        **config: Configuration parameters

    Returns:
        Initialized StateStoreManager instance
    """
    try:
        backend_enum = StorageBackendType(backend_type)
    except ValueError:
        available = [bt.value for bt in StorageBackendType]
        raise ValueError(f"Invalid backend type '{backend_type}'. Available: {available}")

    store_config = StateStoreConfig(backend_type=backend_enum, **config)
    return StateStoreManager(config=store_config)


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
    # Base interfaces and abstract classes
    "StorageBackend",
    "StateStore",
    "TransactionalStateStore",
    "StoredState",
    "StateMetadata",

    # Exception classes
    "StorageError",
    "StateNotFoundError",
    "StateCorruptionError",
    "StorageBackendUnavailableError",

    # Type aliases
    "StateData",
    "ThreadId",
    "AgentName",
    "StateKey",

    # Concrete implementations
    "MemoryStorageBackend",
    "MemoryStateStore",

    # Manager and configuration
    "StateStoreManager",
    "StateStoreConfig",
    "StateValidator",
    "StateStoreMetrics",
    "StorageBackendType",

    # Utility functions
    "get_available_backends",
    "create_storage_backend",
    "create_state_store_manager",
    "serialize_state",
    "deserialize_state",
    "generate_state_key",
    "generate_thread_key",
    "validate_thread_id",
    "validate_agent_name",

    # Backend registry
    "STORAGE_BACKENDS",
]
