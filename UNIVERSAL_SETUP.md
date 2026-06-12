# MCP Memory Hub - Universal Setup Guide

## Complete Integration for Claude Code, GitHub Copilot, Gemini CLI, Jarvis, and OpenCode

---

## What This Does

**One shared memory database that ALL AI tools can access.**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Claude Code ←→ Memory ←→ GitHub Copilot                   │
│        ↓              ↓              ↓                      │
│   Gemini CLI ←→ Memory ←→ OpenCode                          │
│        ↓              ↓                                      │
│     Jarvis ←→ Memory ←→ (All tools share context)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Setup (Do This Once)

### 1. Clone or Update the Repository

```bash
# If you have it already
cd ~/.claude/mcp-daemon
git pull

# If starting fresh
git clone https://github.com/armaan-hub/ai-memory.git ~/.claude/mcp-daemon
```

### 2. Install & Start

```bash
cd ~/.claude/mcp-daemon
./scripts/install.sh
./scripts/start-daemon.sh

# Verify it's running
./scripts/status.sh
```

---

## Claude Code (Automatic)

✅ **Already configured** - Claude Code reads `~/.claude/mcp.json`

**Use it:**
```
You: "remember we decided to use RS256 for JWT"
Claude: memory_add() → saved

You: "search my memory for JWT"
Claude: memory_search("JWT") → shows results
```

**Direct commands:**
```
/memory add "observation"
/memory search "query"
/memory list
/handoff save
/handoff load
```

---

## GitHub Copilot (Already Connected)

✅ **Already configured** - Copilot already has 242 sessions stored

**Search your Copilot history:**
```
You: "search my memory for Jarvis"
You: "search my memory for wallpaper design"
```

**What was imported:**
- Jarvis AI Desktop work (wallpaper/HUD design)
- Voice recognition issues
- MCP server integration problems
- Skills creation (AI Council, Writing Skills)
- TMUX vs Zellij discussions

---

## Gemini CLI

### Option 1: Use the Shell Wrapper (Recommended)

```bash
# Add to your shell (add to ~/.zshrc)
source ~/.claude/mcp-daemon/bridges/gemini-memory-bridge.sh

# Then in Gemini CLI, use commands:
memory add "observation"
memory search "query"
memory list
memory handoff-save "working on X"
memory handoff-load
```

**Shortcuts:**
```bash
m-add "text"
m-search "query"
m-list
m-handoff "context"
m-resume  # load pending handoff
```

### Option 2: Direct Python Client

```bash
# From any terminal
python3 ~/.claude/mcp-daemon/memory_client.py add "observation"
python3 ~/.claude/mcp-daemon/memory_client.py search "Jarvis"
python3 ~/.claude/mcp-daemon/memory_client.py status
```

### Option 3: Copy to Local Bin

```bash
cp ~/.claude/mcp-daemon/memory_client.py ~/.local/bin/memory-client.py

# Then use anywhere
memory-client.py add "text"
memory-client.py search "query"
```

---

## Jarvis (Voice AI Assistant)

✅ **Already integrated** - `~/.jarvis/jarvis_memory.py` is connected

**In Jarvis, just say:**
```
"Remember that I prefer dark mode"
"Search my memory for wallpaper designs"
"What did I work on with Copilot?"
```

**How it works:**
- Jarvis now uses the shared memory database
- Memories added in Jarvis are visible in Claude Code
- Memories from Claude Code/Gemini are visible to Jarvis

**Check it works:**
```bash
cd ~/.jarvis && python3 jarvis_memory.py
```

Should show:
```
🧠 Jarvis Memory Hub Integration
✅ Connected to Memory Hub
   Memories: 7
   Pending Handoffs: 0
✅ Jarvis memory integration working!
```

---

## OpenCode

### Option 1: Use the Bridge

```bash
# Run the bridge script before starting OpenCode
~/.claude/mcp-daemon/bridges/opencode-bridge.py

# Then start OpenCode
opencode
```

### Option 2: Use Memory Client

```bash
python3 ~/.local/bin/memory-client.py add "text"
python3 ~/.local/bin/memory-client.py search "query"
```

---

## Universal Handoff (Switch Between Tools)

### Save Handoff (Before Switching Tools)

```bash
# In Claude Code
memory handoff-save "Working on auth module, JWT refresh incomplete"

# Or via memory-client
memory-client.py handoff-save "Working on X"
```

### Load Handoff (In Next Tool)

```bash
# In Gemini CLI
memory handoff-load

# Or via memory-client
memory-client.py handoff-load
```

---

## Quick Reference Commands

### All Tools

| Task | Command |
|------|---------|
| Add memory | `memory add "text"` or `m-add "text"` |
| Search | `memory search "query"` or `m-search "query"` |
| List all | `memory list` or `m-list` |
| Status | `memory status` or `m-status` |
| Save handoff | `memory handoff-save "context"` or `m-handoff "context"` |
| Load handoff | `memory handoff-load` or `m-resume` |

### Specific Tools

**Claude Code:**
```
/memory add "observation"
/memory search "query"
/memory list
/handoff save
/handoff load
```

**Gemini CLI:**
```
source ~/.claude/mcp-daemon/bridges/gemini-memory-bridge.sh
memory add "text"
memory search "query"
```

**Jarvis (Voice):**
```
"Remember that [fact]"
"What do I have in memory about [topic]?"
"Search my memory for [topic]"
```

**OpenCode:**
```
# Before starting
~/.claude/mcp-daemon/bridges/opencode-bridge.py

# Then use memory commands
```

---

## Troubleshooting

### "Memory database not found"

```bash
# Start the daemon
~/.claude/mcp-daemon/scripts/start-daemon.sh

# Or run manually
cd ~/.claude/mcp-daemon && python3 server.py &
```

### "Tools not working in Claude Code"

1. Check daemon is running: `~/.claude/mcp-daemon/scripts/status.sh`
2. If not, start it: `./scripts/start-daemon.sh`
3. Restart Claude Code

### "Jarvis not seeing memories"

```bash
# Test Jarvis integration
cd ~/.jarvis && python3 jarvis_memory.py

# If error, restart Jarvis
```

### Check All Status

```bash
# Memory Hub status
~/.claude/mcp-daemon/scripts/status.sh

# Test memory client
python3 ~/.local/bin/memory-client.py status

# Test Jarvis
cd ~/.jarvis && python3 jarvis_memory.py
```

---

## File Locations

| Component | Location |
|-----------|----------|
| MCP Server | `~/.claude/mcp-daemon/server.py` |
| Database | `~/.claude/mcp-daemon/data/memory.db` |
| Memory Client | `~/.claude/mcp-daemon/memory_client.py` |
| Gemini Bridge | `~/.claude/mcp-daemon/bridges/gemini-memory-bridge.sh` |
| OpenCode Bridge | `~/.claude/mcp-daemon/bridges/opencode-bridge.py` |
| Jarvis Integration | `~/.jarvis/jarvis_memory.py` |
| Claude Code Config | `~/.claude/mcp.json` |

---

## What Gets Synced

**All of these share the same memory database:**

| Tool | What gets stored |
|------|-----------------|
| Claude Code | Observations, decisions, code changes |
| GitHub Copilot | 242 historical sessions (imported) |
| Gemini CLI | Conversations, research |
| Jarvis | Voice interactions, preferences |
| OpenCode | Development work |
| Manual | Any `memory add` command |

---

## Next Steps

1. **Test it now:**
   ```bash
   # Check all is running
   ~/.claude/mcp-daemon/scripts/status.sh
   
   # Add a test memory
   memory-client.py add "MCP Memory Hub is now working for all tools"
   
   # Search it
   memory-client.py search "MCP Memory Hub"
   ```

2. **In Claude Code:**
   ```
   "search my memory for test"
   ```

3. **In Jarvis (if running):**
   ```
   "Search my memory for MCP Memory Hub"
   ```

All should find the same memory!

---

**Questions?** Just ask in Claude Code - it has the full memory context. 🎯