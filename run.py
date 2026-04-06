#!/usr/bin/env python3
"""
Knowledge Graph — Conceptual Graph Engine
Inspired by: arXiv:2512.05470 (Everything is Context)

Usage:
  python run.py build               Build graph from docs/ directory
  python run.py build --no-llm      Build using heuristic extractor (no API key needed)
  python run.py stats               Print graph statistics
  python run.py query "..."         One-shot concept query
  python run.py connect A B         Find path between two concepts
  python run.py nodes <type>        List nodes by type (APIObject, Endpoint, Event, Concept, Document)
  python run.py chat                Interactive agent chat (requires OPENROUTER_API_KEY)
  python run.py search "..."        Keyword search across files
  python run.py export              Print graph JSON
"""
import argparse
import json
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"
GRAPH_PATH = Path(__file__).parent / "data" / "graph.json"
DATA_DIR = Path(__file__).parent / "data"


def _create_system_fs():
    """Create a SystemFS instance with standard mounts."""
    from systemfs.vfs import SystemFS
    from systemfs.resolvers.docs import DocsResolver
    from systemfs.resolvers.graph import GraphResolver
    from systemfs.resolvers.memory import MemoryResolver
    from systemfs.resolvers.module import ModuleResolver
    from systemfs.context.history import HistoryLayer

    vfs = SystemFS()
    vfs.mount("/docs/", DocsResolver(DOCS_DIR))
    if GRAPH_PATH.exists():
        from kgraph.graph import ConceptGraph
        graph = ConceptGraph.load(GRAPH_PATH)
        vfs.mount("/graph/", GraphResolver(graph))
    vfs.mount("/context/memory/", MemoryResolver(DATA_DIR))
    vfs.mount("/modules/", ModuleResolver())

    history = HistoryLayer(DATA_DIR)
    history.start_session()
    vfs.attach_history(history)

    return vfs


def cmd_build(args):
    from kgraph.builder import GraphBuilder
    use_llm = not args.no_llm
    builder = GraphBuilder(DOCS_DIR, use_llm=use_llm)
    graph = builder.build(verbose=True)
    graph.save(GRAPH_PATH)
    print(f"\nGraph saved to {GRAPH_PATH}")


def cmd_stats(args):
    graph = _load_graph()
    stats = graph.stats()
    print("\nGraph Statistics")
    print("=" * 40)
    print(f"  Total nodes : {stats['total_nodes']}")
    print(f"  Total edges : {stats['total_edges']}")
    print("\nNodes by type:")
    for t, count in sorted(stats["nodes_by_type"].items()):
        print(f"  {t:<20} {count}")
    print("\nEdges by type:")
    for t, count in sorted(stats["edges_by_type"].items()):
        print(f"  {t:<20} {count}")


def cmd_query(args):
    from kgraph.query import GraphQuery
    graph = _load_graph()
    gq = GraphQuery(graph)
    result = gq.related_concepts(args.concept)
    _print_json(result)


def cmd_connect(args):
    from kgraph.query import GraphQuery
    graph = _load_graph()
    gq = GraphQuery(graph)
    result = gq.find_connection(args.source, args.target)
    _print_json(result)


def cmd_nodes(args):
    from kgraph.query import GraphQuery
    graph = _load_graph()
    gq = GraphQuery(graph)
    result = gq.concepts_by_type(args.type)
    _print_json(result)


def cmd_search(args):
    from kgraph.filesystem import FileSystem
    fs = FileSystem(DOCS_DIR)
    results = fs.search(args.query)
    if not results:
        print(f"No results for '{args.query}'")
        return
    for r in results:
        print(f"\n[{r['path']}] {r['title']} ({r['match_count']} matches)")
        for snippet in r["snippets"]:
            print(f"  ...{snippet}...")


def cmd_vfs(args):
    """Dispatch VFS subcommands."""
    vfs = _create_system_fs()
    action = args.vfs_action

    if action == "list":
        result = vfs.list(args.path or "/")
        if result.success:
            items = result.data or []
            if not items:
                print("(empty)")
            for node in items:
                prefix = "/" if node.kind == "directory" else " "
                print(f"  {prefix} {node.path}")
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            sys.exit(1)

    elif action == "read":
        result = vfs.read(args.path)
        if result.success and result.data:
            print(result.data.content or "(no content)")
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            sys.exit(1)

    elif action == "search":
        result = vfs.search(args.query, args.path or "/")
        if result.success:
            items = result.data or []
            if not items:
                print(f"No results for '{args.query}'")
            for node in items:
                print(f"  {node.path}")
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            sys.exit(1)

    elif action == "mounts":
        mounts = vfs.list_mounts()
        print("\nMounted resolvers:")
        for mp, name in sorted(mounts.items()):
            print(f"  {mp:<30} [{name}]")


def cmd_context(args):
    """Dispatch context subcommands."""
    action = args.context_action

    if action == "history":
        from systemfs.context.history import HistoryLayer
        history = HistoryLayer(DATA_DIR)
        entries = history.query_history(limit=args.limit)
        if not entries:
            print("No history entries found.")
            return
        print(f"\nLast {len(entries)} history entries:")
        for e in entries:
            ts = str(e.timestamp)[:19]
            path_str = f" [{e.path}]" if e.path else ""
            print(f"  {ts}  [{e.event_type}] {e.actor}{path_str}")

    elif action == "memory":
        from systemfs.resolvers.memory import MemoryResolver
        mem = MemoryResolver(DATA_DIR)
        result = mem.list(f"/{args.type}/" if args.type else "/")
        if result.success:
            items = result.data or []
            if not items:
                print("No memory entries found.")
            for node in items:
                print(f"  {node.path}")
        else:
            print(f"Error: {result.error}", file=sys.stderr)


def cmd_chat(args):
    from kgraph.query import GraphQuery
    from kgraph.filesystem import FileSystem
    from kgraph.agent import AgentToolkit

    vfs = _create_system_fs()
    agent = AgentToolkit(system_fs=vfs)

    print("Knowledge Graph Agent (graph + filesystem hybrid)")
    print("Type your question or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        print("\nAgent is thinking...\n")
        response = agent.chat(user_input)

        print("─" * 60)
        print(f"Answer:\n{response['answer']}")

        if response["traversal_log"]:
            print("\nTraversal log:")
            for step in response["traversal_log"]:
                print(f"  [{step['tool']}] {step['args']} → {step['result_summary']}")

        if response["sources"]:
            print(f"\nSources: {', '.join(response['sources'])}")

        print("─" * 60 + "\n")


def cmd_export(args):
    graph = _load_graph()
    print(json.dumps(graph.to_json(), indent=2))


def _load_graph():
    from kgraph.graph import ConceptGraph
    if not GRAPH_PATH.exists():
        print(f"Graph not found at {GRAPH_PATH}. Run 'python run.py build' first.")
        sys.exit(1)
    return ConceptGraph.load(GRAPH_PATH)


def _print_json(data):
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Nia Docs — Hybrid Filesystem + Conceptual Graph Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build the conceptual graph from docs")
    p_build.add_argument("--no-llm", action="store_true", help="Use heuristic extractor (no API key needed)")
    p_build.set_defaults(func=cmd_build)

    # stats
    p_stats = subparsers.add_parser("stats", help="Print graph statistics")
    p_stats.set_defaults(func=cmd_stats)

    # query
    p_query = subparsers.add_parser("query", help="Get related concepts for an entity")
    p_query.add_argument("concept", help="Entity name (e.g. Charge)")
    p_query.set_defaults(func=cmd_query)

    # connect
    p_connect = subparsers.add_parser("connect", help="Find path between two concepts")
    p_connect.add_argument("source", help="Source concept")
    p_connect.add_argument("target", help="Target concept")
    p_connect.set_defaults(func=cmd_connect)

    # nodes
    p_nodes = subparsers.add_parser("nodes", help="List all nodes of a given type")
    p_nodes.add_argument("type", choices=["APIObject", "Endpoint", "Event", "Concept", "Document"])
    p_nodes.set_defaults(func=cmd_nodes)

    # search
    p_search = subparsers.add_parser("search", help="Keyword search across docs")
    p_search.add_argument("query", help="Search term")
    p_search.set_defaults(func=cmd_search)

    # chat
    p_chat = subparsers.add_parser("chat", help="Interactive agent chat")
    p_chat.set_defaults(func=cmd_chat)

    # export
    p_export = subparsers.add_parser("export", help="Print graph JSON to stdout")
    p_export.set_defaults(func=cmd_export)

    # vfs subcommand group
    p_vfs = subparsers.add_parser("vfs", help="Virtual File System operations")
    vfs_sub = p_vfs.add_subparsers(dest="vfs_action", required=True)

    p_vfs_list = vfs_sub.add_parser("list", help="List VFS directory")
    p_vfs_list.add_argument("path", nargs="?", default="/", help="VFS path (default: /)")

    p_vfs_read = vfs_sub.add_parser("read", help="Read VFS file")
    p_vfs_read.add_argument("path", help="VFS path")

    p_vfs_search = vfs_sub.add_parser("search", help="Search VFS")
    p_vfs_search.add_argument("query", help="Search query")
    p_vfs_search.add_argument("path", nargs="?", default="/", help="Scope path (default: /)")

    p_vfs_mounts = vfs_sub.add_parser("mounts", help="List mounted resolvers")

    p_vfs.set_defaults(func=cmd_vfs)

    # context subcommand group
    p_ctx = subparsers.add_parser("context", help="Context layer operations")
    ctx_sub = p_ctx.add_subparsers(dest="context_action", required=True)

    p_ctx_hist = ctx_sub.add_parser("history", help="Show recent history")
    p_ctx_hist.add_argument("--limit", type=int, default=20, help="Max entries to show")

    p_ctx_mem = ctx_sub.add_parser("memory", help="List memory entries")
    p_ctx_mem.add_argument("type", nargs="?", choices=["fact", "episodic", "procedural"],
                            help="Filter by memory type")

    p_ctx.set_defaults(func=cmd_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
