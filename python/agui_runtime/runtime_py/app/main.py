"""
Standalone FastAPI application for CopilotKit Python Runtime.

This module provides the main FastAPI application entry point for running
the CopilotKit Python Runtime as a standalone server. It can be started with:

    uvicorn agui_runtime.runtime_py.app.main:app --reload

The application includes:
- CopilotRuntime mounting with GraphQL endpoints
- Health check and info endpoints
- Proper CORS configuration
- Environment-based configuration
- Graceful startup and shutdown handling
"""

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agui_runtime.runtime_py.core.runtime import CopilotRuntime
from agui_runtime.runtime_py.core.types import RuntimeConfig


# Configure logging
def setup_logging() -> None:
    """Setup logging configuration for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO), format=log_format, stream=sys.stdout
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


# Global runtime instance
runtime: CopilotRuntime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager for startup and shutdown handling.

    Args:
        app: The FastAPI application instance.
    """
    global runtime

    logger = logging.getLogger(__name__)

    # Startup
    logger.info("Starting CopilotKit Python Runtime...")

    try:
        # Runtime should already be created and mounted during app creation
        if runtime is None:
            logger.error("Runtime not initialized during app creation")
            raise RuntimeError("Runtime not initialized during app creation")

        # Start the runtime
        await runtime.start()

        logger.info("Runtime started successfully")
        logger.info("GraphQL endpoint available at: /api/copilotkit/graphql")
        logger.info("GraphQL Playground available at: /api/copilotkit/graphql/playground")
        logger.info("Health check available at: /api/copilotkit/health")

        yield

    except Exception as e:
        logger.error(f"Failed to start runtime: {e}")
        raise

    finally:
        # Shutdown
        logger.info("Shutting down CopilotKit Python Runtime...")

        try:
            if runtime:
                await runtime.stop()
            logger.info("Runtime shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    global runtime

    # Setup logging first
    setup_logging()

    logger = logging.getLogger(__name__)

    # Load configuration from environment
    config = RuntimeConfig()

    # Create runtime instance
    runtime = CopilotRuntime(config=config)

    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="CopilotKit Python Runtime",
        description=(
            "Production-ready Python implementation of CopilotKit Runtime. "
            "Enables seamless integration with Python-based AI agent frameworks "
            "while maintaining complete compatibility with existing React applications."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Mount the runtime to the app (this must happen BEFORE startup)
    runtime.mount_to_fastapi(app, path="/api/copilotkit", include_graphql_playground=True)
    logger.info("Runtime mounted to FastAPI application")

    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler for unhandled errors."""
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "type": "INTERNAL_ERROR",
            },
        )

    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {
            "name": "CopilotKit Python Runtime",
            "version": "0.1.0",
            "status": "running",
            "docs_url": "/docs",
            "health_check": "/api/copilotkit/health",
            "runtime_info": "/api/copilotkit/info",
            "graphql_endpoint": "/api/copilotkit/graphql",
            "graphql_playground": "/api/copilotkit/graphql/playground",
        }

    logger.info("FastAPI application created successfully")
    return app


def mount_runtime_to_app(app: FastAPI) -> None:
    """
    Mount the CopilotRuntime to the FastAPI application.

    Note: This function is deprecated and kept for compatibility.
    Runtime mounting is now handled during app creation.

    Args:
        app: The FastAPI application to mount to.
    """
    logger = logging.getLogger(__name__)
    logger.info("Runtime mounting is now handled during app creation")


# Create the FastAPI application
app = create_app()


# Development server entry point
if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("AGUI_RUNTIME_HOST", "0.0.0.0")
    port = int(os.getenv("AGUI_RUNTIME_PORT", "8000"))
    reload = os.getenv("AGUI_RUNTIME_RELOAD", "true").lower() == "true"
    workers = int(os.getenv("AGUI_RUNTIME_WORKERS", "1"))

    print(f"Starting AGUI Runtime Python on {host}:{port}")
    print(f"Reload: {reload}, Workers: {workers}")
    print("Press CTRL+C to quit")

    # Run the server
    uvicorn.run(
        "agui_runtime.runtime_py.app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,  # Can't use workers with reload
        log_config=None,  # Use our custom logging setup
        access_log=True,
    )
