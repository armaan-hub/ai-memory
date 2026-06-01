#!/bin/bash
# Install script for MCP Memory Hub

set -e

echo "🔧 Installing MCP Memory Hub..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Install MCP package
echo "📦 Installing MCP package..."
pip3 install --quiet "mcp>=1.0.0"

# Create directories
mkdir -p "$HOME/.claude/mcp-daemon/data"
mkdir -p "$HOME/.claude/mcp-daemon/logs"

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/mcp-daemon')
from database import init_database
init_database()
print('Database initialized successfully')
"

# Create Claude Code MCP config
echo "🔗 Creating Claude Code MCP config..."
mkdir -p "$HOME/.claude"
cat > "$HOME/.claude/mcp.json" << 'EOF'
{
  "mcpServers": {
    "memory-hub": {
      "command": "python3",
      "args": ["/Users/armaan/.claude/mcp-daemon/server.py"]
    }
  }
}
EOF

# Add to shell profile
SHELL_RC="$HOME/.zshrc"
if [ -f "$SHELL_RC" ]; then
    if ! grep -q "mcp-daemon" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# MCP Memory Hub" >> "$SHELL_RC"
        echo "export PATH=\"$HOME/.claude/mcp-daemon/scripts:\$PATH\"" >> "$SHELL_RC"
        echo "alias memory-status='python3 ~/.claude/mcp-daemon/scripts/status.sh'" >> "$SHELL_RC"
        echo "✅ Added to $SHELL_RC"
    fi
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the daemon:"
echo "  ~/.claude/mcp-daemon/scripts/start-daemon.sh"
echo ""
echo "To use with Claude Code:"
echo "  Claude Code will automatically connect via mcp.json"
echo ""
echo "To use with OpenCode:"
echo "  ~/.claude/mcp-daemon/scripts/opencode-memory.sh"
echo ""
