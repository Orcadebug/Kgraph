"""
ConceptGraph — NetworkX-backed knowledge graph for document concepts.
"""
import json
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

from .schema import NodeModel, EdgeModel, NodeType, EdgeType


class ConceptGraph:
    """
    Bidirectional conceptual graph combining document entities and relationships.
    Nodes: documents, API objects, endpoints, events, concepts.
    Edges: typed relationships (requires, returns, triggers, belongs_to, etc.).
    """

    def __init__(self):
        self._g: nx.DiGraph = nx.DiGraph()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_node(self, node: NodeModel) -> None:
        """Add or update a node. Merges if already present."""
        name = self._normalize(node.name)
        if self._g.has_node(name):
            # Merge: update description/source if existing is empty
            existing = self._g.nodes[name]
            if not existing.get("description") and node.description:
                existing["description"] = node.description
            if not existing.get("source_file") and node.source_file:
                existing["source_file"] = node.source_file
        else:
            self._g.add_node(
                name,
                type=node.type.value,
                description=node.description,
                source_file=node.source_file,
                properties=node.properties,
            )

    def add_edge(self, edge: EdgeModel) -> None:
        """Add or strengthen a typed edge."""
        src = self._normalize(edge.source)
        tgt = self._normalize(edge.target)
        # Auto-create nodes if missing
        for n in (src, tgt):
            if not self._g.has_node(n):
                self._g.add_node(n, type=NodeType.CONCEPT.value, description="", source_file="", properties={})
        if self._g.has_edge(src, tgt):
            # Strengthen existing edge weight
            self._g[src][tgt]["weight"] = min(
                self._g[src][tgt].get("weight", 1.0) + 0.5, 5.0
            )
        else:
            self._g.add_edge(
                src,
                tgt,
                edge_type=edge.edge_type.value,
                weight=edge.weight,
                source_file=edge.source_file,
            )

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_node(self, name: str) -> dict[str, Any] | None:
        key = self._normalize(name)
        if not self._g.has_node(key):
            return None
        data = dict(self._g.nodes[key])
        data["name"] = key
        return data

    def get_neighbors(
        self, name: str, edge_type: str | None = None, direction: str = "both"
    ) -> list[dict[str, Any]]:
        """
        Return neighbors with edge metadata.
        direction: 'out' (successors), 'in' (predecessors), 'both'.
        """
        key = self._normalize(name)
        if not self._g.has_node(key):
            return []

        results: list[dict] = []

        if direction in ("out", "both"):
            for _, tgt, edata in self._g.out_edges(key, data=True):
                if edge_type and edata.get("edge_type") != edge_type:
                    continue
                results.append({
                    "node": tgt,
                    "node_data": dict(self._g.nodes[tgt]),
                    "edge_type": edata.get("edge_type"),
                    "weight": edata.get("weight", 1.0),
                    "direction": "out",
                })

        if direction in ("in", "both"):
            for src, _, edata in self._g.in_edges(key, data=True):
                if edge_type and edata.get("edge_type") != edge_type:
                    continue
                results.append({
                    "node": src,
                    "node_data": dict(self._g.nodes[src]),
                    "edge_type": edata.get("edge_type"),
                    "weight": edata.get("weight", 1.0),
                    "direction": "in",
                })

        return sorted(results, key=lambda x: x["weight"], reverse=True)

    def find_path(self, source: str, target: str) -> list[dict[str, Any]] | None:
        """
        Find the shortest path between two concepts.
        Returns list of {node, edge_to_next} dicts, or None if no path.
        """
        src = self._normalize(source)
        tgt = self._normalize(target)
        try:
            path_nodes = nx.shortest_path(self._g.to_undirected(), src, tgt)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        result = []
        for i, node in enumerate(path_nodes):
            entry: dict[str, Any] = {
                "node": node,
                "node_data": dict(self._g.nodes.get(node, {})),
            }
            if i < len(path_nodes) - 1:
                nxt = path_nodes[i + 1]
                if self._g.has_edge(node, nxt):
                    entry["edge_to_next"] = self._g[node][nxt].get("edge_type", "references")
                elif self._g.has_edge(nxt, node):
                    entry["edge_to_next"] = self._g[nxt][node].get("edge_type", "references")
                else:
                    entry["edge_to_next"] = "references"
            result.append(entry)
        return result

    def subgraph(self, center: str, depth: int = 2) -> "ConceptGraph":
        """Return a new ConceptGraph containing the BFS neighborhood of center."""
        key = self._normalize(center)
        if not self._g.has_node(key):
            return ConceptGraph()
        undirected = self._g.to_undirected()
        nodes_at_depth = nx.single_source_shortest_path_length(undirected, key, cutoff=depth)
        sub = self._g.subgraph(nodes_at_depth.keys()).copy()
        result = ConceptGraph()
        result._g = sub
        return result

    def nodes_by_type(self, node_type: NodeType) -> list[dict[str, Any]]:
        """Return all nodes of a given type."""
        return [
            {"name": n, **dict(data)}
            for n, data in self._g.nodes(data=True)
            if data.get("type") == node_type.value
        ]

    def search(self, query: str) -> list[dict[str, Any]]:
        """Fuzzy name search across all nodes."""
        q = query.lower()
        matches = []
        for name, data in self._g.nodes(data=True):
            score = 0
            if q in name.lower():
                score += 2
            if q in data.get("description", "").lower():
                score += 1
            if score > 0:
                matches.append({"name": name, "score": score, **dict(data)})
        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def stats(self) -> dict[str, Any]:
        """Return graph statistics."""
        type_counts: dict[str, int] = {}
        edge_type_counts: dict[str, int] = {}
        for _, data in self._g.nodes(data=True):
            t = data.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        for _, _, data in self._g.edges(data=True):
            et = data.get("edge_type", "unknown")
            edge_type_counts[et] = edge_type_counts.get(et, 0) + 1
        return {
            "total_nodes": self._g.number_of_nodes(),
            "total_edges": self._g.number_of_edges(),
            "nodes_by_type": type_counts,
            "edges_by_type": edge_type_counts,
        }

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_json(self) -> dict:
        return json_graph.node_link_data(self._g, edges="links")

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "ConceptGraph":
        with open(path) as f:
            data = json.load(f)
        g = cls()
        g._g = json_graph.node_link_graph(data, edges="links", directed=True, multigraph=False)
        return g

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().title()
