#!/usr/bin/env python3
"""
Universal AI History Importer
Imports ALL conversation history from ALL AI tools into MCP Memory Hub.

Sources:
- Claude Code: ~/.claude/history.jsonl (~943)
- Claude Code Projects: ~/.claude/projects/*/
- Gemini CLI: ~/.gemini/history.jsonl
- OpenCode: ~/.local/state/opencode/prompt-history.jsonl
- GitHub Copilot: ~/.copilot/session-store.db
- Jarvis: ~/.jarvis/memory.json

Usage:
    python3 import-all-ai-history.py
"""

import sqlite3
import json
import uuid
import sys
from pathlib import Path
from datetime import datetime

# Paths
MEMORY_DB = Path.home() / ".claude" / "mcp-daemon" / "data" / "memory.db"
CLAUDE_HISTORY = Path.home() / ".claude" / "history.jsonl"
GEMINI_HISTORY = Path.home() / ".gemini" / "history.jsonl"
GEMINI_ANTIGRAVITY = Path.home() / ".gemini" / "antigravity-cli" / "history.jsonl"
OPENCODE_HISTORY = Path.home() / ".local" / "state" / "opencode" / "prompt-history.jsonl"
COPILOT_DB = Path.home() / ".copilot" / "session-store.db"
JARVIS_MEMORY = Path.home() / ".jarvis" / "memory.json"

def get_connection():
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row
    return conn

def get_or_create_project(conn, path, name):
    normalized = str(Path(path).resolve())
    row = conn.execute("SELECT id FROM projects WHERE path = ?", [normalized]).fetchone()
    if row:
        return row['id']

    project_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO projects (id, path, name) VALUES (?, ?, ?)",
        [project_id, normalized, name]
    )
    conn.commit()
    return project_id

def add_memory(conn, project_id, content, category, importance=5, tags=None):
    memory_id = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])

    conn.execute("""
        INSERT INTO memories (id, project_id, content, category, importance, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [memory_id, project_id, content, category, importance, tags_json])

    return memory_id

def import_claude_history(conn, project_id):
    """Import Claude Code history.jsonl"""
    count = 0
    if not CLAUDE_HISTORY.exists():
        print(f"  ⚠️ Claude history not found: {CLAUDE_HISTORY}")
        return 0

    with open(CLAUDE_HISTORY, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                # Check display field (Claude Code format)
                user_msg = entry.get('display', entry.get('message', entry.get('user', '')))
                if user_msg and len(str(user_msg)) > 10:
                    content = f"[Claude Code] {str(user_msg)[:500]}"
                    add_memory(conn, project_id, content, 'claude-history', 5)
                    count += 1
            except:
                continue

    conn.commit()
    return count

def import_gemini_history(conn, project_id):
    """Import Gemini CLI history"""
    count = 0

    for hist_file in [GEMINI_ANTIGRAVITY]:
        if not hist_file.exists():
            continue

        with open(hist_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if isinstance(entry, dict):
                        user_msg = entry.get('display', entry.get('user', entry.get('prompt', entry.get('message', ''))))
                        if user_msg and len(str(user_msg)) > 10:
                            content = f"[Gemini] {str(user_msg)[:500]}"
                            add_memory(conn, project_id, content, 'gemini-history', 5)
                            count += 1
                except:
                    continue

        conn.commit()
    return count

def import_opencode_history(conn, project_id):
    """Import OpenCode history"""
    count = 0
    if not OPENCODE_HISTORY.exists():
        print(f"  ⚠️ OpenCode history not found: {OPENCODE_HISTORY}")
        return 0

    with open(OPENCODE_HISTORY, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if isinstance(entry, dict):
                    prompt = entry.get('input', entry.get('prompt', entry.get('text', '')))
                    if prompt and len(str(prompt)) > 10:
                        content = f"[OpenCode] {str(prompt)[:500]}"
                        add_memory(conn, project_id, content, 'opencode-history', 5)
                        count += 1
            except:
                continue

    conn.commit()
    return count

def import_copilot_sessions(conn):
    """Import GitHub Copilot sessions"""
    count = 0
    if not COPILOT_DB.exists():
        print(f"  ⚠️ Copilot DB not found: {COPILOT_DB}")
        return 0

    conn_cop = sqlite3.connect(str(COPILOT_DB))
    conn_cop.row_factory = sqlite3.Row

    sessions = conn_cop.execute("""
        SELECT id, summary, cwd, repository, created_at, updated_at
        FROM sessions ORDER BY updated_at DESC
    """).fetchall()

    # Get general project
    general_project = get_or_create_project(conn, str(Path.home()), "All Projects")

    for session in sessions:
        if session['summary']:
            content = f"[Copilot] {session['summary'][:500]}"
            add_memory(conn, general_project, content, 'copilot-history', 6)
            count += 1

    conn.commit()
    conn_cop.close()
    return count

def import_jarvis_memory(conn):
    """Import Jarvis memory.json facts"""
    count = 0
    if not JARVIS_MEMORY.exists():
        print(f"  ⚠️ Jarvis memory not found: {JARVIS_MEMORY}")
        return 0

    jarvis_project = get_or_create_project(conn, str(Path.home() / ".jarvis"), "Jarvis AI")

    with open(JARVIS_MEMORY, 'r') as f:
        data = json.load(f)
        facts = data.get('facts', [])

        for fact in facts:
            if isinstance(fact, dict):
                text = fact.get('text', '')
                category = fact.get('category', 'jarvis')
            else:
                text = str(fact)
                category = 'jarvis'

            if text and len(text) > 5:
                content = f"[Jarvis] {text[:500]}"
                add_memory(conn, jarvis_project, content, f'jarvis-{category}', 7)
                count += 1

    conn.commit()
    return count

def import_claude_projects(conn):
    """Import Claude Code project sessions"""
    count = 0
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        return 0

    for project_path in projects_dir.iterdir():
        if not project_path.is_dir():
            continue

        project_name = project_path.name
        project_id = get_or_create_project(conn, str(project_path), project_name)

        # Look for session files
        for session_file in project_path.glob("*.jsonl"):
            try:
                with open(session_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if isinstance(entry, dict):
                                msg = entry.get('message', entry.get('text', entry.get('user', '')))
                                if msg and len(str(msg)) > 10:
                                    content = f"[Claude-{project_name}] {str(msg)[:500]}"
                                    add_memory(conn, project_id, content, 'claude-history', 5)
                                    count += 1
                        except:
                            continue
            except:
                continue

        conn.commit()
    return count

def main():
    print("=" * 60)
    print("🧠 Universal AI History Importer")
    print("=" * 60)
    print()

    if not MEMORY_DB.exists():
        print("❌ Memory database not found. Run install.sh first.")
        return

    conn = get_connection()

    # Get starting count
    start_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    print(f"📊 Starting memories: {start_count}")
    print()

    # Import from all sources
    sources = [
        ("Claude Code history.jsonl", lambda: import_claude_history(conn, get_or_create_project(conn, str(Path.home()), "Claude Code"))),
        ("Claude Code projects", lambda: import_claude_projects(conn)),
        ("Gemini CLI history", lambda: import_gemini_history(conn, get_or_create_project(conn, str(Path.home()), "Gemini CLI"))),
        ("OpenCode history", lambda: import_opencode_history(conn, get_or_create_project(conn, str(Path.home()), "OpenCode"))),
        ("GitHub Copilot sessions", lambda: import_copilot_sessions(conn)),
        ("Jarvis memory", lambda: import_jarvis_memory(conn)),
    ]

    total_imported = 0

    for name, func in sources:
        print(f"📥 Importing {name}...")
        try:
            count = func()
            print(f"  ✅ Imported {count} entries")
            total_imported += count
        except Exception as e:
            print(f"  ❌ Error: {e}")

    conn.commit()
    conn.close()

    # Final count
    conn = get_connection()
    end_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()

    print()
    print("=" * 60)
    print(f"✅ IMPORT COMPLETE!")
    print(f"   Imported: {total_imported} new entries")
    print(f"   Total memories: {start_count} → {end_count}")
    print()
    print(f"📊 View at: http://localhost:5555")
    print("=" * 60)

if __name__ == "__main__":
    main()