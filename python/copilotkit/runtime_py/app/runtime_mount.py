"""
FastAPI GraphQL Integration for CopilotKit Python Runtime.

This module provides the integration layer between FastAPI and Strawberry GraphQL,
enabling the CopilotRuntime to serve GraphQL endpoints with proper context injection,
middleware integration, and development tooling.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from strawberry.fastapi import GraphQLRouter, BaseContext
from strawberry.types import ExecutionContext, Info

from copilotkit.runtime_py.core.runtime import CopilotRuntime
from copilotkit.runtime_py.graphql.schema import schema


class GraphQLContext(BaseContext):
    """
    GraphQL execution context containing runtime and request information.

    This context is injected into all GraphQL resolvers, providing access to:
    - CopilotRuntime instance for agent operations
    - FastAPI Request object for HTTP context
    - Authentication information (in later phases)
    - Request metadata and tracing information
    """

    def __init__(
        self,
        runtime: CopilotRuntime,
        request: Request,
        response: Response,
    ) -> None:
        """
        Initialize GraphQL context.

        Args:
            runtime: The CopilotRuntime instance
            request: FastAPI Request object
            response: FastAPI Response object
        """
        super().__init__()
        self.runtime = runtime
        self.request = request
        self.response = response
        self.logger = logging.getLogger(f"{__name__}.GraphQLContext")

        # Request metadata
        self.request_id = getattr(request.state, "request_id", None)
        self.user_id = None  # Will be populated by auth middleware in later phases
        self.trace_id = None  # Will be populated by tracing middleware

    def get_client_ip(self) -> str:
        """Get the client IP address from the request."""
        forwarded_for = self.request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return self.request.client.host if self.request.client else "unknown"

    def get_user_agent(self) -> str:
        """Get the User-Agent header from the request."""
        return self.request.headers.get("User-Agent", "unknown")

    def log_operation(self, operation_name: str, operation_type: str) -> None:
        """Log GraphQL operation execution."""
        # Get logger fresh each time to support test mocking
        logger = logging.getLogger(f"{__name__}.GraphQLContext")
        logger.info(
            f"GraphQL {operation_type}: {operation_name}",
            extra={
                "operation_name": operation_name,
                "operation_type": operation_type,
                "client_ip": self.get_client_ip(),
                "user_agent": self.get_user_agent(),
                "request_id": self.request_id,
                "user_id": self.user_id,
            }
        )


async def get_graphql_context(
    runtime: CopilotRuntime,
    request: Request,
    response: Response,
) -> GraphQLContext:
    """
    Create GraphQL context for resolver execution.

    This function is called for each GraphQL request to create the execution
    context that will be available to all resolvers via the `info.context` parameter.

    Args:
        runtime: The CopilotRuntime instance
        request: FastAPI Request object
        response: FastAPI Response object

    Returns:
        GraphQLContext instance with runtime and request information
    """
    return GraphQLContext(runtime=runtime, request=request, response=response)


def create_graphql_router(
    runtime: CopilotRuntime,
    path: str = "/graphql",
    include_playground: bool = True,
) -> GraphQLRouter:
    """
    Create a Strawberry GraphQL router with runtime context injection.

    Args:
        runtime: The CopilotRuntime instance to inject into context
        path: GraphQL endpoint path (default: "/graphql")
        include_playground: Whether to enable GraphQL Playground (default: True)

    Returns:
        Configured GraphQLRouter instance
    """
    logger = logging.getLogger(f"{__name__}.create_graphql_router")

    async def context_getter(request: Request, response: Response) -> GraphQLContext:
        """Context factory for GraphQL execution."""
        return await get_graphql_context(runtime, request, response)

    # Create GraphQL router with context injection
    graphql_router = GraphQLRouter(
        schema,
        path=path,
        context_getter=context_getter,
        graphql_ide="playground" if include_playground else None,
    )

    # Add custom GraphQL playground if needed
    if include_playground:
        @graphql_router.get("/playground", response_class=HTMLResponse)
        async def graphql_playground() -> str:
            """Custom GraphQL Playground endpoint."""
            return get_playground_html(path)

    logger.info(f"Created GraphQL router for path: {path}")
    logger.info(f"GraphQL Playground enabled: {include_playground}")

    return graphql_router


def get_playground_html(graphql_path: str) -> str:
    """
    Generate custom GraphQL Playground HTML.

    Args:
        graphql_path: The GraphQL endpoint path

    Returns:
        HTML string for the playground interface
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="robots" content="noindex" />
        <meta name="referrer" content="origin" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>CopilotKit GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.28/build/static/css/index.css" />
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.28/build/favicon.png" />
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.28/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root">
            <style>
                body {{
                    background-color: rgb(23, 42, 58);
                    font-family: Open Sans, sans-serif;
                    height: 90vh;
                }}
                #root {{
                    height: 100%;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .loading {{
                    font-size: 32px;
                    font-weight: 200;
                    color: rgba(255, 255, 255, .6);
                    margin-left: 20px;
                }}
                img {{
                    width: 78px;
                    height: 78px;
                }}
                .title {{
                    font-weight: 400;
                }}
            </style>
            <img src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.28/build/logo.png" alt="Loading..." />
            <div class="loading"> Loading
                <span class="title">CopilotKit GraphQL Playground</span>
            </div>
        </div>
        <script>window.addEventListener('load', function (event) {{
            GraphQLPlayground.init(document.getElementById('root'), {{
                endpoint: '{graphql_path}',
                settings: {{
                    'general.betaUpdates': false,
                    'editor.theme': 'dark',
                    'editor.cursorShape': 'line',
                    'editor.reuseHeaders': true,
                    'tracing.hideTracingResponse': true,
                    'queryPlan.hideQueryPlanResponse': true,
                    'editor.fontSize': 14,
                    'editor.fontFamily': '"Source Code Pro", "Consolas", "Inconsolata", "Droid Sans Mono", "Monaco", monospace',
                    'request.credentials': 'omit',
                }},
                tabs: [
                    {{
                        endpoint: '{graphql_path}',
                        query: `# Welcome to CopilotKit Python Runtime GraphQL Playground
#
# You can explore the available queries and mutations using the schema explorer
# on the right side. Here are some example operations to get you started:

# Get available agents
query GetAgents {{
  availableAgents {{
    agents {{
      name
      description
      version
      capabilities
    }}
  }}
}}

# Get runtime information
query GetRuntimeInfo {{
  runtimeInfo {{
    version
    providers
    agentsCount
  }}
}}

# Generate a copilot response (stub for now)
mutation GenerateResponse {{
  generateCopilotResponse(data: {{
    messages: [{{
      role: USER
      content: "Hello, CopilotKit!"
    }}]
    agentSession: {{
      threadId: "test-thread-123"
    }}
    requestType: CHAT
  }}) {{
    threadId
    status
    messages {{
      ... on Message {{
        id
        role
        content
        status
        createdAt
      }}
    }}
  }}
}}`,
                        variables: {{}},
                        headers: {{
                            "Content-Type": "application/json"
                        }}
                    }}
                ]
            }})
        }})</script>
    </body>
    </html>
    """


def mount_graphql_to_fastapi(
    app: FastAPI,
    runtime: CopilotRuntime,
    path: str = "/graphql",
    include_playground: bool = True,
    include_health_checks: bool = True,
) -> None:
    """
    Mount GraphQL endpoints to a FastAPI application.

    This function integrates the CopilotRuntime with FastAPI by:
    - Creating and mounting the GraphQL router
    - Setting up GraphQL Playground (if enabled)
    - Adding GraphQL-specific middleware
    - Configuring health check endpoints

    Args:
        app: FastAPI application to mount to
        runtime: CopilotRuntime instance
        path: GraphQL endpoint path (default: "/graphql")
        include_playground: Enable GraphQL Playground (default: True)
        include_health_checks: Include GraphQL health checks (default: True)
    """
    logger = logging.getLogger(f"{__name__}.mount_graphql_to_fastapi")

    # Create and include the GraphQL router
    graphql_router = create_graphql_router(
        runtime=runtime,
        path=path,
        include_playground=include_playground,
    )

    # Mount the router to the application
    app.include_router(graphql_router)

    # Add GraphQL health check endpoints if enabled
    if include_health_checks:
        @app.get(f"{path}/health")
        async def graphql_health() -> dict[str, Any]:
            """Health check specific to GraphQL functionality."""
            try:
                # Test GraphQL schema compilation
                from copilotkit.runtime_py.graphql.schema import get_schema_sdl
                schema_sdl = get_schema_sdl()

                # Test runtime agent discovery
                agents = await runtime.discover_agents()

                return {
                    "status": "healthy",
                    "service": "graphql",
                    "schema_valid": bool(schema_sdl),
                    "agents_available": len(agents),
                    "endpoint": path,
                    "playground_enabled": include_playground,
                }
            except Exception as e:
                logger.error(f"GraphQL health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "service": "graphql",
                    "error": str(e),
                    "endpoint": path,
                }

        @app.get(f"{path}/schema")
        async def graphql_schema() -> dict[str, str]:
            """Get the GraphQL schema SDL."""
            try:
                from copilotkit.runtime_py.graphql.schema import get_schema_sdl
                return {
                    "schema": get_schema_sdl(),
                    "format": "SDL"
                }
            except Exception as e:
                logger.error(f"Error getting GraphQL schema: {e}")
                return {
                    "error": str(e),
                    "schema": "",
                    "format": "error"
                }

    logger.info(f"GraphQL endpoints mounted successfully:")
    logger.info(f"  - GraphQL endpoint: {path}")
    if include_playground:
        logger.info(f"  - GraphQL Playground: {path}/playground")
    if include_health_checks:
        logger.info(f"  - Health check: {path}/health")
        logger.info(f"  - Schema introspection: {path}/schema")


def setup_graphql_middleware(app: FastAPI, runtime: CopilotRuntime) -> None:
    """
    Setup GraphQL-specific middleware.

    This function adds middleware that is specifically useful for GraphQL operations:
    - Request ID generation for tracing
    - GraphQL operation logging
    - Error handling and formatting

    Args:
        app: FastAPI application
        runtime: CopilotRuntime instance
    """
    import uuid

    @app.middleware("http")
    async def graphql_request_middleware(request: Request, call_next):
        """Middleware for GraphQL request processing."""
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log GraphQL requests
        if request.url.path.endswith("/graphql"):
            logger = logging.getLogger(f"{__name__}.graphql_request")
            logger.debug(
                f"GraphQL request: {request.method} {request.url}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                }
            )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# Export public interface
__all__ = [
    "GraphQLContext",
    "get_graphql_context",
    "create_graphql_router",
    "mount_graphql_to_fastapi",
    "setup_graphql_middleware",
    "get_playground_html",
]
