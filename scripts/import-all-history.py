#!/usr/bin/env python3
"""Import ALL tool histories into MCP Memory Hub."""

import sqlite3
import json
import uuid
import sys
from pathlib import Path
from datetime import datetime

MEMORY_DB = Path.home() / ".claude" / "mcp-daemon" / "data" / "memory.db"
COPILOT_EXPORT = Path.home() / ".claude" / "mcp-daemon" / "copilot-history-export.json"
GEMINI_HISTORY = Path.home() / ".gemini" / "history"
CLAUDE_SESSIONS = Path.home() / ".claude" / "sessions"
JARVIS_MEMORY = Path.home() / ".jarvis" / "memory.json"

def get_project_id(conn, path, name):
    """Get or create project ID."""
    row = conn.execute("SELECT id FROM projects WHERE path = ?", [str(path)]).fetchone()
    if row:
        return row['id']
    pid = str(uuid.uuid4())
    conn.execute("INSERT INTO projects (id, path, name) VALUES (?, ?, ?)", [pid, str(path), name])
    conn.commit()
    return pid

def import_copilot_history(conn, project_id):
    """Import Copilot sessions as memories."""
    if not COPILOT_EXPORT.exists():
        print("⚠️ Copilot export not found")
        return 0

    with open(COPILOT_EXPORT) as f:
        sessions = json.load(f)

    count = 0
    for session in sessions:
        # Create rich summary from turns
        turns = session.get('turns', [])
        if not turns:
            continue

        # Extract key topics from first few turns
        key_topics = []
        for turn in turns[:3]:
            user_msg = turn.get('user', '')[:100]
            if user_msg and not user_msg.startswith('/'):
                key_topics.append(user_msg)

        summary = session.get('summary', '') or key_topics[0] if key_topics else f"Session {session['session_id'][:8]}"

        # Create memory for this session
        content = f"[Copilot Session] {summary}"
        if key_topics:
            content += f"\nTopics: {' | '.join(key_topics[:3])}"
        if session.get('repository'):
            content += f"\nRepository: {session['repository']}"
        content += f"\nTurns: {len(turns)}"

        memory_id = str(uuid.uuid4())
        tags = json.dumps(["copilot", "session", session['session_id'][:8]])

        conn.execute("""
            INSERT INTO memories (id, project_id, content, category, importance, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [memory_id, project_id, content, 'copilot-history', 7, tags])
        count += 1

    conn.commit()
    return count

def import_gemini_history(conn, project_id):
    """Import Gemini CLI history."""
    count = 0

    if not GEMINI_HISTORY.exists():
        print("⚠️ Gemini history not found")
        return 0

    # Gemini stores history in per-project folders
    for project_dir in GEMINI_HISTORY.iterdir():
        if not project_dir.is_dir():
            continue

        conversations_file = project_dir / "conversations.json"
        if conversations_file.exists():
            try:
                with open(conversations_file) as f:
                    conversations = json.load(f)

                for conv in conversations:
                    content = f"[Gemini] {conv.get('title', 'Untitled')}\n"
                    messages = conv.get('messages', [])
                    if messages:
                        # First user message
                        first_msg = next((m for m in messages if m.get('role') == 'user'), None)
                        if first_msg:
                            content += f"First request: {first_msg.get('content', '')[:200]}"

                    memory_id = str(uuid.uuid4())
                    tags = json.dumps(["gemini", project_dir.name])

                    conn.execute("""
                        INSERT INTO memories (id, project_id, content, category, importance, tags)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [memory_id, project_id, content, 'gemini-history', 6, tags])
                    count += 1
            except Exception as e:
                print(f"  Error reading {conversations_file}: {e}")

    conn.commit()
    return count

def import_claude_sessions(conn, project_id):
    """Import Claude Code sessions as memories."""
    count = 0

    if not CLAUDE_SESSIONS.exists():
        print("⚠️ Claude sessions not found")
        return 0

    for session_file in CLAUDE_SESSIONS.glob("*.json"):
        try:
            with open(session_file) as f:
                session = json.load(f)

            # Extract key info
            session_id = session.get('sessionId', session_file.stem)
            cwd = session.get('cwd', 'unknown')
            started = datetime.fromtimestamp(session.get('startedAt', 0)/1000).strftime('%Y-%m-%d') if session.get('startedAt') else 'unknown'

            content = f"[Claude Code] Session {session_id[:8]} at {cwd}\nStarted: {started}"

            memory_id = str(uuid.uuid4())
            tags = json.dumps(["claude-code", "session", session_id[:8]])

            conn.execute("""
                INSERT INTO memories (id, project_id, content, category, importance, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [memory_id, project_id, content, 'claude-history', 6, tags])
            count += 1
        except Exception as e:
            print(f"  Error reading {session_file}: {e}")

    conn.commit()
    return count

def import_jarvis_memory(conn, project_id):
    """Import Jarvis memories."""
    count = 0

    if not JARVIS_MEMORY.exists():
        print("⚠️ Jarvis memory not found")
        return 0

    with open(JARVIS_MEMORY) as f:
        jarvis = json.load(f)

    for fact in jarvis.get('facts', []):
        content = f"[Jarvis] {fact.get('text', '')}"
        category = fact.get('category', 'general')
        source = fact.get('source', 'jarvis')

        memory_id = str(uuid.uuid4())
        tags = json.dumps(["jarvis", source, category])

        conn.execute("""
            INSERT INTO memories (id, project_id, content, category, importance, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [memory_id, project_id, content, f'jarvis-{category}', 5, tags])
        count += 1

    conn.commit()
    return count

def main():
    print("🧠 MCP Memory Hub - Bulk Import")
    print("=" * 50)

    if not MEMORY_DB.exists():
        print(f"❌ Memory database not found: {MEMORY_DB}")
        return

    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row

    # Get/create main project
    home_path = Path.home()
    project_id = get_project_id(conn, home_path, "Universal Memory Hub")

    # Import from each tool
    print("\n📥 Importing from tools...")

    copilot_count = import_copilot_history(conn, project_id)
    print(f"   Copilot sessions: {copilot_count} memories")

    gemini_count = import_gemini_history(conn, project_id)
    print(f"   Gemini conversations: {gemini_count} memories")

    claude_count = import_claude_sessions(conn, project_id)
    print(f"   Claude Code sessions: {claude_count} memories")

    jarvis_count = import_jarvis_memory(conn, project_id)
    print(f"   Jarvis facts: {jarvis_count} memories")

    # Count total
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    print(f"\n✅ Total memories now in database: {total}")
    print("\n📊 By category:")
    for row in conn.execute("SELECT category, COUNT(*) as c FROM memories GROUP BY category ORDER BY c DESC"):
        print(f"   {row['category']}: {row['c']}")

    conn.close()

if __name__ == "__main__":
    main()