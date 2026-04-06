"""
GraphQuery — high-level query interface for the ConceptGraph.
Provides traversal, pathfinding, and context-gathering operations.
"""
from typing import Any

from .graph import ConceptGraph
from .schema import NodeType


class GraphQuery:
    """
    High-level query layer on top of ConceptGraph.
    Methods return structured dicts suitable for agent tool consumption.
    """

    def __init__(self, graph: ConceptGraph):
        self.graph = graph

    def related_concepts(self, entity: str, max_results: int = 10) -> dict[str, Any]:
        """
        Return all neighbors of an entity with relationship details.
        Equivalent to 'navigate' in the filesystem metaphor.
        """
        node = self.graph.get_node(entity)
        if node is None:
            return {"error": f"Entity '{entity}' not found in graph.", "suggestions": self.graph.search(entity)[:5]}

        neighbors = self.graph.get_neighbors(entity)[:max_results]
        return {
            "entity": node["name"],
            "type": node.get("type"),
            "description": node.get("description"),
            "source_file": node.get("source_file"),
            "relationships": [
                {
                    "node": n["node"],
                    "type": n["node_data"].get("type"),
                    "edge_type": n["edge_type"],
                    "direction": n["direction"],
                    "weight": n["weight"],
                }
                for n in neighbors
            ],
        }

    def find_connection(self, source: str, target: str) -> dict[str, Any]:
        """
        Find the shortest conceptual path between two entities.
        Explains how source connects to target through the graph.
        """
        path = self.graph.find_path(source, target)
        if path is None:
            return {
                "error": f"No connection found between '{source}' and '{target}'.",
                "hint": "These concepts may be in separate components of the graph.",
            }
        return {
            "source": source,
            "target": target,
            "path_length": len(path) - 1,
            "path": [
                {
                    "node": step["node"],
                    "type": step["node_data"].get("type", ""),
                    "edge_to_next": step.get("edge_to_next"),
                }
                for step in path
            ],
        }

    def explain_node(self, entity: str) -> dict[str, Any]:
        """
        Full context for a node: description, source file, all relationships.
        Equivalent to 'inspect' / 'cat' in the filesystem metaphor.
        """
        node = self.graph.get_node(entity)
        if node is None:
            return {"error": f"Entity '{entity}' not found.", "suggestions": self.graph.search(entity)[:3]}

        all_neighbors = self.graph.get_neighbors(entity)
        outgoing = [n for n in all_neighbors if n["direction"] == "out"]
        incoming = [n for n in all_neighbors if n["direction"] == "in"]

        return {
            "entity": node["name"],
            "type": node.get("type"),
            "description": node.get("description"),
            "source_file": node.get("source_file"),
            "outgoing_relationships": [
                {"to": n["node"], "edge_type": n["edge_type"], "weight": n["weight"]}
                for n in outgoing
            ],
            "incoming_relationships": [
                {"from": n["node"], "edge_type": n["edge_type"], "weight": n["weight"]}
                for n in incoming
            ],
        }

    def concepts_by_type(self, node_type: str) -> dict[str, Any]:
        """
        List all entities of a given type.
        Valid types: Document, APIObject, Endpoint, Event, Concept
        """
        try:
            ntype = NodeType(node_type)
        except ValueError:
            valid = [t.value for t in NodeType]
            return {"error": f"Invalid type '{node_type}'. Valid types: {valid}"}

        nodes = self.graph.nodes_by_type(ntype)
        return {
            "type": node_type,
            "count": len(nodes),
            "entities": [
                {"name": n["name"], "description": n.get("description", ""), "source_file": n.get("source_file", "")}
                for n in nodes
            ],
        }

    def search_graph(self, query: str) -> dict[str, Any]:
        """
        Fuzzy name/description search across all graph nodes.
        """
        matches = self.graph.search(query)
        return {
            "query": query,
            "count": len(matches),
            "results": [
                {
                    "name": m["name"],
                    "type": m.get("type"),
                    "description": m.get("description", ""),
                    "source_file": m.get("source_file", ""),
                    "score": m["score"],
                }
                for m in matches[:10]
            ],
        }

    def subgraph_context(self, entity: str, depth: int = 2) -> dict[str, Any]:
        """
        Return the local neighborhood of an entity up to `depth` hops.
        Useful for building context windows for LLM reasoning.
        """
        sub = self.graph.subgraph(entity, depth)
        stats = sub.stats()
        node_data = sub._g.nodes(data=True)
        return {
            "center": entity,
            "depth": depth,
            "stats": stats,
            "nodes": [
                {"name": n, "type": d.get("type"), "description": d.get("description", "")}
                for n, d in node_data
            ],
        }

    def graph_stats(self) -> dict[str, Any]:
        """Return overall graph statistics."""
        return self.graph.stats()
