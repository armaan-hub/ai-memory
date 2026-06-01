"""Database module for MCP Memory Hub - SQLite with FTS5."""

import sqlite3
import uuid
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from config import get_database_path, get_log_level

logger = logging.getLogger(__name__)


def init_logging():
    """Initialize logging based on config."""
    level = get_log_level()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


# Global connection for daemon
_db_path: Optional[Path] = None


def get_db_path() -> Path:
    """Get database path, initializing if needed."""
    global _db_path
    if _db_path is None:
        _db_path = get_database_path()
        _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def get_db():
    """Get a database connection with WAL mode and busy timeout."""
    conn = sqlite3.connect(str(get_db_path()), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with schema."""
    db_path = get_db_path()

    # Create data directory
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))

    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Create tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 5,
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # FTS5 virtual table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)

    # Triggers to keep FTS in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES('delete', old.rowid, old.content);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES('delete', old.rowid, old.content);
            INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
        END
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS handovers (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            from_tool TEXT NOT NULL,
            to_tool TEXT,
            context TEXT NOT NULL,
            goal TEXT NOT NULL,
            state TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id TEXT PRIMARY KEY,
            tool_name TEXT NOT NULL,
            project_id TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS compacts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            content TEXT NOT NULL,
            memory_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_handovers_project_status ON handovers(project_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_compacts_project_tier ON compacts(project_id, tier)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_connections_active ON connections(is_active)")

    conn.commit()
    conn.close()

    logger.info(f"Database initialized at {db_path}")


# ─────────────────────────────────────────────────────────────────
# Project Operations
# ─────────────────────────────────────────────────────────────────

def get_or_create_project(project_path: str) -> dict:
    """Get or create a project by path."""
    normalized = str(Path(project_path).resolve())

    with get_db() as conn:
        # Try to get existing
        row = conn.execute(
            "SELECT * FROM projects WHERE path = ?", [normalized]
        ).fetchone()

        if row:
            # Update last_accessed
            conn.execute(
                "UPDATE projects SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                [row["id"]]
            )
            return dict(row)

        # Create new
        project_id = str(uuid.uuid4())
        name = Path(normalized).name
        conn.execute(
            "INSERT INTO projects (id, path, name) VALUES (?, ?, ?)",
            [project_id, normalized, name]
        )

        return {
            "id": project_id,
            "path": normalized,
            "name": name
        }


def list_projects() -> list[dict]:
    """List all projects."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY last_accessed DESC"
        ).fetchall()
    return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────────────────
# Memory Operations
# ─────────────────────────────────────────────────────────────────

def add_memory(project_id: str, content: str, category: str = "general",
               importance: int = 5, tags: list = None) -> dict:
    """Add a new memory."""
    memory_id = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])

    with get_db() as conn:
        conn.execute("""
            INSERT INTO memories (id, project_id, content, category, importance, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [memory_id, project_id, content, category, importance, tags_json])

    return {"id": memory_id, "status": "added"}


def search_memories(query: str, project_id: str = None,
                    category: str = None, limit: int = 20) -> list[dict]:
    """Search memories using FTS5."""
    with get_db() as conn:
        if project_id:
            sql = """
                SELECT m.*, memories_fts.rank
                FROM memories m
                JOIN memories_fts ON m.rowid = memories_fts.rowid
                WHERE memories_fts MATCH ?
                  AND m.project_id = ?
            """
            params = [query, project_id]

            if category:
                sql += " AND m.category = ?"
                params.append(category)

            sql += " ORDER BY memories_fts.rank LIMIT ?"
            params.append(limit)
        else:
            sql = """
                SELECT m.*, memories_fts.rank
                FROM memories m
                JOIN memories_fts ON m.rowid = memories_fts.rowid
                WHERE memories_fts MATCH ?
            """
            params = [query, limit]

            if category:
                sql += " AND m.category = ?"
                params.append(category)

            sql += " ORDER BY memories_fts.rank LIMIT ?"

        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def get_recent_memories(project_id: str, limit: int = 20) -> list[dict]:
    """Get recent memories for a project."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM memories
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, [project_id, limit]).fetchall()

    return [dict(row) for row in rows]


def list_memories(project_id: str = None, tag: str = None,
                  limit: int = 50, offset: int = 0) -> list[dict]:
    """List memories with optional filters."""
    with get_db() as conn:
        if project_id:
            sql = "SELECT * FROM memories WHERE project_id = ?"
            params = [project_id]

            if tag:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")

            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        else:
            sql = "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = [limit, offset]

        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────────────────
# Handover Operations
# ─────────────────────────────────────────────────────────────────

def save_handover(project_id: str, from_tool: str, context: str,
                  goal: str, to_tool: str = None, state: dict = None) -> dict:
    """Save a handover."""
    handover_id = str(uuid.uuid4())
    state_json = json.dumps(state or {})

    with get_db() as conn:
        conn.execute("""
            INSERT INTO handovers (id, project_id, from_tool, to_tool, context, goal, state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [handover_id, project_id, from_tool, to_tool, context, goal, state_json])

    return {"id": handover_id, "status": "saved", "from": from_tool, "to": to_tool or "any"}


def load_handover(project_id: str, tool_name: str = None) -> dict | None:
    """Load pending handover for a project."""
    with get_db() as conn:
        sql = """
            SELECT * FROM handovers
            WHERE project_id = ? AND status = 'pending'
              AND (to_tool IS NULL OR to_tool = ? OR to_tool = 'any')
            ORDER BY created_at DESC LIMIT 1
        """
        row = conn.execute(sql, [project_id, tool_name or "any"]).fetchone()

    return dict(row) if row else None


def complete_handover(handover_id: str, outcome: str = None) -> dict:
    """Mark a handover as completed."""
    with get_db() as conn:
        conn.execute("""
            UPDATE handovers
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [handover_id])

    return {"id": handover_id, "status": "completed"}


def get_handover_status(handover_id: str = None) -> list[dict]:
    """Get handover status (one or all)."""
    with get_db() as conn:
        if handover_id:
            sql = """
                SELECT h.*, p.name as project_name
                FROM handovers h
                JOIN projects p ON h.project_id = p.id
                WHERE h.id = ?
            """
            rows = conn.execute(sql, [handover_id]).fetchall()
        else:
            sql = """
                SELECT h.*, p.name as project_name
                FROM handovers h
                JOIN projects p ON h.project_id = p.id
                WHERE h.status = 'pending'
                ORDER BY h.created_at DESC
            """
            rows = conn.execute(sql).fetchall()

    return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────────────────
# Connection Tracking
# ─────────────────────────────────────────────────────────────────

def register_connection(tool_name: str, project_id: str = None,
                        metadata: dict = None) -> str:
    """Register a tool connection."""
    conn_id = str(uuid.uuid4())
    metadata_json = json.dumps(metadata or {})

    with get_db() as conn:
        # Deactivate any existing connection for this tool
        conn.execute(
            "UPDATE connections SET is_active = 0 WHERE tool_name = ?",
            [tool_name]
        )

        # Register new connection
        conn.execute("""
            INSERT INTO connections (id, tool_name, project_id, is_active, metadata)
            VALUES (?, ?, ?, 1, ?)
        """, [conn_id, tool_name, project_id, metadata_json])

    return conn_id


def unregister_connection(conn_id: str):
    """Mark a connection as inactive."""
    with get_db() as conn:
        conn.execute(
            "UPDATE connections SET is_active = 0 WHERE id = ?",
            [conn_id]
        )


def get_active_connection(project_id: str = None) -> dict | None:
    """Get the active connection for a project."""
    with get_db() as conn:
        if project_id:
            sql = """
                SELECT * FROM connections
                WHERE project_id = ? AND is_active = 1
                ORDER BY last_seen DESC LIMIT 1
            """
            row = conn.execute(sql, [project_id]).fetchone()
        else:
            sql = """
                SELECT * FROM connections
                WHERE is_active = 1
                ORDER BY last_seen DESC LIMIT 1
            """
            row = conn.execute(sql).fetchone()

    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────
# Compact Operations
# ─────────────────────────────────────────────────────────────────

def create_compact(project_id: str, tier: str, content: str,
                    memory_count: int) -> dict:
    """Create a compact summary."""
    compact_id = str(uuid.uuid4())

    with get_db() as conn:
        conn.execute("""
            INSERT INTO compacts (id, project_id, tier, content, memory_count)
            VALUES (?, ?, ?, ?, ?)
        """, [compact_id, project_id, tier, content, memory_count])

    return {"id": compact_id, "status": "created"}


def get_latest_compact(project_id: str, tier: str = None) -> dict | None:
    """Get the latest compact for a project."""
    with get_db() as conn:
        if tier:
            sql = """
                SELECT * FROM compacts
                WHERE project_id = ? AND tier = ?
                ORDER BY created_at DESC LIMIT 1
            """
            row = conn.execute(sql, [project_id, tier]).fetchone()
        else:
            sql = """
                SELECT * FROM compacts
                WHERE project_id = ?
                ORDER BY created_at DESC LIMIT 1
            """
            row = conn.execute(sql, [project_id]).fetchone()

    return dict(row) if row else None


if __name__ == "__main__":
    init_logging()
    init_database()
    print("Database initialized successfully")
