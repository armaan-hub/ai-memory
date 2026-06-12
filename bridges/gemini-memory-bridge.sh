#!/bin/bash
# Gemini CLI Memory Bridge
# Usage: source gemini-memory.sh
# Then use: memory add "text", memory search "query", etc.

MEMORY_CLIENT="$HOME/.claude/mcp-daemon/memory_client.py"
PYTHON_CMD="python3"

# Check if memory client exists
if [ ! -f "$MEMORY_CLIENT" ]; then
    echo "❌ Memory client not found. Run: cp ~/.claude/mcp-daemon/memory_client.py ~/.local/bin/"
    return 1
fi

# Memory functions
memory() {
    local cmd="$1"
    shift
    case "$cmd" in
        add)
            $PYTHON_CMD "$MEMORY_CLIENT" add "$@"
            ;;
        search)
            $PYTHON_CMD "$MEMORY_CLIENT" search "$@"
            ;;
        list)
            $PYTHON_CMD "$MEMORY_CLIENT" list
            ;;
        status)
            $PYTHON_CMD "$MEMORY_CLIENT" status
            ;;
        handoff-save)
            $PYTHON_CMD "$MEMORY_CLIENT" handoff-save "$@"
            ;;
        handoff-load)
            $PYTHON_CMD "$MEMORY_CLIENT" handoff-load
            ;;
        *)
            echo "Usage: memory <add|search|list|status|handoff-save|handoff-load> [args]"
            ;;
    esac
}

# Short aliases
m-add() { memory add "$@"; }
m-search() { memory search "$@"; }
m-list() { memory list; }
m-status() { memory status; }
m-handoff() { memory handoff-save "$@"; }
m-resume() { memory handoff-load; }

echo "✅ MCP Memory Hub loaded in Gemini CLI"
echo "   Commands: memory add|search|list|status|handoff-save|handoff-load"
echo "   Shortcuts: m-add, m-search, m-list, m-status, m-handoff, m-resume"
echo ""
echo "   Example: memory search \"Jarvis\""