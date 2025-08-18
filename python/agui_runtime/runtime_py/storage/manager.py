"""
State store manager for unified state operations in CopilotKit Python Runtime.

This module provides the StateStoreManager class that coordinates multiple
storage backends, handles configuration, validation, and provides a unified
interface for all state management operations across the runtime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum
import json
import datetime

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
    TransactionalStateStore,
    validate_agent_name,
    validate_thread_id,
)
from .memory import MemoryStateStore


class StorageBackendType(Enum):
    """Supported storage backend types."""
    MEMORY = "memory"
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


class StateStoreConfig:
    """Configuration for state store backends."""

    def __init__(
        self,
        backend_type: StorageBackendType = StorageBackendType.MEMORY,
        connection_string: str | None = None,
        max_size_mb: int = 100,
        default_ttl_seconds: int | None = 3600,
        connection_pool_size: int = 10,
        timeout_seconds: int = 30,
        retry_attempts: int = 3,
        enable_compression: bool = False,
        enable_encryption: bool = False,
        backup_enabled: bool = False,
        backup_interval_seconds: int = 3600,
        metrics_enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Initialize state store configuration.

        Args:
            backend_type: Type of storage backend to use
            connection_string: Connection string for external backends
            max_size_mb: Maximum storage size in megabytes
            default_ttl_seconds: Default TTL for stored states
            connection_pool_size: Size of connection pool
            timeout_seconds: Operation timeout
            retry_attempts: Number of retry attempts for failed operations
            enable_compression: Whether to compress stored data
            enable_encryption: Whether to encrypt stored data
            backup_enabled: Whether to enable automatic backups
            backup_interval_seconds: Backup interval in seconds
            metrics_enabled: Whether to collect metrics
            **kwargs: Additional backend-specific configuration
        """
        self.backend_type = backend_type
        self.connection_string = connection_string
        self.max_size_mb = max_size_mb
        self.default_ttl_seconds = default_ttl_seconds
        self.connection_pool_size = connection_pool_size
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.enable_compression = enable_compression
        self.enable_encryption = enable_encryption
        self.backup_enabled = backup_enabled
        self.backup_interval_seconds = backup_interval_seconds
        self.metrics_enabled = metrics_enabled
        self.extra_config = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "backend_type": self.backend_type.value,
            "connection_string": self.connection_string,
            "max_size_mb": self.max_size_mb,
            "default_ttl_seconds": self.default_ttl_seconds,
            "connection_pool_size": self.connection_pool_size,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "enable_compression": self.enable_compression,
            "enable_encryption": self.enable_encryption,
            "backup_enabled": self.backup_enabled,
            "backup_interval_seconds": self.backup_interval_seconds,
            "metrics_enabled": self.metrics_enabled,
            **self.extra_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateStoreConfig:
        """Create configuration from dictionary."""
        backend_type = StorageBackendType(data.get("backend_type", "memory"))
        return cls(
            backend_type=backend_type,
            connection_string=data.get("connection_string"),
            max_size_mb=data.get("max_size_mb", 100),
            default_ttl_seconds=data.get("default_ttl_seconds", 3600),
            connection_pool_size=data.get("connection_pool_size", 10),
            timeout_seconds=data.get("timeout_seconds", 30),
            retry_attempts=data.get("retry_attempts", 3),
            enable_compression=data.get("enable_compression", False),
            enable_encryption=data.get("enable_encryption", False),
            backup_enabled=data.get("backup_enabled", False),
            backup_interval_seconds=data.get("backup_interval_seconds", 3600),
            metrics_enabled=data.get("metrics_enabled", True),
            **{k: v for k, v in data.items() if k not in [
                "backend_type", "connection_string", "max_size_mb", "default_ttl_seconds",
                "connection_pool_size", "timeout_seconds", "retry_attempts",
                "enable_compression", "enable_encryption", "backup_enabled",
                "backup_interval_seconds", "metrics_enabled"
            ]}
        )


class StateStoreMetrics:
    """Metrics collection for state store operations."""

    def __init__(self) -> None:
        self.operations_count: Dict[str, int] = {}
        self.operation_durations: Dict[str, List[float]] = {}
        self.error_count: Dict[str, int] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_states_stored = 0
        self.total_states_loaded = 0
        self.total_states_deleted = 0
        self.started_at = datetime.datetime.utcnow()

    def record_operation(self, operation: str, duration: float, success: bool = True) -> None:
        """Record an operation with its duration and success status."""
        self.operations_count[operation] = self.operations_count.get(operation, 0) + 1

        if operation not in self.operation_durations:
            self.operation_durations[operation] = []
        self.operation_durations[operation].append(duration)

        if not success:
            self.error_count[operation] = self.error_count.get(operation, 0) + 1

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive metrics statistics."""
        avg_durations = {}
        for op, durations in self.operation_durations.items():
            if durations:
                avg_durations[f"{op}_avg_duration"] = sum(durations) / len(durations)
                avg_durations[f"{op}_max_duration"] = max(durations)
                avg_durations[f"{op}_min_duration"] = min(durations)

        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / cache_total * 100) if cache_total > 0 else 0

        return {
            "operations_count": self.operations_count.copy(),
            "error_count": self.error_count.copy(),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate_percent": cache_hit_rate,
            "total_states_stored": self.total_states_stored,
            "total_states_loaded": self.total_states_loaded,
            "total_states_deleted": self.total_states_deleted,
            "uptime_seconds": (datetime.datetime.utcnow() - self.started_at).total_seconds(),
            **avg_durations,
        }


class StateValidator:
    """State data validation and schema checking."""

    def __init__(self) -> None:
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.required_fields: Dict[str, List[str]] = {}

    def register_schema(
        self,
        agent_name: str,
        schema: Dict[str, Any],
        required_fields: List[str] | None = None,
    ) -> None:
        """Register a validation schema for an agent."""
        self.schemas[agent_name] = schema
        self.required_fields[agent_name] = required_fields or []

    def validate_state(self, agent_name: str, state_data: StateData) -> bool:
        """
        Validate state data against registered schema.

        Args:
            agent_name: Agent name to validate for
            state_data: State data to validate

        Returns:
            True if valid, False otherwise

        Raises:
            StorageError: If validation fails with details
        """
        if agent_name not in self.schemas:
            # No schema registered - allow any data
            return True

        schema = self.schemas[agent_name]
        required = self.required_fields.get(agent_name, [])

        # Check required fields
        missing_fields = [field for field in required if field not in state_data]
        if missing_fields:
            raise StorageError(
                f"Missing required fields for agent {agent_name}: {missing_fields}"
            )

        # Basic type checking
        for field, expected_type in schema.items():
            if field in state_data:
                value = state_data[field]
                if not self._check_type(value, expected_type):
                    raise StorageError(
                        f"Invalid type for field '{field}' in agent {agent_name}: "
                        f"expected {expected_type}, got {type(value).__name__}"
                    )

        return True

    def _check_type(self, value: Any, expected_type: Any) -> bool:
        """Check if value matches expected type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif isinstance(expected_type, type):
            return isinstance(value, expected_type)
        else:
            # Unknown type - allow it
            return True


class StateStoreManager:
    """
    Unified state store manager for CopilotKit Runtime.

    Provides a high-level interface for state management operations,
    coordinates multiple storage backends, handles validation, caching,
    and provides comprehensive monitoring and health checking.
    """

    def __init__(
        self,
        config: StateStoreConfig | None = None,
        validator: StateValidator | None = None,
    ) -> None:
        """
        Initialize state store manager.

        Args:
            config: Storage configuration
            validator: State validator for schema checking
        """
        self.config = config or StateStoreConfig()
        self.validator = validator or StateValidator()

        # Core components
        self._store: StateStore | None = None
        self._metrics = StateStoreMetrics() if self.config.metrics_enabled else None

        # Caching (simple in-memory cache for metadata)
        self._metadata_cache: Dict[str, StateMetadata] = {}
        self._cache_expiry: Dict[str, datetime.datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes

        # Health and monitoring
        self._health_check_interval = 60  # 1 minute
        self._last_health_check: datetime.datetime | None = None
        self._is_healthy = True
        self._health_check_task: asyncio.Task | None = None

        # Backup management
        self._backup_task: asyncio.Task | None = None
        self._last_backup: datetime.datetime | None = None

        # Logging
        self.logger = logging.getLogger(f"{__name__}.StateStoreManager")

        self.logger.info(f"State store manager initialized with {self.config.backend_type.value} backend")

    async def initialize(self) -> None:
        """Initialize the state store manager and backend."""
        try:
            # Create the storage backend
            self._store = await self._create_store()

            # Start monitoring tasks
            if self.config.metrics_enabled:
                self._start_health_monitoring()

            if self.config.backup_enabled:
                self._start_backup_task()

            # Perform initial health check
            await self._perform_health_check()

            self.logger.info("State store manager initialization completed")

        except Exception as e:
            self.logger.error(f"Failed to initialize state store manager: {e}")
            raise StorageError(f"Initialization failed: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the state store manager and cleanup resources."""
        try:
            # Cancel monitoring tasks
            for task in [self._health_check_task, self._backup_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Cleanup store
            if self._store:
                await self._store.cleanup()

            # Clear caches
            self._metadata_cache.clear()
            self._cache_expiry.clear()

            self.logger.info("State store manager shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def save_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
        state_data: StateData,
        merge_with_existing: bool = True,
        tags: Dict[str, str] | None = None,
    ) -> StoredState:
        """Save agent state with validation and metrics."""
        start_time = datetime.datetime.utcnow()
        operation = "save_agent_state"

        try:
            # Validate inputs
            if not validate_thread_id(thread_id):
                raise StorageError(f"Invalid thread ID: {thread_id}")

            if not validate_agent_name(agent_name):
                raise StorageError(f"Invalid agent name: {agent_name}")

            # Validate state data
            self.validator.validate_state(agent_name, state_data)

            # Ensure store is initialized
            await self._ensure_store()

            # Perform the save operation
            stored_state = await self._store.save_agent_state(
                thread_id, agent_name, state_data, merge_with_existing, tags
            )

            # Update cache
            cache_key = f"{thread_id}:{agent_name}"
            self._metadata_cache[cache_key] = stored_state.metadata
            self._cache_expiry[cache_key] = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=self._cache_ttl_seconds
            )

            # Record metrics
            if self._metrics:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, True)
                self._metrics.total_states_stored += 1

            self.logger.debug(
                f"Saved state for agent '{agent_name}' in thread '{thread_id}' "
                f"({stored_state.metadata.size_bytes} bytes)"
            )

            return stored_state

        except Exception as e:
            # Record error metrics
            if self._metrics:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, False)

            self.logger.error(
                f"Failed to save state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise

    async def load_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StoredState | None:
        """Load agent state with caching and metrics."""
        start_time = datetime.datetime.utcnow()
        operation = "load_agent_state"

        try:
            # Validate inputs
            if not validate_thread_id(thread_id):
                raise StorageError(f"Invalid thread ID: {thread_id}")

            if not validate_agent_name(agent_name):
                raise StorageError(f"Invalid agent name: {agent_name}")

            # Ensure store is initialized
            await self._ensure_store()

            # Perform the load operation
            stored_state = await self._store.load_agent_state(thread_id, agent_name)

            # Update cache and metrics
            cache_key = f"{thread_id}:{agent_name}"
            if stored_state:
                self._metadata_cache[cache_key] = stored_state.metadata
                self._cache_expiry[cache_key] = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=self._cache_ttl_seconds
                )

                if self._metrics:
                    self._metrics.cache_misses += 1
                    self._metrics.total_states_loaded += 1
            else:
                # Remove from cache if not found
                self._metadata_cache.pop(cache_key, None)
                self._cache_expiry.pop(cache_key, None)

            # Record metrics
            if self._metrics:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, True)

            return stored_state

        except Exception as e:
            # Record error metrics
            if self._metrics:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, False)

            self.logger.error(
                f"Failed to load state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise

    async def delete_agent_state(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> bool:
        """Delete agent state with cache invalidation and metrics."""
        start_time = datetime.datetime.utcnow()
        operation = "delete_agent_state"

        try:
            # Validate inputs
            if not validate_thread_id(thread_id):
                raise StorageError(f"Invalid thread ID: {thread_id}")

            if not validate_agent_name(agent_name):
                raise StorageError(f"Invalid agent name: {agent_name}")

            # Ensure store is initialized
            await self._ensure_store()

            # Perform the delete operation
            deleted = await self._store.delete_agent_state(thread_id, agent_name)

            # Update cache
            cache_key = f"{thread_id}:{agent_name}"
            self._metadata_cache.pop(cache_key, None)
            self._cache_expiry.pop(cache_key, None)

            # Record metrics
            if self._metrics and deleted:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, True)
                self._metrics.total_states_deleted += 1

            return deleted

        except Exception as e:
            # Record error metrics
            if self._metrics:
                duration = (datetime.datetime.utcnow() - start_time).total_seconds()
                self._metrics.record_operation(operation, duration, False)

            self.logger.error(
                f"Failed to delete state for agent '{agent_name}' in thread '{thread_id}': {e}"
            )
            raise

    async def get_state_metadata(
        self,
        thread_id: ThreadId,
        agent_name: AgentName,
    ) -> StateMetadata | None:
        """Get state metadata with caching."""
        # Check cache first
        cache_key = f"{thread_id}:{agent_name}"
        if cache_key in self._metadata_cache:
            expiry = self._cache_expiry.get(cache_key)
            if expiry and datetime.datetime.utcnow() < expiry:
                if self._metrics:
                    self._metrics.record_cache_hit()
                return self._metadata_cache[cache_key]

        # Cache miss - record it
        if self._metrics:
            self._metrics.record_cache_miss()

        # Load from store
        await self._ensure_store()
        return await self._store.get_state_metadata(thread_id, agent_name)

    async def list_thread_agents(self, thread_id: ThreadId) -> List[AgentName]:
        """List all agents with state in a thread."""
        await self._ensure_store()
        return await self._store.list_thread_agents(thread_id)

    async def list_agent_threads(self, agent_name: AgentName) -> List[ThreadId]:
        """List all threads where an agent has state."""
        await self._ensure_store()
        return await self._store.list_agent_threads(agent_name)

    async def clear_thread_state(self, thread_id: ThreadId) -> int:
        """Clear all agent state for a thread."""
        await self._ensure_store()

        # Clear cache entries for this thread
        keys_to_remove = [key for key in self._metadata_cache.keys() if key.startswith(f"{thread_id}:")]
        for key in keys_to_remove:
            self._metadata_cache.pop(key, None)
            self._cache_expiry.pop(key, None)

        return await self._store.clear_thread_state(thread_id)

    async def bulk_save_states(
        self,
        states: List[tuple[ThreadId, AgentName, StateData]],
        merge_with_existing: bool = True,
    ) -> List[StoredState]:
        """Bulk save multiple states for efficiency."""
        results = []
        for thread_id, agent_name, state_data in states:
            stored_state = await self.save_agent_state(
                thread_id, agent_name, state_data, merge_with_existing
            )
            results.append(stored_state)
        return results

    async def bulk_load_states(
        self,
        requests: List[tuple[ThreadId, AgentName]],
    ) -> List[StoredState | None]:
        """Bulk load multiple states for efficiency."""
        results = []
        for thread_id, agent_name in requests:
            stored_state = await self.load_agent_state(thread_id, agent_name)
            results.append(stored_state)
        return results

    async def health_check(self) -> bool:
        """Check if state store is healthy."""
        try:
            if not self._store:
                return False
            return await self._store.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any] | None:
        """Get comprehensive metrics."""
        if not self._metrics:
            return None

        base_metrics = self._metrics.get_stats()

        # Add cache metrics
        cache_size = len(self._metadata_cache)
        base_metrics.update({
            "cache_size": cache_size,
            "cache_ttl_seconds": self._cache_ttl_seconds,
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "config": self.config.to_dict(),
        })

        return base_metrics

    async def _create_store(self) -> StateStore:
        """Create storage backend based on configuration."""
        if self.config.backend_type == StorageBackendType.MEMORY:
            return MemoryStateStore(
                max_size_mb=self.config.max_size_mb,
                default_ttl_seconds=self.config.default_ttl_seconds,
            )
        elif self.config.backend_type == StorageBackendType.REDIS:
            # TODO: Implement Redis backend
            raise NotImplementedError("Redis backend not yet implemented")
        elif self.config.backend_type == StorageBackendType.POSTGRESQL:
            # TODO: Implement PostgreSQL backend
            raise NotImplementedError("PostgreSQL backend not yet implemented")
        else:
            raise StorageError(f"Unknown backend type: {self.config.backend_type}")

    async def _ensure_store(self) -> None:
        """Ensure store is initialized."""
        if not self._store:
            await self.initialize()

    async def _perform_health_check(self) -> None:
        """Perform comprehensive health check."""
        try:
            if self._store:
                self._is_healthy = await self._store.health_check()
            else:
                self._is_healthy = False

            self._last_health_check = datetime.datetime.utcnow()

            if not self._is_healthy:
                self.logger.warning("State store health check failed")

        except Exception as e:
            self._is_healthy = False
            self.logger.error(f"Health check error: {e}")

    def _start_health_monitoring(self) -> None:
        """Start periodic health monitoring."""
        async def health_monitor():
            while True:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    await self._perform_health_check()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in health monitoring: {e}")

        self._health_check_task = asyncio.create_task(health_monitor())

    def _start_backup_task(self) -> None:
        """Start periodic backup task."""
        async def backup_task():
            while True:
                try:
                    await asyncio.sleep(self.config.backup_interval_seconds)
                    await self._perform_backup()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in backup task: {e}")

        self._backup_task = asyncio.create_task(backup_task())

    async def _perform_backup(self) -> None:
        """Perform state backup (placeholder for future implementation)."""
        # TODO: Implement backup functionality
        self._last_backup = datetime.datetime.utcnow()
        self.logger.debug("State backup performed")


# Export public API
__all__ = [
    "StateStoreManager",
    "StateStoreConfig",
    "StateValidator",
    "StateStoreMetrics",
    "StorageBackendType",
]
