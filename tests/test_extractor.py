"""Tests for the heuristic extractor."""
import tempfile
from pathlib import Path

import pytest
from kgraph.extractor_heuristic import extract
from kgraph.schema import NodeType, EdgeType


SAMPLE_DOC = """# Create a Charge

Creates a Charge object to bill a Customer.

## Endpoint
POST /v1/charges

## Returns
Returns a **Charge** object.

## Relationships
- A **Charge** requires a **Customer**
- A **Charge** requires a **PaymentMethod**
- On success, triggers the `charge.succeeded` **Webhook** event
- A **PaymentMethod** belongs_to a **Customer**
"""


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "create-charge.md"
    f.write_text(SAMPLE_DOC)
    return f


def test_extracts_document_node(sample_file):
    result = extract(sample_file)
    doc_nodes = [n for n in result.nodes if n.type == NodeType.DOCUMENT]
    assert len(doc_nodes) == 1


def test_extracts_endpoint(sample_file):
    result = extract(sample_file)
    endpoints = [n for n in result.nodes if n.type == NodeType.ENDPOINT]
    assert any("Post" in n.name and "/V1/Charges" in n.name or "POST" in n.name and "/v1/charges" in n.name for n in endpoints)


def test_extracts_event(sample_file):
    result = extract(sample_file)
    events = [n for n in result.nodes if n.type == NodeType.EVENT]
    assert any("charge.succeeded" in n.name.lower() for n in events)


def test_extracts_api_objects(sample_file):
    result = extract(sample_file)
    obj_names = {n.name.lower() for n in result.nodes if n.type == NodeType.API_OBJECT}
    assert "charge" in obj_names
    assert "customer" in obj_names


def test_extracts_requires_relationships(sample_file):
    result = extract(sample_file)
    requires_edges = [e for e in result.edges if e.edge_type == EdgeType.REQUIRES]
    assert len(requires_edges) >= 1


def test_extracts_belongs_to(sample_file):
    result = extract(sample_file)
    belongs_edges = [e for e in result.edges if e.edge_type == EdgeType.BELONGS_TO]
    assert len(belongs_edges) >= 1


def test_source_file_recorded(sample_file):
    result = extract(sample_file)
    assert result.source_file == str(sample_file)
    for node in result.nodes:
        assert node.source_file == str(sample_file)
