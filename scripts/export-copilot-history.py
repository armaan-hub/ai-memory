#!/usr/bin/env python3
"""Extract all GitHub Copilot history and add to MCP Memory Hub."""

import sqlite3
import sys
import json
from pathlib import Path

COPILOT_DB = Path.home() / ".copilot" / "session-store.db"
OUTPUT_FILE = Path.home() / ".claude" / "mcp-daemon" / "copilot-history-export.json"

def extract_copilot_history():
    """Extract all Copilot conversations."""
    if not COPILOT_DB.exists():
        print(f"❌ Copilot database not found: {COPILOT_DB}")
        return []

    conn = sqlite3.connect(str(COPILOT_DB))
    conn.row_factory = sqlite3.Row

    # Get all sessions with their turns
    sessions = conn.execute("""
        SELECT id, cwd, repository, host_type, branch, summary, created_at, updated_at
        FROM sessions
        ORDER BY updated_at DESC
    """).fetchall()

    all_history = []

    for session in sessions:
        session_id = session['id']

        # Get turns for this session
        turns = conn.execute("""
            SELECT turn_index, user_message, assistant_response, timestamp
            FROM turns
            WHERE session_id = ?
            ORDER BY turn_index
        """, [session_id]).fetchall()

        session_data = {
            'session_id': session_id,
            'summary': session['summary'],
            'cwd': session['cwd'],
            'repository': session['repository'],
            'created_at': session['created_at'],
            'updated_at': session['updated_at'],
            'turns': []
        }

        for turn in turns:
            if turn['user_message']:
                session_data['turns'].append({
                    'index': turn['turn_index'],
                    'user': turn['user_message'],
                    'assistant': turn['assistant_response'],
                    'timestamp': turn['timestamp']
                })

        if session_data['turns']:  # Only add sessions with content
            all_history.append(session_data)

    conn.close()
    return all_history

def main():
    print("📦 Extracting GitHub Copilot history...")

    history = extract_copilot_history()

    if not history:
        print("❌ No history found")
        return

    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(history, f, indent=2)

    print(f"✅ Extracted {len(history)} sessions")

    # Count total turns
    total_turns = sum(len(s['turns']) for s in history)
    print(f"📝 Total conversation turns: {total_turns}")

    print(f"\n💾 Saved to: {OUTPUT_FILE}")
    print(f"\nTo add to memory, run in Claude Code:")
    print(f"  memory_add(content='Imported {len(history)} sessions from GitHub Copilot', category='history-import')")

if __name__ == '__main__':
    main()