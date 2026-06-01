#!/bin/bash
# Gemini Memory Bridge - Injects memory context into Gemini CLI

set -e

MCP_DAEMON="$HOME/.claude/mcp-daemon"
SERVER="$MCP_DAEMON/server.py"

# Check if server is running
if ! pgrep -f "python3.*server.py" > /dev/null 2>&1; then
    echo "⚠️  MCP Memory Hub not running. Starting..."
    "$MCP_DAEMON/scripts/start-daemon.sh" &
    sleep 2
fi

# Get context from MCP
get_context() {
    local project="${PWD##*/}"
    local context=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"context_inject","arguments":{"project":"'"$PWD"'","style":"concise"}}}' | python3 "$SERVER" 2>/dev/null || echo "")
    echo "$context"
}

# Check for pending handoff
check_handoff() {
    local project="${PWD##*/}"
    # Use Python to query the database directly
    python3 << EOF
import sys
sys.path.insert(0, '$MCP_DAEMON')
from database import init_database, detect_project, get_or_create_project, load_handover

init_database()
from utils.project import detect_project
project = detect_project()
project_data = get_or_create_project(project['path'])
handoff = load_handover(project_data['id'], 'gemini')
if handoff:
    print(f"📋 HANDOVER from {handoff['from_tool']}: {handoff['goal']}")
EOF
}

# Main execution
CONTEXT=""
if [ -n "$1" ] && [ "$1" != "--no-memory" ]; then
    # Show handoff if pending
    HANDOVER=$(check_handoff 2>/dev/null || true)
    if [ -n "$HANDOVER" ]; then
        echo "$HANDOVER"
        echo ""
    fi
fi

# Run Gemini with the rest of the arguments
shift || true
exec gemini "$@"
