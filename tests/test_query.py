"""Tests for GraphQuery interface."""
import pytest
from nia.graph import ConceptGraph
from nia.query import GraphQuery
from nia.schema import NodeModel, EdgeModel, NodeType, EdgeType


@pytest.fixture
def gq():
    g = ConceptGraph()
    for name, ntype in [
        ("Charge", NodeType.API_OBJECT),
        ("Customer", NodeType.API_OBJECT),
        ("PaymentMethod", NodeType.API_OBJECT),
        ("Invoice", NodeType.API_OBJECT),
        ("Subscription", NodeType.API_OBJECT),
        ("charge.succeeded", NodeType.EVENT),
    ]:
        g.add_node(NodeModel(name=name, type=ntype, description=f"A {name}"))

    edges = [
        ("Charge", "Customer", EdgeType.REQUIRES),
        ("Charge", "PaymentMethod", EdgeType.REQUIRES),
        ("Charge", "charge.succeeded", EdgeType.TRIGGERS),
        ("PaymentMethod", "Customer", EdgeType.BELONGS_TO),
        ("Invoice", "Charge", EdgeType.GENERATES),
        ("Subscription", "Invoice", EdgeType.GENERATES),
        ("Subscription", "Customer", EdgeType.BELONGS_TO),
    ]
    for src, tgt, et in edges:
        g.add_edge(EdgeModel(source=src, target=tgt, edge_type=et))

    return GraphQuery(g)


def test_related_concepts_found(gq):
    result = gq.related_concepts("Charge")
    assert "error" not in result
    assert result["entity"] == "Charge"
    rel_nodes = {r["node"] for r in result["relationships"]}
    assert "Customer" in rel_nodes


def test_related_concepts_not_found(gq):
    result = gq.related_concepts("Nonexistent")
    assert "error" in result
    assert "suggestions" in result


def test_find_connection_direct(gq):
    result = gq.find_connection("Charge", "Customer")
    assert "error" not in result
    assert result["path_length"] >= 1


def test_find_connection_indirect(gq):
    # Subscription → Invoice → Charge → Customer
    result = gq.find_connection("Subscription", "Customer")
    assert "error" not in result or result.get("path_length", 0) >= 1


def test_explain_node(gq):
    result = gq.explain_node("Charge")
    assert "error" not in result
    assert result["entity"] == "Charge"
    assert "outgoing_relationships" in result
    assert "incoming_relationships" in result


def test_concepts_by_type(gq):
    result = gq.concepts_by_type("APIObject")
    assert result["count"] >= 4
    names = {e["name"] for e in result["entities"]}
    assert "Charge" in names


def test_concepts_by_type_invalid(gq):
    result = gq.concepts_by_type("InvalidType")
    assert "error" in result


def test_search_graph(gq):
    result = gq.search_graph("charge")
    assert result["count"] > 0
    names = {r["name"] for r in result["results"]}
    assert any("charge" in n.lower() for n in names)


def test_graph_stats(gq):
    stats = gq.graph_stats()
    assert stats["total_nodes"] >= 6
    assert stats["total_edges"] >= 7
