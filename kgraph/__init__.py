"""
kgraph — Conceptual Graph Engine for Document Navigation
"""
from .graph import ConceptGraph
from .builder import GraphBuilder
from .query import GraphQuery
from .filesystem import FileSystem
from .agent import AgentToolkit


def create_system_fs(docs_dir=None, graph_path=None, data_dir=None):
    """
    Factory: create a SystemFS with standard mounts.

    Args:
        docs_dir: Path to docs directory (default: ./docs)
        graph_path: Path to graph.json (default: ./data/graph.json)
        data_dir: Path to data directory (default: ./data)
    """
    from pathlib import Path
    from systemfs.vfs import SystemFS
    from systemfs.resolvers.docs import DocsResolver
    from systemfs.resolvers.memory import MemoryResolver
    from systemfs.resolvers.module import ModuleResolver

    base = Path(__file__).parent.parent
    docs = Path(docs_dir) if docs_dir else base / "docs"
    graph_file = Path(graph_path) if graph_path else base / "data" / "graph.json"
    data = Path(data_dir) if data_dir else base / "data"

    vfs = SystemFS()
    vfs.mount("/docs/", DocsResolver(docs))

    if graph_file.exists():
        from systemfs.resolvers.graph import GraphResolver
        from kgraph.graph import ConceptGraph
        graph = ConceptGraph.load(graph_file)
        vfs.mount("/graph/", GraphResolver(graph))

    vfs.mount("/context/memory/", MemoryResolver(data))
    vfs.mount("/modules/", ModuleResolver())
    return vfs


__all__ = ["ConceptGraph", "GraphBuilder", "GraphQuery", "FileSystem", "AgentToolkit",
           "create_system_fs"]
