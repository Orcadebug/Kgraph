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


def cmd_chat(args):
    from kgraph.query import GraphQuery
    from kgraph.filesystem import FileSystem
    from kgraph.agent import AgentToolkit

    graph = _load_graph()
    gq = GraphQuery(graph)
    fs = FileSystem(DOCS_DIR)
    agent = AgentToolkit(gq, fs)

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
