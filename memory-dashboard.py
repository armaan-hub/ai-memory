#!/usr/bin/env python3
"""
MCP Memory Hub - Web Dashboard
View all memories in a beautiful web interface.

Run: python3 memory-dashboard.py
Then open: http://localhost:5555
"""

from flask import Flask, render_template_string, jsonify, request
import sqlite3
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

DB_PATH = Path.home() / ".claude" / "mcp-daemon" / "data" / "memory.db"

# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Memory Hub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px 40px;
            border-bottom: 1px solid #00ff8866;
        }
        .header h1 {
            color: #00ff88;
            font-size: 28px;
            text-shadow: 0 0 20px #00ff8844;
        }
        .header p { color: #888; margin-top: 5px; }

        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-card .number {
            font-size: 36px;
            font-weight: bold;
            color: #00ff88;
            text-shadow: 0 0 15px #00ff8844;
        }
        .stat-card .label {
            color: #888;
            margin-top: 5px;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 10px 20px;
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 8px;
            color: #888;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab:hover { border-color: #00ff88; color: #00ff88; }
        .tab.active {
            background: #00ff88;
            color: #0a0a0f;
            border-color: #00ff88;
        }

        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .search-box input {
            flex: 1;
            padding: 12px 20px;
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
        }
        .search-box input:focus {
            outline: none;
            border-color: #00ff88;
            box-shadow: 0 0 15px #00ff8822;
        }
        .search-box button {
            padding: 12px 30px;
            background: #00ff88;
            border: none;
            border-radius: 8px;
            color: #0a0a0f;
            font-weight: bold;
            cursor: pointer;
        }

        .memory-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .memory-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #12121f 100%);
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s;
        }
        .memory-card:hover {
            border-color: #00ff8866;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px #00ff8822;
        }
        .memory-card .category {
            display: inline-block;
            padding: 4px 12px;
            background: #00ff8822;
            color: #00ff88;
            border-radius: 20px;
            font-size: 12px;
            text-transform: uppercase;
        }
        .memory-card .source {
            display: inline-block;
            padding: 4px 12px;
            background: #ff880022;
            color: #ff8800;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 5px;
        }
        .memory-card .content {
            margin: 15px 0;
            line-height: 1.6;
            color: #ccc;
        }
        .memory-card .meta {
            display: flex;
            justify-content: space-between;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #333;
            padding-top: 10px;
        }

        .handoff-section {
            background: linear-gradient(135deg, #1a1a2e 0%, #12121f 100%);
            border: 1px solid #ff880066;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .handoff-section h3 {
            color: #ff8800;
            margin-bottom: 15px;
        }
        .handoff-item {
            background: #0a0a0f;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }

        .empty {
            text-align: center;
            padding: 60px;
            color: #666;
        }
        .empty h3 { color: #888; margin-bottom: 10px; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .live { animation: pulse 2s infinite; color: #00ff88; }

        .tool-icons {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tool-icon {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: #1a1a2e;
            border-radius: 30px;
            font-size: 14px;
        }
        .tool-icon.claude { border: 1px solid #ff8800; color: #ff8800; }
        .tool-icon.copilot { border: 1px solid #00ff88; color: #00ff88; }
        .tool-icon.gemini { border: 1px solid #4285f4; color: #4285f4; }
        .tool-icon.jarvis { border: 1px solid #9d4edd; color: #9d4edd; }
        .tool-icon.opencode { border: 1px solid #00ff88; color: #00ff88; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 MCP Memory Hub</h1>
        <p>Universal memory for all AI tools | <span class="live">● LIVE</span></p>
    </div>

    <div class="container">
        <div class="tool-icons">
            <div class="tool-icon claudecode">Claude Code</div>
            <div class="tool-icon copilot">GitHub Copilot</div>
            <div class="tool-icon gemini">Gemini CLI</div>
            <div class="tool-icon jarvis">Jarvis</div>
            <div class="tool-icon opencode">OpenCode</div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number" id="total-memories">{{ total_memories }}</div>
                <div class="label">Total Memories</div>
            </div>
            <div class="stat-card">
                <div class="number">{{ projects_count }}</div>
                <div class="label">Projects</div>
            </div>
            <div class="stat-card">
                <div class="number">{{ handoffs_count }}</div>
                <div class="label">Pending Handoffs</div>
            </div>
            <div class="stat-card">
                <div class="number">{{ categories_count }}</div>
                <div class="label">Categories</div>
            </div>
        </div>

        <div class="search-box">
            <input type="text" id="search-input" placeholder="Search memories...">
            <button onclick="searchMemories()">Search</button>
            <button onclick="showAll()" style="background: #333; color: #fff;">Show All</button>
        </div>

        {% if handoffs %}
        <div class="handoff-section">
            <h3>📋 Pending Handoffs</h3>
            {% for h in handoffs %}
            <div class="handoff-item">
                <strong>{{ h.from_tool }}</strong> → <strong>{{ h.to_tool or 'any' }}</strong>
                <p style="color:#ccc; margin:8px 0;">{{ h.context }}</p>
                <small style="color:#666;">Goal: {{ h.goal }} | {{ h.created_at }}</small>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="tabs">
            <div class="tab active" onclick="filterCategory('all')">All</div>
            {% for cat in categories %}
            <div class="tab" onclick="filterCategory('{{ cat }}')">{{ cat }}</div>
            {% endfor %}
        </div>

        <div class="memory-grid" id="memory-grid">
            {% for memory in memories %}
            <div class="memory-card" data-category="{{ memory.category }}">
                <span class="category">{{ memory.category }}</span>
                <span class="source">{{ memory.project_name or 'general' }}</span>
                <div class="content">{{ memory.content }}</div>
                <div class="meta">
                    <span>{{ memory.importance }}/10 ⭐</span>
                    <span>{{ memory.created_at[:19] if memory.created_at else '' }}</span>
                </div>
            </div>
            {% endfor %}

            {% if not memories %}
            <div class="empty">
                <h3>No memories yet</h3>
                <p>Start using your AI tools and memories will appear here</p>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        function filterCategory(cat) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.querySelectorAll('.memory-card').forEach(card => {
                if (cat === 'all' || card.dataset.category === cat) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        function searchMemories() {
            const query = document.getElementById('search-input').value;
            if (query) {
                window.location.href = '/api/search?q=' + encodeURIComponent(query);
            }
        }

        document.getElementById('search-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') searchMemories();
        });

        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()

    # Get stats
    total_memories = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    projects_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    handoffs_count = conn.execute("SELECT COUNT(*) FROM handovers WHERE status = 'pending'").fetchone()[0]
    categories = conn.execute("SELECT DISTINCT category FROM memories").fetchall()
    categories_count = len(categories)

    # Get memories
    memories = conn.execute("""
        SELECT m.*, p.name as project_name
        FROM memories m
        LEFT JOIN projects p ON m.project_id = p.id
        ORDER BY m.created_at DESC
        LIMIT 100
    """).fetchall()

    # Get pending handoffs
    handoffs = conn.execute("""
        SELECT * FROM handovers
        WHERE status = 'pending'
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template_string(DASHBOARD_HTML,
        total_memories=total_memories,
        projects_count=projects_count,
        handoffs_count=handoffs_count,
        categories_count=categories_count,
        categories=[c['category'] for c in categories],
        memories=[dict(m) for m in memories],
        handoffs=[dict(h) for h in handoffs]
    )

@app.route('/api/memories')
def api_memories():
    conn = get_db()
    memories = conn.execute("""
        SELECT m.*, p.name as project_name
        FROM memories m
        LEFT JOIN projects p ON m.project_id = p.id
        ORDER BY m.created_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(m) for m in memories])

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    conn = get_db()

    if query:
        rows = conn.execute("""
            SELECT m.*, p.name as project_name, memories_fts.rank
            FROM memories m
            JOIN memories_fts ON m.rowid = memories_fts.rowid
            LEFT JOIN projects p ON m.project_id = p.id
            WHERE memories_fts MATCH ?
            ORDER BY memories_fts.rank
            LIMIT 50
        """, [query]).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.*, p.name as project_name
            FROM memories m
            LEFT JOIN projects p ON m.project_id = p.id
            ORDER BY m.created_at DESC
            LIMIT 50
        """).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    stats = {
        'total_memories': conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
        'projects': conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
        'pending_handoffs': conn.execute("SELECT COUNT(*) FROM handovers WHERE status = 'pending'").fetchone()[0],
    }
    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    print("🧠 MCP Memory Hub Dashboard")
    print("=" * 40)
    print("🌐 Opening: http://localhost:5555")
    print("📝 Add memories with: memory-client.py add 'text'")
    print()
    app.run(host='0.0.0.0', port=5555, debug=True)