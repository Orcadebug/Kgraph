"""GraphResolver — wraps ConceptGraph + GraphQuery."""
from __future__ import annotations
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from typing import Any
from ..base import BaseResolver
from ..models import VFSNode, VFSResult, VFSOperation, NodeKind, Provenance

from kgraph.graph import ConceptGraph
from kgraph.query import GraphQuery


class GraphResolver(BaseResolver):
    """Adapts the knowledge graph into the VFS hierarchy."""

    _name = "graph"

    def __init__(self, graph: ConceptGraph):
        self._graph = graph
        self._query = GraphQuery(graph)

    @property
    def name(self) -> str:
        return self._name

    @property
    def readonly(self) -> bool:
        return True

    def read(self, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]

        if not parts or path.strip("/") == "":
            return self.list(path)

        if parts == ["stats"]:
            data = self._graph.stats()
            content = json.dumps(data, indent=2)
            node = VFSNode(path="/graph/stats", kind=NodeKind.VIRTUAL, name="stats",
                           content=content, size=len(content),
                           provenance=Provenance(source="graph", origin_path="stats"))
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)

        if len(parts) == 2 and parts[0] == "nodes":
            node_name = parts[1]
            result = self._query.explain_node(node_name)
            if "error" in result:
                return VFSResult(success=False, operation=VFSOperation.READ,
                                 path=path, error=result["error"])
            content = json.dumps(result, indent=2)
            node = VFSNode(path=f"/graph/nodes/{node_name}", kind=NodeKind.VIRTUAL, name=node_name,
                           content=content, size=len(content),
                           provenance=Provenance(source="graph", origin_path=f"nodes/{node_name}"))
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)

        if len(parts) == 2 and parts[0] == "edges":
            edge_key = parts[1]
            if "--" not in edge_key:
                return VFSResult(success=False, operation=VFSOperation.READ,
                                 path=path, error=f"Invalid edge key: {edge_key} (expected 'Source--Target')")
            src, tgt = edge_key.split("--", 1)
            edge_data = self._graph._g.get_edge_data(src, tgt) or self._graph._g.get_edge_data(tgt, src)
            if edge_data is None:
                return VFSResult(success=False, operation=VFSOperation.READ,
                                 path=path, error=f"Edge not found: {src} -- {tgt}")
            content = json.dumps({"source": src, "target": tgt, **edge_data}, indent=2)
            node = VFSNode(path=f"/graph/edges/{edge_key}", kind=NodeKind.VIRTUAL, name=edge_key,
                           content=content, size=len(content),
                           provenance=Provenance(source="graph", origin_path=f"edges/{edge_key}"))
            return VFSResult(success=True, operation=VFSOperation.READ, path=path, data=node)

        return VFSResult(success=False, operation=VFSOperation.READ,
                         path=path, error=f"Unknown graph path: {path}")

    def write(self, path: str, content: str, metadata: dict[str, Any] | None = None) -> VFSResult:
        return VFSResult(success=False, operation=VFSOperation.WRITE,
                         path=path, error="graph resolver is read-only")

    def list(self, path: str) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]

        if not parts:
            root_nodes = [
                VFSNode(path="/graph/nodes/", kind=NodeKind.DIRECTORY, name="nodes"),
                VFSNode(path="/graph/edges/", kind=NodeKind.DIRECTORY, name="edges"),
                VFSNode(path="/graph/stats", kind=NodeKind.VIRTUAL, name="stats"),
            ]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=root_nodes)

        if parts == ["nodes"]:
            nodes = [
                VFSNode(path=f"/graph/nodes/{n}", kind=NodeKind.VIRTUAL, name=n)
                for n in sorted(self._graph._g.nodes())
            ]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)

        if parts == ["edges"]:
            nodes = [
                VFSNode(path=f"/graph/edges/{u}--{v}", kind=NodeKind.VIRTUAL, name=f"{u}--{v}")
                for u, v in sorted(self._graph._g.edges())
            ]
            return VFSResult(success=True, operation=VFSOperation.LIST, path=path, data=nodes)

        return VFSResult(success=False, operation=VFSOperation.LIST,
                         path=path, error=f"Unknown graph path: {path}")

    def search(self, query: str, path: str = "/", max_results: int = 10) -> VFSResult:
        result = self._query.search_graph(query)
        nodes = [
            VFSNode(
                path=f"/graph/nodes/{r['name']}", kind=NodeKind.VIRTUAL, name=r["name"],
                metadata={"type": r.get("type"), "description": r.get("description", "")},
                provenance=Provenance(source="graph", origin_path=f"nodes/{r['name']}",
                                      confidence=r.get("score", 1.0)),
            )
            for r in result.get("results", [])
        ]
        return VFSResult(success=True, operation=VFSOperation.SEARCH, path=path, data=nodes[:max_results])

    def exec(self, path: str, args: dict[str, Any] | None = None) -> VFSResult:
        parts = [p for p in path.strip("/").split("/") if p]
        if parts != ["query"] and path.strip("/") != "query":
            return VFSResult(success=False, operation=VFSOperation.EXEC,
                             path=path, error=f"exec only supported at /graph/query, got: {path}")
        if not args:
            return VFSResult(success=False, operation=VFSOperation.EXEC,
                             path=path, error="exec requires args dict with 'operation' key")

        op = args.get("operation")
        if op == "find_path":
            data = self._query.find_connection(args["source"], args["target"])
        elif op == "subgraph":
            data = self._query.subgraph_context(args["center"], args.get("depth", 2))
        elif op == "related_concepts":
            data = self._query.related_concepts(args["entity"])
        elif op == "explain":
            data = self._query.explain_node(args["entity"])
        elif op == "stats":
            data = self._query.graph_stats()
        else:
            return VFSResult(success=False, operation=VFSOperation.EXEC,
                             path=path, error=f"Unknown operation: {op}")

        content = json.dumps(data, indent=2)
        node = VFSNode(path=f"/graph/query", kind=NodeKind.VIRTUAL, name="query",
                       content=content, metadata={"operation": op, "args": args})
        return VFSResult(success=True, operation=VFSOperation.EXEC, path=path, data=node)
