#!/bin/bash
# Start MCP Memory Hub Dashboard
# Opens a web interface to view all memories

cd ~/.claude/mcp-daemon

# Check if dashboard is already running
if curl -s http://localhost:5555 > /dev/null 2>&1; then
    echo "🧠 MCP Memory Hub Dashboard is already running"
    echo "🌐 http://localhost:5555"
else
    echo "🧠 Starting MCP Memory Hub Dashboard..."
    nohup python3 memory-dashboard.py > logs/dashboard.log 2>&1 &
    sleep 2

    if curl -s http://localhost:5555 > /dev/null 2>&1; then
        echo ""
        echo "✅ Dashboard is running!"
        echo ""
        echo "🌐 Open in browser:"
        echo "   http://localhost:5555"
        echo ""
        echo "📊 You'll see:"
        echo "   - All memories from Claude Code, Copilot, Gemini, Jarvis, OpenCode"
        echo "   - Search functionality"
        echo "   - Pending handoffs"
        echo "   - Categories and projects"
    else
        echo "❌ Failed to start dashboard"
        echo "Check logs: ~/.claude/mcp-daemon/logs/dashboard.log"
    fi
fi