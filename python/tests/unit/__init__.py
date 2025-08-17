"""
CopilotKit Runtime Python - Unit Tests

This module contains unit tests for individual components and classes
of the CopilotKit Python Runtime. Unit tests focus on testing isolated
functionality without external dependencies.

Test Coverage:
- CopilotRuntime core functionality
- AgentProvider interface and implementations
- Type definitions and data structures
- Configuration management
- GraphQL schema and types
- Utility functions and helpers
- Error handling and validation

Unit Test Guidelines:
- Mock all external dependencies
- Test individual functions and methods in isolation
- Focus on business logic and edge cases
- Maintain fast execution times
- Use dependency injection for testability
- Cover error conditions and validation

Usage:
    # Run all unit tests
    pytest tests/unit/

    # Run specific unit test file
    pytest tests/unit/test_runtime.py

    # Run with coverage
    pytest tests/unit/ --cov=copilotkit.runtime_py

    # Run unit tests with markers
    pytest -m "unit"
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Test fixtures and utilities
from copilotkit.runtime_py.core.types import (
    AgentDescriptor,
    CopilotRequestType,
    MessageRole,
    MessageStatus,
    RuntimeConfig,
)

# Unit test directory
UNIT_TESTS_DIR = Path(__file__).parent

# Common test data
TEST_THREAD_ID = "test-thread-123"
TEST_AGENT_NAME = "test_agent"
TEST_USER_ID = "test-user-456"
TEST_SESSION_ID = "test-session-789"


def create_test_runtime_config(**overrides) -> RuntimeConfig:
    """
    Create a test runtime configuration with sensible defaults.

    Args:
        **overrides: Configuration values to override

    Returns:
        RuntimeConfig instance for testing
    """
    config_data = {
        "host": "127.0.0.1",
        "port": 8080,
        "graphql_path": "/test/graphql",
        "enabled_providers": ["test_provider"],
        "state_store_backend": "memory",
        "cors_origins": ["http://localhost:3000"],
        "max_concurrent_requests": 10,
        "request_timeout_seconds": 30,
    }
    config_data.update(overrides)
    return RuntimeConfig(**config_data)


def create_test_agent_descriptor(**overrides) -> AgentDescriptor:
    """
    Create a test agent descriptor with default values.

    Args:
        **overrides: Agent properties to override

    Returns:
        AgentDescriptor instance for testing
    """
    agent_data = {
        "name": TEST_AGENT_NAME,
        "description": "A test agent for unit testing",
        "version": "1.0.0",
        "capabilities": ["test", "mock"],
    }
    agent_data.update(overrides)
    return AgentDescriptor(**agent_data)


class MockAsyncContextManager:
    """Mock async context manager for testing."""

    def __init__(self, return_value=None):
        self.return_value = return_value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return False


class AsyncIteratorMock:
    """Mock async iterator for testing streaming responses."""

    def __init__(self, items: list[Any]):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


# Common pytest fixtures for unit tests
@pytest.fixture
def test_config():
    """Fixture providing a test runtime configuration."""
    return create_test_runtime_config()


@pytest.fixture
def test_agent():
    """Fixture providing a test agent descriptor."""
    return create_test_agent_descriptor()


@pytest.fixture
def mock_fastapi_app():
    """Fixture providing a mock FastAPI app."""
    from fastapi import FastAPI

    return FastAPI(title="Test App")


@pytest.fixture
def event_loop():
    """Fixture providing a clean event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test utilities
def assert_agent_equals(actual: AgentDescriptor, expected: AgentDescriptor):
    """
    Assert that two agent descriptors are equal.

    Args:
        actual: The actual agent descriptor
        expected: The expected agent descriptor
    """
    assert actual.name == expected.name
    assert actual.description == expected.description
    assert actual.version == expected.version
    assert actual.capabilities == expected.capabilities


def assert_config_equals(actual: RuntimeConfig, expected: RuntimeConfig):
    """
    Assert that two runtime configurations are equal.

    Args:
        actual: The actual runtime configuration
        expected: The expected runtime configuration
    """
    assert actual.host == expected.host
    assert actual.port == expected.port
    assert actual.graphql_path == expected.graphql_path
    assert actual.enabled_providers == expected.enabled_providers


async def run_async_test(coro):
    """
    Helper to run async test functions.

    Args:
        coro: Async coroutine to run

    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        return await coro
    finally:
        loop.close()


# Mock classes for testing
class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.debug_calls = []
        self.info_calls = []
        self.warning_calls = []
        self.error_calls = []

    def debug(self, msg, *args, **kwargs):
        self.debug_calls.append((msg, args, kwargs))

    def info(self, msg, *args, **kwargs):
        self.info_calls.append((msg, args, kwargs))

    def warning(self, msg, *args, **kwargs):
        self.warning_calls.append((msg, args, kwargs))

    def error(self, msg, *args, **kwargs):
        self.error_calls.append((msg, args, kwargs))

    def child(self, **kwargs):
        return MockLogger()


__all__ = [
    # Test directory
    "UNIT_TESTS_DIR",
    # Test constants
    "TEST_THREAD_ID",
    "TEST_AGENT_NAME",
    "TEST_USER_ID",
    "TEST_SESSION_ID",
    # Factory functions
    "create_test_runtime_config",
    "create_test_agent_descriptor",
    # Mock classes
    "MockAsyncContextManager",
    "AsyncIteratorMock",
    "MockLogger",
    # Test utilities
    "assert_agent_equals",
    "assert_config_equals",
    "run_async_test",
]
