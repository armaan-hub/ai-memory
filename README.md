# MCP Memory Hub

**Universal Memory System for AI Development Tools**

A persistent memory daemon that enables Claude Code, OpenCode, Gemini CLI, and other MCP-compatible AI tools to share context, track project history, and hand off tasks seamlessly.

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         MCP Memory Hub               │
                    │   ┌─────────────────────────────┐   │
                    │   │     SQLite Database         │   │
                    │   │  ┌─────┐ ┌──────┐ ┌────┐   │   │
                    │   │  │Memories│ │Handoffs│ │Projects│ │   │
                    │   │  └─────┘ └──────┘ └────┘   │   │
                    │   └─────────────────────────────┘   │
                    └──────────────┬──────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
    ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
    │Claude Code  │        │  OpenCode   │        │ Gemini CLI  │
    │             │        │             │        │             │
    └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
           │                       │                       │
           └───────────────────────┴───────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Handoff System    │
                    │  (Cross-tool state)  │
                    └─────────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **MCP Daemon** | stdio-based MCP server process running persistently |
| **SQLite Database** | Local file storage for memories, handoffs, and project metadata |
| **MCP Clients** | Claude Code, OpenCode, Gemini CLI - any tool using the MCP protocol |
| **Bridge Scripts** | Per-tool connection scripts for non-MCP-native tools |

---

## Features

### Memory Tools

| Tool | Description |
|------|-------------|
| `memory_add` | Store observations, decisions, and context with categories and importance |
| `memory_search` | Full-text search across all memories |
| `memory_recent` | Retrieve recent memories for quick context |
| `memory_list` | List all memories for a project |
| `memory_compact` | Generate compressed summary at 3 tiers (light/medium/deep) |

### Handoff Tools

| Tool | Description |
|------|-------------|
| `handoff_save` | Save current state before switching tools |
| `handoff_load` | Load pending handoff when starting in a new tool |
| `handoff_complete` | Mark handoff as done |
| `handoff_status` | View all pending handoffs |

### Project Tools

| Tool | Description |
|------|-------------|
| `project_list` | List all tracked projects |
| `context_inject` | Get formatted context string for injection |

---

## Quick Start

### 1. Installation

```bash
# Ensure you're in the mcp-daemon directory
cd ~/.claude/mcp-daemon

# The daemon is ready to run - no installation needed
```

### 2. Starting the Daemon

**Option A: Direct Python**
```bash
python3 ~/.claude/mcp-daemon/server.py
```

**Option B: Via MCP config (Claude Code)**
Add to your MCP settings file:

```json
{
  "mcpServers": {
    "memory-hub": {
      "command": "python3",
      "args": ["/Users/armaan/.claude/mcp-daemon/server.py"]
    }
  }
}
```

### 3. Using with Claude Code

Once configured, use the tools directly in your conversation:

```
/memory_add "The database schema uses UUID primary keys"
/memory_search "database schema"
/handoff_save context="Migrated auth to JWT" goal="Verify endpoints" to_tool="OpenCode"
```

---

## Usage Examples

### Adding Memories

```javascript
// MCP tool call
{
  "name": "memory_add",
  "arguments": {
    "content": "Refactored user service to use dependency injection",
    "category": "architecture",
    "importance": 8,
    "tags": ["refactor", "di", "users"]
  }
}
```

### Searching Memories

```javascript
// Find all memories about authentication
{
  "name": "memory_search",
  "arguments": {
    "query": "authentication JWT oauth",
    "project": "my-project",
    "limit": 10
  }
}
```

### Saving a Handoff

```javascript
// Save state before switching tools
{
  "name": "handoff_save",
  "arguments": {
    "context": "Completed user registration endpoint. Need to add validation middleware.",
    "goal": "Add input validation to /api/users POST endpoint",
    "project": "backend-api",
    "to_tool": "Claude Code"
  }
}
```

### Loading a Handoff

```javascript
// When starting in a new tool
{
  "name": "handoff_load",
  "arguments": {
    "project": "backend-api"
  }
}
```

### Context Injection

```javascript
// Get all context for injection
{
  "name": "context_inject",
  "arguments": {
    "project": "backend-api",
    "style": "detailed"
  }
}
```

### Memory Compaction

```javascript
// Generate summary
{
  "name": "memory_compact",
  "arguments": {
    "tier": "medium",
    "project": "backend-api"
  }
}
```

---

## Configuration

Edit `~/.claude/mcp-daemon/config.json`:

```json
{
  "version": "1.0",
  "database_path": "~/.claude/mcp-daemon/data/memory.db",
  "log_level": "INFO",
  "log_file": "~/.claude/mcp-daemon/logs/mcp-daemon.log",
  
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
```

### Config Options

| Option | Default | Description |
|--------|---------|-------------|
| `database_path` | `~/.claude/mcp-daemon/data/memory.db` | SQLite database location |
| `log_level` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `log_file` | `~/.claude/mcp-daemon/logs/mcp-daemon.log` | Log file path |
| `max_recent_items` | `50` | Max items in recent memories |
| `max_search_results` | `20` | Max search results returned |
| `handoff_retention_hours` | `72` | Hours before handoffs expire |

---

## How the Handoff System Works

```
Tool A (Claude Code)                    Tool B (OpenCode)
      │                                       │
      │  1. /handoff_save                    │
      │     context="state"                  │
      │     goal="task"                      │
      │     to_tool="OpenCode"               │
      │ ─────────────────────────────────────►│
      │     [Saves to SQLite]                 │
      │                                       │
      │  2. Exit Claude Code                  │
      │  3. Start OpenCode                    │
      │                                       │
      │                                       │  4. /handoff_load
      │                                       │     [Reads from SQLite]
      │                                       │     Shows context + goal
      │                                       │
      │                                       │  5. Complete task
      │                                       │
      │                                       │  6. /handoff_complete
      │                                       │     [Marks done]
```

### Handoff States

| State | Description |
|-------|-------------|
| `pending` | Saved, waiting for target tool |
| `loaded` | Target tool has read it |
| `completed` | Task done, archived |
| `expired` | Not loaded within retention period |

---

## Database Schema

The SQLite database (`memory.db`) contains:

### memories
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | UUID primary key |
| project_id | INTEGER | Foreign key to projects |
| content | TEXT | Memory content |
| category | TEXT | general/architecture/bug/feature/decision/context/todo |
| importance | INTEGER | 1-10 scale |
| tags | TEXT | JSON array |
| created_at | TIMESTAMP | Creation time |

### handovers
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | UUID primary key |
| project_id | INTEGER | Foreign key to projects |
| from_tool | TEXT | Source tool name |
| to_tool | TEXT | Target tool name |
| context | TEXT | State to transfer |
| goal | TEXT | Task description |
| status | TEXT | pending/loaded/completed/expired |
| created_at | TIMESTAMP | When saved |
| completed_at | TIMESTAMP | When completed |

### projects
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PK |
| name | TEXT | Project name |
| path | TEXT | Working directory |
| created_at | TIMESTAMP | First access |

---

## Troubleshooting

### Daemon Won't Start

```bash
# Check Python version
python3 --version  # Must be 3.8+

# Verify database directory exists
mkdir -p ~/.claude/mcp-daemon/data

# Check permissions
ls -la ~/.claude/mcp-daemon/

# Run with debug logging
python3 server.py 2>&1 | head -50
```

### Client Can't Connect

```bash
# Verify daemon is running (stdio mode - no network port)
# Check logs
tail -f ~/.claude/mcp-daemon/logs/mcp-daemon.log

# Verify MCP config is correct
# For Claude Code: ~/.claude/settings.json
```

### Handoff Not Loading

```bash
# Check handoff status
# Use handoff_status tool to see pending handoffs

# Verify project name matches (case-sensitive)
# Check handoff_retention_hours hasn't passed
```

### Memory Search Returns Nothing

```bash
# Verify memories exist
# Use memory_list to see all memories

# Check project detection is working
# Try explicit project parameter
```

### Database Corruption

```bash
# Backup current database
cp ~/.claude/mcp-daemon/data/memory.db ~/.claude/mcp-daemon/data/memory.db.backup

# Reset database (will lose all data)
rm ~/.claude/mcp-daemon/data/memory.db
python3 ~/.claude/mcp-daemon/server.py  # Reinitializes
```

---

## Bridge Scripts

The `bridges/` directory contains connection scripts for non-MCP-native tools:

```
bridges/
├── opencode-bridge.sh    # Connect OpenCode to MCP Memory Hub
├── gemini-bridge.py      # Connect Gemini CLI
└── generic-bridge.sh     # Template for other tools
```

---

## Logs

View logs at `~/.claude/mcp-daemon/logs/mcp-daemon.log`:

```bash
# Real-time monitoring
tail -f ~/.claude/mcp-daemon/logs/mcp-daemon.log

# Last 100 lines
tail -100 ~/.claude/mcp-daemon/logs/mcp-daemon.log

# Errors only
grep ERROR ~/.claude/mcp-daemon/logs/mcp-daemon.log
```

---

## Architecture Details

### Transport Protocol

The daemon uses MCP over stdio (standard input/output):

1. Client sends JSON-RPC request to stdin
2. Daemon reads, processes, writes response to stdout
3. Protocol version: `2024-11-05`

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "memory_add",
    "arguments": {
      "content": "..."
    }
  }
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Memory added: abc123..."
      }
    ]
  }
}
```

### Concurrency

- Single-threaded async server (asyncio)
- Sequential request processing (MCP stdio requirement)
- SQLite with WAL mode for concurrent reads

---

## Files Structure

```
~/.claude/mcp-daemon/
├── server.py           # Main MCP server entry point
├── database.py         # SQLite operations
├── config.py           # Configuration loader
├── config.json         # Default configuration
├── test-server.py      # Testing utilities
├── pyproject.toml      # Project metadata
├── README.md           # This file
├── tools/              # (Reserved for future modular tools)
├── utils/              # Utility modules
├── bridges/            # Cross-tool bridge scripts
├── data/               # SQLite database location
└── logs/               # Log files
```

---

## Extending the Hub

### Adding a New Tool

1. Create bridge script in `bridges/` directory
2. Connect to daemon via stdio
3. Send JSON-RPC requests matching MCP protocol

### Custom Memory Categories

Edit `server.py` - add to the `category` enum in `memory_add` schema.

### Compaction Tiers

Modify `config.json` `compact_tiers` to adjust summary sizes.

---

## License

MIT License - See project repository for details.