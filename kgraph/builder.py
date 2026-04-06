"""
GraphBuilder — orchestrates doc extraction and assembles the ConceptGraph.
"""
from pathlib import Path

from .graph import ConceptGraph
from .schema import ExtractionResult


class GraphBuilder:
    """
    Walks a docs directory, extracts concepts from each file,
    and merges them into a single ConceptGraph.
    """

    def __init__(self, docs_root: str | Path, use_llm: bool = True):
        self.docs_root = Path(docs_root)
        self.use_llm = use_llm

    def build(self, verbose: bool = True) -> ConceptGraph:
        """Build and return a ConceptGraph from all docs."""
        graph = ConceptGraph()
        doc_files = sorted(self.docs_root.rglob("*.md"))

        if not doc_files:
            raise FileNotFoundError(f"No markdown files found in {self.docs_root}")

        if verbose:
            mode = "LLM" if self.use_llm else "heuristic"
            print(f"Building graph from {len(doc_files)} files using {mode} extractor...")

        for doc in doc_files:
            if verbose:
                print(f"  Extracting: {doc.relative_to(self.docs_root)}")
            result = self._extract(doc)
            self._merge(graph, result)

        if verbose:
            stats = graph.stats()
            print(f"\nGraph built: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
            print("  Nodes by type:", stats["nodes_by_type"])
            print("  Edges by type:", stats["edges_by_type"])

        return graph

    def _extract(self, path: Path) -> ExtractionResult:
        if self.use_llm:
            from . import extractor_llm
            return extractor_llm.extract(path)
        else:
            from . import extractor_heuristic
            return extractor_heuristic.extract(path)

    def _merge(self, graph: ConceptGraph, result: ExtractionResult) -> None:
        for node in result.nodes:
            graph.add_node(node)
        for edge in result.edges:
            if edge.source and edge.target:
                graph.add_edge(edge)
