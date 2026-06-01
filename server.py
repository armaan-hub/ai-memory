#!/usr/bin/env python3
"""MCP Memory Hub Server - Universal memory for AI tools."""

import asyncio
import sys
import json
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_database, get_db, get_or_create_project, list_projects
from database import add_memory, search_memories, get_recent_memories, list_memories
from database import save_handover, load_handover, complete_handover, get_handover_status
from database import register_connection, unregister_connection, get_active_connection
from database import create_compact, get_latest_compact
from utils.project import detect_project, get_cwd_project
from config import get_config, init_logging

logger = logging.getLogger(__name__)

# MCP protocol constants
PROTOCOL_VERSION = "2024-11-05"


class MemoryHubServer:
    """MCP Server for Universal Memory Hub."""

    def __init__(self):
        self.config = get_config()
        self.connection_id = None
        self.current_tool = "unknown"

    async def handle_request(self, method: str, params: dict) -> dict:
        """Handle an MCP request."""
        handlers = {
            "initialize": self.handle_initialize,
            "tools/list": self.handle_list_tools,
            "tools/call": self.handle_call_tool,
            "ping": self.handle_ping,
        }

        handler = handlers.get(method)
        if handler:
            return await handler(params)

        return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}

    async def handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        self.current_tool = params.get("clientInfo", {}).get("name", "unknown")
        logger.info(f"Initializing MCP Memory Hub for {self.current_tool}")

        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {
                "name": "mcp-memory-hub",
                "version": "0.1.0"
            },
            "capabilities": {
                "tools": {}
            }
        }

    async def handle_list_tools(self, params: dict) -> dict:
        """Handle tools/list request."""
        tools = [
            {
                "name": "memory_add",
                "description": "Add an observation to persistent memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The memory/observation to store"},
                        "category": {
                            "type": "string",
                            "enum": ["general", "architecture", "bug", "feature", "decision", "context", "todo"],
                            "default": "general"
                        },
                        "importance": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "memory_search",
                "description": "Search memories using full-text search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "project": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "default": 20}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "memory_recent",
                "description": "Get recent memories for context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "limit": {"type": "integer", "default": 10}
                    }
                }
            },
            {
                "name": "memory_list",
                "description": "List all memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "limit": {"type": "integer", "default": 50}
                    }
                }
            },
            {
                "name": "memory_compact",
                "description": "Generate compressed summary of memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string", "enum": ["light", "medium", "deep"], "default": "medium"},
                        "project": {"type": "string"}
                    }
                }
            },
            {
                "name": "handoff_save",
                "description": "Save state for handoff to next tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "context": {"type": "string"},
                        "goal": {"type": "string"},
                        "project": {"type": "string"},
                        "to_tool": {"type": "string"}
                    },
                    "required": ["context", "goal"]
                }
            },
            {
                "name": "handoff_load",
                "description": "Load pending handoff for current tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"}
                    }
                }
            },
            {
                "name": "handoff_complete",
                "description": "Mark a handoff as completed",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "handover_id": {"type": "string"}
                    },
                    "required": ["handover_id"]
                }
            },
            {
                "name": "handoff_status",
                "description": "Show pending handoffs",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "project_list",
                "description": "List all tracked projects",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "context_inject",
                "description": "Get formatted context string for injection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "style": {"type": "string", "enum": ["concise", "detailed"], "default": "concise"}
                    }
                }
            }
        ]

        return {"tools": tools}

    async def handle_call_tool(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "memory_add":
                return await self.tool_memory_add(arguments)
            elif tool_name == "memory_search":
                return await self.tool_memory_search(arguments)
            elif tool_name == "memory_recent":
                return await self.tool_memory_recent(arguments)
            elif tool_name == "memory_list":
                return await self.tool_memory_list(arguments)
            elif tool_name == "memory_compact":
                return await self.tool_memory_compact(arguments)
            elif tool_name == "handoff_save":
                return await self.tool_handoff_save(arguments)
            elif tool_name == "handoff_load":
                return await self.tool_handoff_load(arguments)
            elif tool_name == "handoff_complete":
                return await self.tool_handoff_complete(arguments)
            elif tool_name == "handoff_status":
                return await self.tool_handoff_status(arguments)
            elif tool_name == "project_list":
                return await self.tool_project_list(arguments)
            elif tool_name == "context_inject":
                return await self.tool_context_inject(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error in {tool_name}: {e}")
            return {"error": str(e)}

    async def tool_memory_add(self, args: dict) -> dict:
        """Add a memory."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        result = add_memory(
            project_id=project_data["id"],
            content=args["content"],
            category=args.get("category", "general"),
            importance=args.get("importance", 5),
            tags=args.get("tags", [])
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Memory added: {result['id'][:8]}... for project {project['name']}"
                }
            ]
        }

    async def tool_memory_search(self, args: dict) -> dict:
        """Search memories."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        results = search_memories(
            query=args["query"],
            project_id=project_data["id"],
            category=args.get("category"),
            limit=args.get("limit", 20)
        )

        if not results:
            return {"content": [{"type": "text", "text": "No memories found."}]}

        lines = [f"Found {len(results)} memories:\n"]
        for r in results[:10]:
            lines.append(f"[{r['category']}] {r['content'][:100]}...")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    async def tool_memory_recent(self, args: dict) -> dict:
        """Get recent memories."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        results = get_recent_memories(
            project_id=project_data["id"],
            limit=args.get("limit", 10)
        )

        if not results:
            return {"content": [{"type": "text", "text": "No recent memories."}]}

        lines = ["Recent memories:\n"]
        for r in results:
            lines.append(f"[{r['category']}] {r['content'][:100]}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    async def tool_memory_list(self, args: dict) -> dict:
        """List memories."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        results = list_memories(
            project_id=project_data["id"],
            limit=args.get("limit", 50)
        )

        return {"content": [{"type": "text", "text": f"Total: {len(results)} memories"}]}

    async def tool_memory_compact(self, args: dict) -> dict:
        """Generate compact summary."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])
        tier = args.get("tier", "medium")

        # Get memories for compaction
        memories = get_recent_memories(project_id=project_data["id"], limit=100)

        if not memories:
            return {"content": [{"type": "text", "text": "No memories to compact."}]}

        # Simple tier-based compression
        max_items = {"light": 5, "medium": 15, "deep": 50}.get(tier, 15)
        selected = memories[:max_items]

        # Format as summary
        lines = [f"# Memory Compact ({tier.upper()}) - {project['name']}\n"]
        lines.append(f"Total memories: {len(memories)} | Compacted: {len(selected)}\n")

        by_cat = {}
        for m in selected:
            cat = m.get("category", "general")
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(m["content"][:80])

        for cat, contents in by_cat.items():
            lines.append(f"\n## {cat.upper()}")
            for c in contents:
                lines.append(f"- {c}")

        summary = "\n".join(lines)

        # Store compact
        create_compact(
            project_id=project_data["id"],
            tier=tier,
            content=summary,
            memory_count=len(memories)
        )

        return {"content": [{"type": "text", "text": summary}]}

    async def tool_handoff_save(self, args: dict) -> dict:
        """Save handoff."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        result = save_handover(
            project_id=project_data["id"],
            from_tool=self.current_tool,
            context=args.get("context", ""),
            goal=args.get("goal", ""),
            to_tool=args.get("to_tool")
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Handoff saved: {result['id'][:8]}... → {result['to']}"
                }
            ]
        }

    async def tool_handoff_load(self, args: dict) -> dict:
        """Load handoff."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])

        handoff = load_handover(
            project_id=project_data["id"],
            tool_name=self.current_tool
        )

        if not handoff:
            return {"content": [{"type": "text", "text": "No pending handoff."}]}

        lines = [
            f"📋 HANDOVER from {handoff['from_tool']}:",
            f"Goal: {handoff['goal']}",
            f"Context: {handoff['context']}"
        ]

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    async def tool_handoff_complete(self, args: dict) -> dict:
        """Complete handoff."""
        result = complete_handover(args.get("handover_id"))
        return {"content": [{"type": "text", "text": f"Handoff {result['status']}"}]}

    async def tool_handoff_status(self, args: dict) -> dict:
        """Get handoff status."""
        handoffs = get_handover_status()

        if not handoffs:
            return {"content": [{"type": "text", "text": "No pending handoffs."}]}

        lines = ["Pending handoffs:\n"]
        for h in handoffs:
            lines.append(f"- {h['project_name']}: {h['from_tool']} → {h['to_tool'] or 'any'}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    async def tool_project_list(self, args: dict) -> dict:
        """List projects."""
        projects = list_projects()

        if not projects:
            return {"content": [{"type": "text", "text": "No projects tracked."}]}

        lines = ["Tracked projects:\n"]
        for p in projects:
            lines.append(f"- {p['name']} ({p['path']})")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    async def tool_context_inject(self, args: dict) -> dict:
        """Get context for injection."""
        project = detect_project(args.get("project"))
        project_data = get_or_create_project(project["path"])
        style = args.get("style", "concise")

        # Check for pending handoff
        handoff = load_handover(project_id=project_data["id"], tool_name=self.current_tool)

        # Get recent memories
        limit = 5 if style == "concise" else 20
        memories = get_recent_memories(project_id=project_data["id"], limit=limit)

        parts = []

        if handoff:
            parts.append(f"📋 HANDOVER from {handoff['from_tool']}:\n{handoff['goal']}")

        if memories:
            parts.append("📝 RECENT MEMORIES:")
            for m in memories:
                parts.append(f"[{m['category']}] {m['content'][:100]}")

        if not parts:
            return {"content": [{"type": "text", "text": f"(No context for {project['name']})"}]}

        return {"content": [{"type": "text", "text": "\n\n".join(parts)}]}

    async def handle_ping(self, params: dict) -> dict:
        """Handle ping request."""
        return {"pong": True}


async def run_stdio_server():
    """Run MCP server using stdio transport."""
    init_logging()
    init_database()

    server = MemoryHubServer()

    while True:
        try:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            request = json.loads(line)

            # Handle request
            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id")

            result = await server.handle_request(method, params)

            # Send response
            response = {"jsonrpc": "2.0", "id": req_id}

            if "error" in result and isinstance(result.get("error"), dict):
                response["error"] = result["error"]
            else:
                response["result"] = result

            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Server error: {e}")
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)


def main():
    """Main entry point."""
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
