#!/bin/bash
# Start MCP Memory Hub Daemon

DAEMON_DIR="$HOME/.claude/mcp-daemon"
SERVER="$DAEMON_DIR/server.py"
PID_FILE="$DAEMON_DIR/mcp-daemon.pid"
LOG_FILE="$DAEMON_DIR/logs/mcp-daemon.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "MCP Memory Hub is already running (PID: $OLD_PID)"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Ensure directories exist
mkdir -p "$DAEMON_DIR/data"
mkdir -p "$DAEMON_DIR/logs"

# Start the daemon
echo "Starting MCP Memory Hub..."
nohup python3 "$SERVER" >> "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

# Wait a moment and verify
sleep 1
if kill -0 "$PID" 2>/dev/null; then
    echo "✅ MCP Memory Hub started (PID: $PID)"
    echo "📝 Log: $LOG_FILE"
else
    echo "❌ Failed to start MCP Memory Hub"
    rm -f "$PID_FILE"
    exit 1
fi
