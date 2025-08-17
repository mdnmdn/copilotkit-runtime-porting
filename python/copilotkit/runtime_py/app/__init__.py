"""
CopilotKit Runtime App - FastAPI application components.

This module contains the FastAPI application setup and server configuration
for the CopilotKit Python Runtime. It provides the web server infrastructure
for serving GraphQL endpoints and handling HTTP requests.

Key Components:
- FastAPI application factory
- Server lifecycle management
- Request handling and middleware
- Health check endpoints
- Runtime mounting functionality

Example Usage:
    ```python
    from copilotkit.runtime_py.app import create_app

    app = create_app()
    # App is ready to be served with uvicorn
    ```
"""

from copilotkit.runtime_py.app.main import (
    app,
    create_app,
    mount_runtime_to_app,
    setup_logging,
)

__version__ = "0.1.0"

# Public API
__all__ = [
    "create_app",
    "mount_runtime_to_app",
    "setup_logging",
    "app",
]
