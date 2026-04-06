"""Tests for GraphResolver."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kgraph.graph import ConceptGraph
from kgraph.schema import NodeModel, EdgeModel, NodeType, EdgeType
from systemfs.resolvers.graph import GraphResolver
from systemfs.models import NodeKind, VFSOperation


@pytest.fixture
def graph():
    g = ConceptGraph()
    g.add_node(NodeModel(name="Charge", type=NodeType.API_OBJECT, description="A payment charge"))
    g.add_node(NodeModel(name="Customer", type=NodeType.API_OBJECT, description="A customer"))
    g.add_edge(EdgeModel(source="Charge", target="Customer", edge_type=EdgeType.REQUIRES))
    return g


@pytest.fixture
def resolver(graph):
    return GraphResolver(graph)


def test_list_root(resolver):
    r = resolver.list("/")
    assert r.success
    names = {n.name for n in r.data}
    assert "nodes" in names
    assert "edges" in names
    assert "stats" in names


def test_list_nodes(resolver):
    r = resolver.list("/nodes/")
    assert r.success
    names = {n.name for n in r.data}
    assert "Charge" in names
    assert "Customer" in names


def test_read_node(resolver):
    r = resolver.read("/nodes/Charge")
    assert r.success
    assert "Charge" in r.data.content


def test_read_stats(resolver):
    r = resolver.read("/stats")
    assert r.success
    import json
    data = json.loads(r.data.content)
    assert "total_nodes" in data


def test_search(resolver):
    r = resolver.search("charge")
    assert r.success


def test_exec_related_concepts(resolver):
    r = resolver.exec("/query", {"operation": "related_concepts", "entity": "Charge"})
    assert r.success


def test_exec_find_path(resolver):
    r = resolver.exec("/query", {"operation": "find_path", "source": "Charge", "target": "Customer"})
    assert r.success


def test_write_rejected(resolver):
    r = resolver.write("/nodes/Charge", "data")
    assert not r.success
    assert "read-only" in r.error


def test_exec_unknown_op(resolver):
    r = resolver.exec("/query", {"operation": "unknown_op"})
    assert not r.success
