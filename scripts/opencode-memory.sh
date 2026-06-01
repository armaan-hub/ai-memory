#!/bin/bash
# OpenCode Memory Bridge - Use this to start OpenCode with memory hub

export MCP_TOOL="opencode"

# Add MCP daemon to PATH
export PATH="$HOME/.claude/mcp-daemon:$PATH"

# Start OpenCode with MCP server
opencode "$@"
