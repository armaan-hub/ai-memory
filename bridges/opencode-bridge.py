#!/usr/bin/env python3
"""OpenCode MCP Bridge - Connects OpenCode to Memory Hub."""

import sys
import json
import subprocess
from pathlib import Path

# Path to the MCP server
SERVER_PATH = Path.home() / ".claude" / "mcp-daemon" / "server.py"


def run_server():
    """Run the MCP server, passing through to OpenCode."""
    import asyncio
    import os

    # Add MCP daemon to path
    sys.path.insert(0, str(Path.home() / ".claude" / "mcp-daemon"))

    # Set environment
    os.environ["MCP_TOOL"] = "opencode"

    # Import and run the server
    from server import main
    asyncio.run(main())


if __name__ == "__main__":
    run_server()
