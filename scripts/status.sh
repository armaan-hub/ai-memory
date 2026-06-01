#!/bin/bash
# Check MCP Memory Hub status

PID_FILE="$HOME/.claude/mcp-daemon/mcp-daemon.pid"
LOG_FILE="$HOME/.claude/mcp-daemon/logs/mcp-daemon.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🟢 MCP Memory Hub is RUNNING"
        echo "   PID: $PID"
        echo "   Log: $LOG_FILE"

        # Show recent log entries
        echo ""
        echo "Recent log entries:"
        tail -5 "$LOG_FILE" 2>/dev/null || echo "(no entries)"

        exit 0
    fi
fi

echo "🔴 MCP Memory Hub is NOT running"
echo ""
echo "To start: ~/.claude/mcp-daemon/scripts/start-daemon.sh"
