"""Configuration module for MCP Memory Hub."""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from config.json."""
    if not CONFIG_PATH.exists():
        return get_defaults()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Expand ~ in paths
    config["database_path"] = os.path.expanduser(config["database_path"])
    config["log_file"] = os.path.expanduser(config["log_file"])

    return config


def get_defaults() -> dict[str, Any]:
    """Return default configuration."""
    base = Path.home() / ".claude" / "mcp-daemon"
    return {
        "version": "1.0",
        "database_path": str(base / "data" / "memory.db"),
        "log_level": "INFO",
        "log_file": str(base / "logs" / "mcp-daemon.log"),
        "max_recent_items": 50,
        "max_search_results": 20,
        "compact_tiers": {
            "light": {"max_items": 5, "min_importance": 8},
            "medium": {"max_items": 20, "min_importance": 1},
            "deep": {"max_items": 100, "min_importance": 1}
        },
        "handoff_retention_hours": 72,
        "server": {
            "transport": "stdio",
            "name": "mcp-memory-hub"
        }
    }


def get_config() -> dict[str, Any]:
    """Get current configuration (loads from file or returns defaults)."""
    return load_config()


# Convenience accessors
def get_database_path() -> Path:
    return Path(get_config()["database_path"])


def get_log_path() -> Path:
    return Path(get_config()["log_file"])


def get_log_level() -> str:
    return get_config().get("log_level", "INFO")


def init_logging():
    """Initialize logging based on config."""
    import logging
    level = get_log_level()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(get_log_path()),
            logging.StreamHandler()
        ]
    )