#!/usr/bin/env python3
"""
Development scripts for AGUI Runtime Python.

This module provides development utilities and scripts for the AGUI Runtime
Python project. It includes commands for running the server,
testing, linting, and other development tasks.

Usage:
    python scripts.py dev           # Start development server
    python scripts.py test         # Run all tests
    python scripts.py lint         # Run linting
    python scripts.py check        # Run all checks
    python scripts.py clean        # Clean build artifacts
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True, cwd: Path | None = None) -> int:
    """
    Run a shell command.

    Args:
        cmd: Command and arguments to run
        check: Whether to raise exception on non-zero exit code
        cwd: Working directory for the command

    Returns:
        Exit code of the command
    """
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, cwd=cwd)
        return result.returncode
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e.returncode


def dev_server():
    """Start the development server with auto-reload."""
    return run_command(
        [
            "python",
            "-m",
            "uvicorn",
            "agui_runtime.runtime_py.app.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
    )


def start_server():
    """Start the production server."""
    return run_command(["python", "-m", "agui_runtime.runtime_py.cli"])


def run_tests(category: str | None = None):
    """
    Run tests.

    Args:
        category: Test category (unit, integration, e2e) or None for all
    """
    cmd = ["pytest"]

    if category:
        if category == "unit":
            cmd.append("tests/unit/")
        elif category == "integration":
            cmd.append("tests/integration/")
        elif category == "e2e":
            cmd.append("tests/e2e/")
        else:
            print(f"Unknown test category: {category}")
            return 1

    return run_command(cmd)


def run_tests_with_coverage():
    """Run tests with coverage reporting."""
    return run_command(
        [
            "pytest",
            "--cov=agui_runtime.runtime_py",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-report=xml",
        ]
    )


def run_lint(fix: bool = False):
    """
    Run linting tools.

    Args:
        fix: Whether to automatically fix issues
    """
    # Run ruff
    ruff_cmd = ["ruff", "check", "."]
    if fix:
        ruff_cmd.append("--fix")

    ruff_result = run_command(ruff_cmd, check=False)

    # Run black
    black_cmd = ["black", "."]
    if not fix:
        black_cmd.append("--check")

    black_result = run_command(black_cmd, check=False)

    return max(ruff_result, black_result)


def run_type_check():
    """Run type checking with mypy."""
    return run_command(["mypy", "copilotkit/"], check=False)


def run_all_checks():
    """Run all code quality checks."""
    print("Running linting...")
    lint_result = run_lint()

    print("\nRunning type checking...")
    type_result = run_type_check()

    if lint_result == 0 and type_result == 0:
        print("\n✅ All checks passed!")
        return 0
    else:
        print("\n❌ Some checks failed!")
        return 1


def format_code():
    """Format code with black."""
    return run_command(["black", "."])


def clean_build():
    """Clean build artifacts and cache files."""
    import shutil

    # Directories to clean
    clean_dirs = [
        "__pycache__",
        ".pytest_cache",
        "htmlcov",
        ".coverage",
        "*.egg-info",
        "build",
        "dist",
    ]

    # Find and remove cache directories
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name in ["__pycache__", ".pytest_cache"]:
                dir_path = Path(root) / dir_name
                print(f"Removing: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)

        # Remove files
        for file_name in files:
            if file_name.endswith(".pyc") or file_name == ".coverage":
                file_path = Path(root) / file_name
                print(f"Removing: {file_path}")
                file_path.unlink(missing_ok=True)

    # Remove build directories
    for pattern in ["htmlcov", "*.egg-info", "build", "dist"]:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                print(f"Removing directory: {path}")
                shutil.rmtree(path, ignore_errors=True)
            else:
                print(f"Removing file: {path}")
                path.unlink(missing_ok=True)

    print("✅ Cleanup completed!")
    return 0


def install_dev_deps():
    """Install development dependencies."""
    return run_command(["uv", "sync", "--all-extras", "--dev"])


def update_deps():
    """Update dependencies."""
    return run_command(["uv", "lock", "--upgrade"])


def show_schema():
    """Show GraphQL schema."""
    return run_command(
        [
            "python",
            "-c",
            "from agui_runtime.runtime_py.graphql.schema import get_schema_sdl; print(get_schema_sdl())",
        ]
    )


def show_info():
    """Show runtime information."""
    return run_command(
        [
            "python",
            "-c",
            "from agui_runtime.runtime_py.core import CopilotRuntime; runtime = CopilotRuntime(); print(repr(runtime))",
        ]
    )


def main():
    """Main entry point for development scripts."""
    parser = argparse.ArgumentParser(
        description="CopilotKit Python Runtime Development Scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  dev              Start development server with auto-reload
  start            Start production server
  test             Run all tests
  test-unit        Run unit tests only
  test-integration Run integration tests only
  test-e2e         Run end-to-end tests only
  test-cov         Run tests with coverage reporting
  lint             Run linting (ruff + black check)
  lint-fix         Run linting with auto-fix
  format           Format code with black
  check            Run all quality checks (lint + type check)
  check-types      Run type checking only
  clean            Clean build artifacts and cache files
  install-dev      Install development dependencies
  update-deps      Update dependencies
  schema           Show GraphQL schema
  info             Show runtime information

Examples:
  python scripts.py dev
  python scripts.py test-cov
  python scripts.py lint-fix
        """,
    )

    parser.add_argument(
        "command",
        help="Command to run",
        choices=[
            "dev",
            "start",
            "test",
            "test-unit",
            "test-integration",
            "test-e2e",
            "test-cov",
            "lint",
            "lint-fix",
            "format",
            "check",
            "check-types",
            "clean",
            "install-dev",
            "update-deps",
            "schema",
            "info",
        ],
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Execute the requested command
    if args.command == "dev":
        return dev_server()
    elif args.command == "start":
        return start_server()
    elif args.command == "test":
        return run_tests()
    elif args.command == "test-unit":
        return run_tests("unit")
    elif args.command == "test-integration":
        return run_tests("integration")
    elif args.command == "test-e2e":
        return run_tests("e2e")
    elif args.command == "test-cov":
        return run_tests_with_coverage()
    elif args.command == "lint":
        return run_lint()
    elif args.command == "lint-fix":
        return run_lint(fix=True)
    elif args.command == "format":
        return format_code()
    elif args.command == "check":
        return run_all_checks()
    elif args.command == "check-types":
        return run_type_check()
    elif args.command == "clean":
        return clean_build()
    elif args.command == "install-dev":
        return install_dev_deps()
    elif args.command == "update-deps":
        return update_deps()
    elif args.command == "schema":
        return show_schema()
    elif args.command == "info":
        return show_info()
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
