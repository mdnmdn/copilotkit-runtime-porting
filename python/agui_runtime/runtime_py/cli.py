"""
Command Line Interface for CopilotKit Python Runtime.

This module provides a CLI for starting and managing the CopilotKit Python Runtime
server. It supports various configuration options and development/production modes.

Usage:
    copilotkit-runtime --host 0.0.0.0 --port 8000
    copilotkit-runtime --config config.json --log-level DEBUG
    copilotkit-runtime --help
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from pydantic import ValidationError

from agui_runtime.runtime_py.app.main import create_app
from agui_runtime.runtime_py.core.types import RuntimeConfig


def setup_logging(log_level: str, log_format: str | None = None) -> None:
    """
    Configure logging for the CLI and application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Optional custom log format string
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    try:
        level = getattr(logging, log_level.upper())
    except AttributeError:
        level = logging.INFO
        print(f"Warning: Invalid log level '{log_level}', using INFO")

    logging.basicConfig(level=level, format=log_format, stream=sys.stdout, force=True)

    # Suppress noisy loggers in production
    if level >= logging.WARNING:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def load_config_file(config_path: str) -> dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with config_file.open("r") as f:
            config_data = json.load(f)
        return config_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}") from e


def create_runtime_config(args: argparse.Namespace) -> RuntimeConfig:
    """
    Create a RuntimeConfig from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        RuntimeConfig instance

    Raises:
        ValidationError: If configuration is invalid
    """
    config_data = {}

    # Load from config file if specified
    if args.config:
        try:
            config_data = load_config_file(args.config)
            print(f"Loaded configuration from: {args.config}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)

    # Override with command line arguments
    if args.host:
        config_data["host"] = args.host
    if args.port:
        config_data["port"] = args.port
    if args.graphql_path:
        config_data["graphql_path"] = args.graphql_path
    if args.providers:
        config_data["enabled_providers"] = args.providers
    if args.state_store:
        config_data["state_store_backend"] = args.state_store
    if args.redis_url:
        config_data["redis_url"] = args.redis_url
    if args.database_url:
        config_data["database_url"] = args.database_url
    if args.cors_origins:
        config_data["cors_origins"] = args.cors_origins
    if args.max_requests:
        config_data["max_concurrent_requests"] = args.max_requests
    if args.timeout:
        config_data["request_timeout_seconds"] = args.timeout

    # Load environment variables with AGUI_RUNTIME_ prefix
    env_config = {}
    for key, value in os.environ.items():
        if key.startswith("AGUI_RUNTIME_"):
            # Convert AGUI_RUNTIME_HOST to host
            config_key = key[11:].lower()  # Remove AGUI_RUNTIME_ prefix
            env_config[config_key] = value

    # Merge: env_config < config_file < command_line_args
    final_config = {**env_config, **config_data}

    try:
        return RuntimeConfig(**final_config)
    except ValidationError as e:
        print(f"Configuration validation error: {e}")
        sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create the command line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="agui-runtime",
        description="AGUI Runtime Python - Production-ready Python implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  agui-runtime                                    # Start with defaults
  agui-runtime --host 0.0.0.0 --port 8000       # Custom host/port
  agui-runtime --config config.json              # Load from config file
  agui-runtime --providers langgraph crewai      # Enable specific providers
  agui-runtime --dev                             # Development mode
  agui-runtime --log-level DEBUG                 # Debug logging

Environment Variables:
  AGUI_RUNTIME_HOST                 Server host (default: 0.0.0.0)
  AGUI_RUNTIME_PORT                 Server port (default: 8000)
  AGUI_RUNTIME_GRAPHQL_PATH         GraphQL endpoint path
  AGUI_RUNTIME_ENABLED_PROVIDERS    Comma-separated provider list
  AGUI_RUNTIME_STATE_STORE_BACKEND  State storage backend
  AGUI_RUNTIME_REDIS_URL            Redis connection URL
  AGUI_RUNTIME_DATABASE_URL         Database connection URL
  LOG_LEVEL                       Logging level""",
    )

    # Server configuration
    server_group = parser.add_argument_group("Server Options")
    server_group.add_argument(
        "--host", type=str, help="Host to bind the server to (default: 0.0.0.0)"
    )
    server_group.add_argument("--port", type=int, help="Port to bind the server to (default: 8000)")
    server_group.add_argument(
        "--graphql-path", type=str, help="Path for GraphQL endpoint (default: /api/copilotkit)"
    )

    # Development options
    dev_group = parser.add_argument_group("Development Options")
    dev_group.add_argument(
        "--dev", action="store_true", help="Enable development mode (auto-reload, debug logging)"
    )
    dev_group.add_argument(
        "--reload", action="store_true", help="Enable auto-reload on file changes"
    )
    dev_group.add_argument(
        "--workers", type=int, default=1, help="Number of worker processes (default: 1)"
    )

    # Provider configuration
    provider_group = parser.add_argument_group("Provider Options")
    provider_group.add_argument(
        "--providers",
        nargs="+",
        choices=["langgraph", "crewai"],
        help="Enabled providers (default: langgraph)",
    )

    # Storage configuration
    storage_group = parser.add_argument_group("Storage Options")
    storage_group.add_argument(
        "--state-store",
        choices=["memory", "redis", "postgresql"],
        help="State storage backend (default: memory)",
    )
    storage_group.add_argument("--redis-url", type=str, help="Redis connection URL")
    storage_group.add_argument("--database-url", type=str, help="Database connection URL")

    # Security and performance
    security_group = parser.add_argument_group("Security & Performance")
    security_group.add_argument(
        "--cors-origins", nargs="+", help="CORS allowed origins (default: ['*'])"
    )
    security_group.add_argument(
        "--max-requests", type=int, help="Maximum concurrent requests (default: 100)"
    )
    security_group.add_argument(
        "--timeout", type=int, help="Request timeout in seconds (default: 300)"
    )

    # Logging and debugging
    logging_group = parser.add_argument_group("Logging Options")
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    logging_group.add_argument("--log-format", type=str, help="Custom log format string")
    logging_group.add_argument(
        "--access-log",
        action="store_true",
        default=True,
        help="Enable access logging (default: enabled)",
    )
    logging_group.add_argument(
        "--no-access-log", action="store_false", dest="access_log", help="Disable access logging"
    )

    # Configuration file
    parser.add_argument("--config", type=str, help="Path to JSON configuration file")

    # Version
    parser.add_argument("--version", action="version", version="AGUI Runtime Python 0.1.0")

    return parser


def validate_args(args: argparse.Namespace) -> None:
    """
    Validate command line arguments and apply development mode defaults.

    Args:
        args: Parsed command line arguments
    """
    # Apply development mode defaults
    if args.dev:
        if not args.log_level or args.log_level == "INFO":
            args.log_level = "DEBUG"
        args.reload = True
        if not args.host:
            args.host = "127.0.0.1"  # Localhost for development

    # Validate port range
    if args.port and not (1 <= args.port <= 65535):
        print(f"Error: Port must be between 1 and 65535, got {args.port}")
        sys.exit(1)

    # Validate workers with reload
    if args.reload and args.workers > 1:
        print("Warning: Cannot use multiple workers with reload enabled, setting workers=1")
        args.workers = 1

    # Validate storage configuration
    if (
        args.state_store == "redis"
        and not args.redis_url
        and not os.getenv("AGUI_RUNTIME_REDIS_URL")
    ):
        print("Error: Redis URL required when using Redis state store")
        sys.exit(1)

    if (
        args.state_store == "postgresql"
        and not args.database_url
        and not os.getenv("AGUI_RUNTIME_DATABASE_URL")
    ):
        print("Error: Database URL required when using PostgreSQL state store")
        sys.exit(1)


def run_server(args: argparse.Namespace) -> None:
    """
    Start the CopilotKit runtime server.

    Args:
        args: Parsed and validated command line arguments
    """
    # Setup logging
    setup_logging(args.log_level, args.log_format)

    logger = logging.getLogger(__name__)

    # Create runtime configuration
    try:
        config = create_runtime_config(args)
    except Exception as e:
        logger.error(f"Failed to create configuration: {e}")
        sys.exit(1)

    # Create FastAPI app
    try:
        create_app()
        logger.info("FastAPI application created successfully")
    except Exception as e:
        logger.error(f"Failed to create FastAPI application: {e}")
        sys.exit(1)

    # Determine server configuration
    host = config.host
    port = config.port
    reload = args.reload
    workers = args.workers if not reload else 1

    logger.info("Starting CopilotKit Python Runtime")
    logger.info(f"Server: {host}:{port}")
    logger.info(f"GraphQL endpoint: {config.graphql_path}")
    logger.info(f"Reload: {reload}, Workers: {workers}")
    logger.info(f"Log level: {args.log_level}")

    if args.providers:
        logger.info(f"Enabled providers: {', '.join(args.providers)}")

    # Start the server
    try:
        uvicorn.run(
            "agui_runtime.runtime_py.app.main:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            access_log=args.access_log,
            log_config=None,  # Use our custom logging
            server_header=False,
            date_header=False,
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


def main() -> None:
    """
    Main CLI entry point.
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    validate_args(args)

    # Run the server
    run_server(args)


if __name__ == "__main__":
    main()
