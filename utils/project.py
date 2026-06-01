"""Project detection utility for MCP Memory Hub."""

import os
import hashlib
from pathlib import Path
from typing import Optional

# Environment variables to check (in order of priority)
ENV_VARS = [
    "CLAUDE_PROJECT_PATH",
    "CLAUDE_WORKING_DIR",
    "PROJECT_DIR",
    "PROJECT_PATH",
    "GIT_DIR",  # Git sets this for worktrees
]

# Project markers (files/dirs that indicate project root)
PROJECT_MARKERS = [
    ".git",           # Git repository
    "package.json",   # Node.js
    "pyproject.toml", # Python
    "Cargo.toml",     # Rust
    "go.mod",         # Go
    "pom.xml",        # Java/Maven
    "build.gradle",   # Java/Gradle
    ".project",       # Eclipse/Kepler
    "requirements.txt", # Python pip
    "Makefile",       # Generic build
    "CMakeLists.txt", # C/C++
    ".venv",          # Python virtual env
    "venv/",          # Python virtual env alt
]


def get_current_project_path() -> str:
    """Get the current project path from environment or file system."""
    # 1. Check environment variables (highest priority)
    for var in ENV_VARS:
        path = os.environ.get(var)
        if path and Path(path).exists():
            return str(Path(path).resolve())

    # 2. Check PWD
    cwd = Path.cwd()
    if cwd.exists():
        return str(cwd.resolve())

    # 3. Fallback to home
    return str(Path.home())


def find_project_root(start_path: Path) -> Optional[Path]:
    """Find project root by searching for markers upward from start_path."""
    current = start_path.resolve()

    # Don't search above home directory
    home = Path.home().resolve()

    while current != home and current != current.parent:
        # Check for any project marker
        for marker in PROJECT_MARKERS:
            if (current / marker).exists():
                return current

        current = current.parent

    # No marker found, return the start path
    return start_path.resolve()


def get_project_hash(path: str) -> str:
    """Generate a consistent project hash from path."""
    normalized = str(Path(path).resolve())
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def detect_project(explicit_path: Optional[str] = None) -> dict:
    """
    Detect project from explicit path, environment, or file system.

    Returns dict with:
        - id: project hash (first 12 chars of MD5)
        - path: resolved absolute path
        - name: directory name
        - marker: the marker file that identified the project (if any)
    """
    if explicit_path:
        path = Path(explicit_path).resolve()
    else:
        # Try to find project root from current working directory
        cwd = Path.cwd()
        path = find_project_root(cwd)

    marker = None
    for m in PROJECT_MARKERS:
        if (path / m).exists():
            marker = m
            break

    return {
        "id": get_project_hash(str(path)),
        "path": str(path),
        "name": path.name,
        "marker": marker
    }


def get_cwd_project() -> dict:
    """Get project info for current working directory."""
    return detect_project()


# CLI helper for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        project = detect_project(sys.argv[1])
    else:
        project = get_cwd_project()

    print(f"Project: {project['name']}")
    print(f"Path: {project['path']}")
    print(f"ID: {project['id']}")
    print(f"Marker: {project['marker'] or '(none)'}")