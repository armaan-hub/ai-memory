# AI Memory Hub - Quick Start Guide

## What This Does

**Your memories and work context follow you between AI tools automatically.**

```
Claude Code → OpenCode → Gemini CLI → any AI tool
                    ↓
            All share the same memory database
                    ↓
            No need to re-explain context
```

---

## How It Works (Step by Step)

### The 3 Core Concepts

1. **MCP Server** - A background program that stores memories in SQLite
2. **MCP Client** - Each AI tool (Claude Code, OpenCode, etc.) connects to the server
3. **Handoff Protocol** - Saves your work state so the next tool can continue

### Memory Flow

```
┌─────────────────────────────────────────────────────────────┐
│  AI Tool (e.g., Claude Code)                                │
│                                                             │
│  You say: "remember we decided JWT RS256"                   │
│              ↓                                              │
│  Tool calls: memory_add()                                   │
│              ↓                                              │
│  MCP Client ────────────→ MCP Server (daemon)               │
│                                 ↓                            │
│                            SQLite DB                        │
│                         ~/.claude/mcp-daemon/               │
│                          data/memory.db                    │
└─────────────────────────────────────────────────────────────┘

Next day, different tool:
┌─────────────────────────────────────────────────────────────┐
│  Different AI Tool (e.g., OpenCode)                         │
│                                                             │
│  You say: "what did I decide about JWT?"                    │
│              ↓                                              │
│  Tool calls: memory_search("JWT")                           │
│              ↓                                              │
│  MCP Client ────────────→ MCP Server (same daemon)          │
│                                 ↓                            │
│                            SQLite DB                        │
│                         ← returns your memory               │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup (One Time)

### Step 1: Run the Installation Script

```bash
~/.claude/mcp-daemon/scripts/install.sh
```

This creates the database and sets up everything.

### Step 2: Configure Claude Code (Done Automatically)

The `~/.claude/mcp.json` file tells Claude Code to connect to the MCP server.
Claude Code reads this file when it starts and automatically connects.

### Step 3: For Other Tools

**OpenCode:**
```bash
python3 ~/.claude/mcp-daemon/bridges/opencode-bridge.py
```

**Gemini CLI:**
```bash
source ~/.claude/mcp-daemon/bridges/gemini-memory.sh
```

---

## Daily Usage

### In Claude Code

**Save a memory:**
```
You: "Remember that we're using RS256 for JWT"
Claude: calls memory_add() → saved to database

You: "Remember the deadline is June 15"
Claude: calls memory_add() → saved to database
```

**Search memories:**
```
You: "search my memory for JWT decisions"
Claude: calls memory_search("JWT") → shows results
```

**Hand off to another tool:**
```
You: "handoff save - working on auth module, need to finish JWT"
Claude: calls handoff_save() → saves current state

You close Claude Code, open OpenCode
```

**Continue from handoff in OpenCode:**
```
You: "load pending handoff"
OpenCode: calls handoff_load() → shows "Claude was working on auth, JWT pending"
OpenCode: can continue immediately
```

---

## The Daemon

The MCP server runs as a **daemon** (background process).

**Start it:**
```bash
~/.claude/mcp-daemon/scripts/start-daemon.sh
```

**Check if it's running:**
```bash
~/.claude/mcp-daemon/scripts/status.sh
```

**If Claude Code isn't seeing memories:**
```bash
# Check if daemon is running
pgrep -f "mcp-daemon"
# If not running, start it
~/.claude/mcp-daemon/scripts/start-daemon.sh
```

---

## Manual Commands (When Needed)

### From Any Terminal

```bash
# Add a memory directly
cd ~/.claude/mcp-daemon
python3 -c "
import sys
sys.path.insert(0, '.')
from database import init_database, get_or_create_project, add_memory
init_database()
p = get_or_create_project('/Users/armaan/projects/myproject')
add_memory(p['id'], 'Important decision here', 'general', 8)
print('Memory added!')
"
```

### Check Database Contents

```bash
cd ~/.claude/mcp-daemon
sqlite3 data/memory.db "SELECT * FROM memories LIMIT 10;"
sqlite3 data/memory.db "SELECT * FROM handovers LIMIT 10;"
```

---

## Does It Work Automatically?

**Yes, for Claude Code:**
- Starts automatically when Claude Code starts
- Reads `~/.claude/mcp.json` → connects to daemon
- All tools available without any manual command

**For other tools:**
- Need to run the bridge script once per session
- Or manually connect via stdio

**If things break:**
```bash
# Restart the daemon
pkill -f mcp-daemon
~/.claude/mcp-daemon/scripts/start-daemon.sh
```

---

## File Structure

```
~/.claude/mcp-daemon/
├── server.py           # MCP server (runs as daemon)
├── database.py         # SQLite database operations
├── config.py           # Configuration
├── config.json         # Settings
├── data/
│   └── memory.db       # SQLite database (your memories)
├── bridges/            # Integration for other AI tools
│   ├── opencode-bridge.py
│   ├── gemini-memory.sh
│   └── gemini-simple.sh
├── scripts/
│   ├── install.sh      # One-time setup
│   ├── start-daemon.sh # Start the daemon
│   └── status.sh       # Check if running
└── README.md           # This file

~/.claude/mcp-daemon/
```

---

## Quick Reference

| Need | Command |
|------|---------|
| Check daemon status | `~/.claude/mcp-daemon/scripts/status.sh` |
| Start daemon | `~/.claude/mcp-daemon/scripts/start-daemon.sh` |
| Add memory | (in Claude Code) "remember X" |
| Search memory | (in Claude Code) "search my memory for X" |
| Save handoff | (in Claude Code) "handoff save - working on X" |
| Load handoff | (in new tool) "load pending handoff" |
| View all memories | (in Claude Code) "memory list" |

---

## Troubleshooting

**"Tools not available" in Claude Code:**
1. Check if daemon is running: `~/.claude/mcp-daemon/scripts/status.sh`
2. If not, start it: `~/.claude/mcp-daemon/scripts/start-daemon.sh`
3. Restart Claude Code

**"Connection refused" errors:**
1. Daemon might have stopped
2. Run `start-daemon.sh` again

**Want to start fresh:**
```bash
# Delete database
rm ~/.claude/mcp-daemon/data/memory.db
# Run install again
~/.claude/mcp-daemon/scripts/install.sh
```

---

## Recreate This From Scratch (From GitHub)

```bash
# 1. Clone the repo
git clone https://github.com/armaan-hub/ai-memory.git ~/.claude/mcp-daemon

# 2. Go into directory
cd ~/.claude/mcp-daemon

# 3. Run install
./scripts/install.sh

# 4. For Claude Code, ensure ~/.claude/mcp.json points to this
# (already configured, but verify with:)
cat ~/.claude/mcp.json

# 5. Start daemon
./scripts/start-daemon.sh

# 6. Test
claude
# In Claude Code: "memory add test"
# Then: "memory list" to verify it appears
```

---

## Summary

| Question | Answer |
|----------|--------|
| Does it work automatically? | **Yes** for Claude Code - just use it |
| Do I need to run commands? | **No** for normal use - Claude Code connects automatically |
| What if it stops working? | Run `start-daemon.sh` and restart Claude Code |
| Can other tools use it? | **Yes** - use the bridge scripts |
| Is my data safe? | **Yes** - stored locally in `~/.claude/mcp-daemon/data/memory.db` |

---

**That's it!** Just use Claude Code normally and your memories will be saved automatically.