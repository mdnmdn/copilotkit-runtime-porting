"""
CopilotKit Runtime Python - Test Suite

This package contains comprehensive tests for the CopilotKit Python Runtime,
organized into multiple test categories to ensure thorough coverage and
maintainability.

Test Structure:
- unit/: Unit tests for individual components and classes
- integration/: Integration tests for provider implementations and external services
- e2e/: End-to-end tests for complete workflows and GraphQL API

Test Categories:
- Core runtime functionality and provider management
- GraphQL schema and resolver testing
- Provider implementations (LangGraph, CrewAI)
- Storage backend implementations
- FastAPI integration and HTTP endpoints
- Configuration and environment handling
- Error handling and edge cases

Usage:
    # Run all tests
    pytest

    # Run specific test category
    pytest tests/unit/
    pytest tests/integration/
    pytest tests/e2e/

    # Run with coverage
    pytest --cov=agui_runtime.runtime_py

    # Run specific test markers
    pytest -m "unit"
    pytest -m "integration"
    pytest -m "e2e"
    pytest -m "slow"
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path for testing
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Test configuration
TESTS_DIR = Path(__file__).parent
UNIT_TESTS_DIR = TESTS_DIR / "unit"
INTEGRATION_TESTS_DIR = TESTS_DIR / "integration"
E2E_TESTS_DIR = TESTS_DIR / "e2e"

# Test environment variables
TEST_ENV_PREFIX = "AGUI_RUNTIME_TEST_"


def get_test_env(key: str, default=None):
    """
    Get a test-specific environment variable.

    Args:
        key: Environment variable key (without TEST_ prefix)
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    return os.getenv(f"{TEST_ENV_PREFIX}{key}", default)


def is_integration_tests_enabled() -> bool:
    """
    Check if integration tests should be run.

    Returns:
        True if integration tests are enabled
    """
    return get_test_env("INTEGRATION_ENABLED", "false").lower() == "true"


def is_e2e_tests_enabled() -> bool:
    """
    Check if end-to-end tests should be run.

    Returns:
        True if e2e tests are enabled
    """
    return get_test_env("E2E_ENABLED", "false").lower() == "true"


__version__ = "0.1.0"

__all__ = [
    "TESTS_DIR",
    "UNIT_TESTS_DIR",
    "INTEGRATION_TESTS_DIR",
    "E2E_TESTS_DIR",
    "get_test_env",
    "is_integration_tests_enabled",
    "is_e2e_tests_enabled",
]
