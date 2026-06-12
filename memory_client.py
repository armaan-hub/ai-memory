#!/usr/bin/env python3
"""
MCP Memory Hub Client
Universal memory access for Claude Code, OpenCode, Gemini CLI, Jarvis, and any AI tool.

Usage:
    from memory_client import MemoryHub
    hub = MemoryHub()
    hub.add("Remember this decision")
    hub.search("Jarvis")
    hub.handoff_save("Working on auth module")
"""

import sqlite3
import json
import sys
import uuid
from pathlib import Path
from typing import Optional, List, Dict

# Configuration
MEMORY_DB = Path.home() / ".claude" / "mcp-daemon" / "data" / "memory.db"


class MemoryHub:
    """Universal memory client for all AI tools."""

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else MEMORY_DB
        self._ensure_db()
        self._ensure_project()

    def _ensure_db(self):
        """Ensure database exists."""
        if not self.db_path.exists():
            # Try to initialize from mcp-daemon
            sys.path.insert(0, str(Path.home() / ".claude" / "mcp-daemon"))
            try:
                from database import init_database
                init_database()
            except:
                pass

    def _ensure_project(self):
        """Ensure current project is registered."""
        cwd = str(Path.cwd())
        self.project_id = self._get_or_create_project(cwd)
        return self.project_id

    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(str(self.db_path))

    def _get_or_create_project(self, path: str) -> str:
        """Get or create project."""
        normalized = str(Path(path).resolve())

        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT id FROM projects WHERE path = ?", [normalized]
        ).fetchone()

        if row:
            conn.close()
            return row['id']

        project_id = str(uuid.uuid4())
        name = Path(normalized).name
        conn.execute(
            "INSERT INTO projects (id, path, name) VALUES (?, ?, ?)",
            [project_id, normalized, name]
        )
        conn.commit()
        conn.close()

        return project_id

    def add(self, content: str, category: str = "general", importance: int = 5) -> Dict:
        """Add a memory."""
        import uuid

        memory_id = str(uuid.uuid4())
        tags_json = json.dumps([])

        conn = self._get_connection()
        conn.execute("""
            INSERT INTO memories (id, project_id, content, category, importance, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [memory_id, self.project_id, content, category, importance, tags_json])
        conn.commit()
        conn.close()

        return {"id": memory_id, "status": "added", "content": content}

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memories."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT m.*, memories_fts.rank
            FROM memories m
            JOIN memories_fts ON m.rowid = memories_fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY memories_fts.rank
            LIMIT ?
        """, [query, limit]).fetchall()

        conn.close()
        return [dict(row) for row in rows]

    def list(self, limit: int = 20) -> List[Dict]:
        """List recent memories."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT * FROM memories
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, [self.project_id, limit]).fetchall()

        conn.close()
        return [dict(row) for row in rows]

    def handoff_save(self, context: str, goal: str, from_tool: str = "unknown",
                     to_tool: str = None, state: Dict = None) -> Dict:
        """Save a handoff."""
        import uuid

        handover_id = str(uuid.uuid4())
        state_json = json.dumps(state or {})

        conn = self._get_connection()
        conn.execute("""
            INSERT INTO handovers (id, project_id, from_tool, to_tool, context, goal, state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [handover_id, self.project_id, from_tool, to_tool, context, goal, state_json])
        conn.commit()
        conn.close()

        return {
            "id": handover_id,
            "status": "saved",
            "from": from_tool,
            "to": to_tool or "any"
        }

    def handoff_load(self, tool_name: str = None) -> Optional[Dict]:
        """Load pending handoff."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        sql = """
            SELECT * FROM handovers
            WHERE project_id = ? AND status = 'pending'
              AND (to_tool IS NULL OR to_tool = ? OR to_tool = 'any')
            ORDER BY created_at DESC LIMIT 1
        """
        row = conn.execute(sql, [self.project_id, tool_name or "any"]).fetchone()
        conn.close()

        return dict(row) if row else None

    def handoff_complete(self, handover_id: str) -> Dict:
        """Complete a handoff."""
        conn = self._get_connection()
        conn.execute("""
            UPDATE handovers
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [handover_id])
        conn.commit()
        conn.close()

        return {"id": handover_id, "status": "completed"}

    def status(self) -> Dict:
        """Get memory hub status."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        memory_count = conn.execute(
            "SELECT COUNT(*) as count FROM memories WHERE project_id = ?",
            [self.project_id]
        ).fetchone()['count']

        pending_handoffs = conn.execute(
            "SELECT COUNT(*) as count FROM handovers WHERE project_id = ? AND status = 'pending'",
            [self.project_id]
        ).fetchone()['count']

        conn.close()

        return {
            "project_id": self.project_id,
            "memories": memory_count,
            "pending_handoffs": pending_handoffs,
            "db_path": str(self.db_path)
        }


# CLI Interface
def main():
    if len(sys.argv) < 2:
        print("MCP Memory Hub Client")
        print("Usage: memory-client.py <command> [args]")
        print("")
        print("Commands:")
        print("  add <content>           Add a memory")
        print("  search <query>          Search memories")
        print("  list                   List recent memories")
        print("  status                  Show memory hub status")
        print("  handoff-save <context>  Save handoff")
        print("  handoff-load           Load pending handoff")
        return

    hub = MemoryHub()
    cmd = sys.argv[1]

    if cmd == "add":
        content = " ".join(sys.argv[2:])
        if content:
            result = hub.add(content)
            print(f"✅ Memory added: {result['id']}")
        else:
            print("❌ No content provided")

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        if query:
            results = hub.search(query)
            print(f"🔍 Results for '{query}':")
            for r in results:
                print(f"  - [{r['category']}] {r['content'][:80]}")
        else:
            print("❌ No query provided")

    elif cmd == "list":
        memories = hub.list()
        print(f"📋 Recent memories ({len(memories)}):")
        for m in memories:
            print(f"  - [{m['category']}] {m['content'][:80]}")

    elif cmd == "status":
        status = hub.status()
        print("📊 Memory Hub Status:")
        print(f"  Project: {status['project_id'][:20]}...")
        print(f"  Memories: {status['memories']}")
        print(f"  Pending Handoffs: {status['pending_handoffs']}")
        print(f"  DB: {status['db_path']}")

    elif cmd == "handoff-save":
        context = " ".join(sys.argv[2:])
        if context:
            result = hub.handoff_save(context, "continue work")
            print(f"✅ Handoff saved: {result['id']}")
        else:
            print("❌ No context provided")

    elif cmd == "handoff-load":
        handoff = hub.handoff_load()
        if handoff:
            print("📋 Pending Handoff:")
            print(f"  From: {handoff['from_tool']}")
            print(f"  Context: {handoff['context']}")
            print(f"  Goal: {handoff['goal']}")
        else:
            print("No pending handoffs")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()