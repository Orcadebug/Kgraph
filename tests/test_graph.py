"""Tests for ConceptGraph core operations."""
import pytest
from nia.graph import ConceptGraph
from nia.schema import NodeModel, EdgeModel, NodeType, EdgeType


@pytest.fixture
def graph():
    g = ConceptGraph()
    g.add_node(NodeModel(name="Charge", type=NodeType.API_OBJECT, description="A payment attempt"))
    g.add_node(NodeModel(name="Customer", type=NodeType.API_OBJECT, description="A buyer"))
    g.add_node(NodeModel(name="PaymentMethod", type=NodeType.API_OBJECT, description="A card or bank"))
    g.add_node(NodeModel(name="Invoice", type=NodeType.API_OBJECT, description="A billing record"))
    g.add_node(NodeModel(name="charge.succeeded", type=NodeType.EVENT, description="Charge success event"))
    g.add_edge(EdgeModel(source="Charge", target="Customer", edge_type=EdgeType.REQUIRES))
    g.add_edge(EdgeModel(source="Charge", target="PaymentMethod", edge_type=EdgeType.REQUIRES))
    g.add_edge(EdgeModel(source="Charge", target="charge.succeeded", edge_type=EdgeType.TRIGGERS))
    g.add_edge(EdgeModel(source="PaymentMethod", target="Customer", edge_type=EdgeType.BELONGS_TO))
    g.add_edge(EdgeModel(source="Invoice", target="Charge", edge_type=EdgeType.GENERATES))
    return g


def test_add_and_get_node(graph):
    node = graph.get_node("Charge")
    assert node is not None
    assert node["type"] == NodeType.API_OBJECT.value
    assert "payment" in node["description"].lower()


def test_node_normalization(graph):
    # Both forms should resolve to the same node
    assert graph.get_node("charge") is not None
    assert graph.get_node("CHARGE") is not None


def test_get_neighbors_outgoing(graph):
    neighbors = graph.get_neighbors("Charge", direction="out")
    names = {n["node"] for n in neighbors}
    assert "Customer" in names
    assert "Paymentmethod" in names or "PaymentMethod".title() in names


def test_get_neighbors_incoming(graph):
    neighbors = graph.get_neighbors("Charge", direction="in")
    names = {n["node"] for n in neighbors}
    assert "Invoice" in names


def test_find_path(graph):
    path = graph.find_path("Invoice", "Customer")
    assert path is not None
    node_names = [step["node"] for step in path]
    assert "Invoice" in node_names
    assert "Customer" in node_names


def test_find_path_no_connection(graph):
    # Disconnected node
    graph.add_node(NodeModel(name="Orphan", type=NodeType.CONCEPT))
    path = graph.find_path("Orphan", "Charge")
    assert path is None


def test_nodes_by_type(graph):
    api_objects = graph.nodes_by_type(NodeType.API_OBJECT)
    names = {n["name"] for n in api_objects}
    assert "Charge" in names
    assert "Customer" in names


def test_search(graph):
    results = graph.search("payment")
    assert len(results) > 0
    names = {r["name"] for r in results}
    # PaymentMethod should match 'payment'
    assert any("Payment" in n for n in names)


def test_edge_strengthening(graph):
    # Adding same edge twice should increase weight
    before = graph._g["Charge"]["Customer"]["weight"]
    graph.add_edge(EdgeModel(source="Charge", target="Customer", edge_type=EdgeType.REQUIRES))
    after = graph._g["Charge"]["Customer"]["weight"]
    assert after > before


def test_stats(graph):
    stats = graph.stats()
    assert stats["total_nodes"] >= 5
    assert stats["total_edges"] >= 5
    assert "APIObject" in stats["nodes_by_type"]
    assert "requires" in stats["edges_by_type"]


def test_serialize_roundtrip(graph, tmp_path):
    save_path = tmp_path / "test_graph.json"
    graph.save(save_path)
    loaded = ConceptGraph.load(save_path)
    assert loaded.get_node("Charge") is not None
    assert loaded.stats()["total_nodes"] == graph.stats()["total_nodes"]


def test_subgraph(graph):
    sub = graph.subgraph("Charge", depth=1)
    node_names = set(sub._g.nodes())
    assert "Charge" in node_names
    assert "Customer" in node_names
