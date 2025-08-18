"""
AGUI Runtime Python - Core Runtime Implementation.

This module provides the main CopilotRuntime class and supporting infrastructure
for integrating Python AI frameworks with AGUI's GraphQL-based frontend runtime.

Key Components:
- CopilotRuntime: Main orchestrator class for FastAPI integration
- Provider interfaces: Pluggable AI framework connectors
- GraphQL schema: Complete schema compatibility with TypeScript runtime
- Streaming support: Real-time message and event delivery

Example Usage:
    ```python
    from agui_runtime.runtime_py import CopilotRuntime
    from fastapi import FastAPI

    app = FastAPI()
    runtime = CopilotRuntime()

    # Mount runtime to FastAPI app
    runtime.mount_to_fastapi(app, path="/api/agui")
    ```
"""

from agui_runtime.runtime_py.core.runtime import CopilotRuntime
from agui_runtime.runtime_py.core.types import (
    ActionInputAvailability,
    CopilotRequestType,
    MessageRole,
    MessageStatus,
)

__version__ = "0.1.0"
__author__ = "AGUI Runtime Team"

# Public API
__all__ = [
    "CopilotRuntime",
    "MessageRole",
    "MessageStatus",
    "CopilotRequestType",
    "ActionInputAvailability",
]
