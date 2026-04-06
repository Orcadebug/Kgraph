"""
AgentToolkit — LLM agent with filesystem + graph tools via OpenRouter.

Implements the "file-system-like commands for concept navigation" pattern
from arXiv:2512.05470 (Everything is Context).

Tools available to the agent:
  navigate(concept)        — get related concepts (like cd + ls)
  inspect(concept)         — full node details (like cat)
  connect(a, b)            — shortest path between concepts
  search_graph(query)      — semantic graph search
  search_files(query)      — flat keyword search across docs
  read(file_path)          — read a source doc
"""
import json
import os
from typing import Any

from dotenv import load_dotenv

from .filesystem import FileSystem
from .query import GraphQuery

try:
    from systemfs.vfs import SystemFS
except ImportError:
    SystemFS = None

load_dotenv()

# ── Tool definitions (OpenAI function-calling format) ─────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Get all concepts related to an entity in the knowledge graph. Use this to explore what a concept connects to.",
            "parameters": {
                "type": "object",
                "properties": {
                    "concept": {"type": "string", "description": "The concept or entity name to navigate from"},
                },
                "required": ["concept"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect",
            "description": "Get full details about a concept: description, source doc, all incoming and outgoing relationships.",
            "parameters": {
                "type": "object",
                "properties": {
                    "concept": {"type": "string", "description": "The concept or entity name to inspect"},
                },
                "required": ["concept"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "connect",
            "description": "Find the shortest conceptual path between two entities in the knowledge graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Starting concept"},
                    "target": {"type": "string", "description": "Target concept"},
                },
                "required": ["source", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_graph",
            "description": "Search the knowledge graph by concept name or description keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Keyword search across all documentation files (flat filesystem search).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read the full content of a documentation file by its relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the doc file (e.g. 'charges/create-charge.md')"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vfs_read",
            "description": "Read any file in the Virtual File System by absolute path. Paths include /docs/, /graph/nodes/, /graph/edges/, /graph/stats, /context/memory/fact/, /context/memory/episodic/, /context/scratchpad/",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute VFS path (e.g. '/docs/auth.md', '/graph/nodes/Charge', '/context/memory/fact/key')"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vfs_list",
            "description": "List contents of a VFS directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "VFS directory path (e.g. '/', '/docs/', '/graph/nodes/', '/context/memory/')"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vfs_search",
            "description": "Search for content across the VFS. Optionally scope to a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms"},
                    "path": {"type": "string", "description": "Optional VFS path to scope the search (default: '/')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vfs_write",
            "description": "Write content to the VFS. Only writable paths work (e.g. /context/memory/fact/, /context/scratchpad/).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute VFS path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
]

_SYSTEM_PROMPT = """You are a documentation navigator with access to two complementary systems:
1. A flat filesystem of API documentation files
2. A conceptual knowledge graph extracted from those docs

Use the graph tools (navigate, inspect, connect, search_graph) to understand relationships
between concepts. Use filesystem tools (search_files, read) to get precise textual content.

When answering questions:
- Start by using the graph to understand the conceptual landscape
- Then read specific files for precise details
- Prefer graph traversal for questions about relationships; prefer file reading for exact API parameters
- Always cite which documents you consulted

You have access to these tools: navigate, inspect, connect, search_graph, search_files, read

The VFS (Virtual File System) exposes all context sources in a unified hierarchy:
- /docs/          — API documentation files
- /graph/nodes/   — Knowledge graph nodes (use vfs_read /graph/nodes/Charge for details)
- /graph/edges/   — Knowledge graph edges
- /graph/stats    — Graph statistics
- /context/memory/fact/       — Verified facts
- /context/memory/episodic/   — Interaction memories
- /context/memory/procedural/ — Procedural knowledge
- /context/scratchpad/        — Ephemeral workspace

Use vfs_list to explore, vfs_read to fetch content, vfs_search to find relevant nodes,
and vfs_write to save findings to /context/memory/ or /context/scratchpad/.
"""


class AgentToolkit:
    """
    Wraps the graph query and filesystem interfaces as LLM tools.
    Runs a tool-calling loop via OpenRouter and returns a structured response.
    """

    def __init__(self, graph_query: GraphQuery = None, filesystem: FileSystem = None,
                 model: str | None = None, system_fs=None):
        self.gq = graph_query
        self.fs = filesystem
        self.model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

        if system_fs is not None:
            self._vfs = system_fs
        elif SystemFS is not None and (graph_query is not None or filesystem is not None):
            try:
                self._vfs = SystemFS()
            except Exception:
                self._vfs = None
        else:
            self._vfs = None

    def chat(self, user_message: str, max_iterations: int = 10) -> dict[str, Any]:
        """
        Run the agent loop for a user query.
        Returns: {answer, traversal_log, sources}
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {
                "answer": "No OPENROUTER_API_KEY set. Run with --no-llm to use heuristic mode, or set the key in .env",
                "traversal_log": [],
                "sources": [],
            }

        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        traversal_log: list[dict] = []
        sources: set[str] = set()

        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
                temperature=0.0,
            )

            choice = response.choices[0]
            messages.append(choice.message.model_dump(exclude_none=True))

            # No more tool calls — we have the final answer
            if not choice.message.tool_calls:
                return {
                    "answer": choice.message.content or "",
                    "traversal_log": traversal_log,
                    "sources": sorted(sources),
                }

            # Execute each tool call
            for tc in choice.message.tool_calls:
                tool_name = tc.function.name
                args = json.loads(tc.function.arguments)
                result, file_refs = self._dispatch(tool_name, args)

                sources.update(file_refs)
                traversal_log.append({
                    "tool": tool_name,
                    "args": args,
                    "result_summary": _summarize(result),
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        return {
            "answer": "Max iterations reached without a final answer.",
            "traversal_log": traversal_log,
            "sources": sorted(sources),
        }

    def _dispatch(self, tool_name: str, args: dict) -> tuple[Any, list[str]]:
        """Execute a tool and return (result, file_references)."""
        if tool_name == "navigate":
            result = self.gq.related_concepts(args["concept"])
            sources = _extract_source_files(result)
            return result, sources

        elif tool_name == "inspect":
            result = self.gq.explain_node(args["concept"])
            sources = _extract_source_files(result)
            return result, sources

        elif tool_name == "connect":
            result = self.gq.find_connection(args["source"], args["target"])
            return result, []

        elif tool_name == "search_graph":
            result = self.gq.search_graph(args["query"])
            sources = [r.get("source_file", "") for r in result.get("results", []) if r.get("source_file")]
            return result, sources

        elif tool_name == "search_files":
            result = self.fs.search(args["query"])
            sources = [r["path"] for r in result]
            return result, sources

        elif tool_name == "read":
            content = self.fs.read_file(args["file_path"])
            if content is None:
                return {"error": f"File not found: {args['file_path']}"}, []
            return {"path": args["file_path"], "content": content}, [args["file_path"]]

        elif tool_name == "vfs_read":
            if self._vfs:
                result = self._vfs.read(args["path"])
                if result.success and result.data:
                    return {"path": args["path"], "content": result.data.content,
                            "kind": result.data.kind}, []
                return {"error": result.error or "not found"}, []
            return {"error": "VFS not available"}, []

        elif tool_name == "vfs_list":
            if self._vfs:
                result = self._vfs.list(args.get("path", "/"))
                if result.success:
                    items = [{"path": n.path, "name": n.name, "kind": n.kind}
                             for n in (result.data or [])]
                    return {"path": args.get("path", "/"), "items": items}, []
                return {"error": result.error or "list failed"}, []
            return {"error": "VFS not available"}, []

        elif tool_name == "vfs_search":
            if self._vfs:
                result = self._vfs.search(args["query"], args.get("path", "/"))
                if result.success:
                    items = [{"path": n.path, "name": n.name} for n in (result.data or [])]
                    return {"query": args["query"], "results": items, "count": len(items)}, []
                return {"error": result.error or "search failed"}, []
            return {"error": "VFS not available"}, []

        elif tool_name == "vfs_write":
            if self._vfs:
                result = self._vfs.write(args["path"], args["content"])
                if result.success:
                    return {"path": args["path"], "status": "written"}, []
                return {"error": result.error or "write failed"}, []
            return {"error": "VFS not available"}, []

        else:
            return {"error": f"Unknown tool: {tool_name}"}, []


def _extract_source_files(result: dict) -> list[str]:
    sources = []
    if isinstance(result, dict):
        sf = result.get("source_file", "")
        if sf:
            sources.append(sf)
    return sources


def _summarize(result: Any) -> str:
    """Short summary of a tool result for the traversal log."""
    if isinstance(result, dict):
        if "error" in result:
            return f"error: {result['error']}"
        if "relationships" in result:
            return f"{len(result['relationships'])} relationships found"
        if "path" in result and isinstance(result["path"], list):
            nodes = [s["node"] for s in result["path"]]
            return " → ".join(nodes)
        if "results" in result:
            return f"{result.get('count', len(result['results']))} results"
        if "content" in result:
            return f"read {result.get('path', 'file')} ({len(result['content'])} chars)"
    if isinstance(result, list):
        return f"{len(result)} items"
    return str(result)[:100]
