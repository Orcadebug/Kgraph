"""
Schema definitions for nodes, edges, and extraction results.
"""
from enum import Enum
from typing import Any
from pydantic import BaseModel


class NodeType(str, Enum):
    DOCUMENT = "Document"
    API_OBJECT = "APIObject"
    ENDPOINT = "Endpoint"
    EVENT = "Event"
    CONCEPT = "Concept"


class EdgeType(str, Enum):
    CONTAINS = "contains"        # Document → entity
    REQUIRES = "requires"        # Charge requires Customer
    RETURNS = "returns"          # Endpoint returns APIObject
    TRIGGERS = "triggers"        # Charge triggers charge.succeeded
    BELONGS_TO = "belongs_to"    # PaymentMethod belongs_to Customer
    REFERENCES = "references"    # generic cross-doc link
    GENERATES = "generates"      # Subscription generates Invoice


class NodeModel(BaseModel):
    name: str
    type: NodeType
    description: str = ""
    source_file: str = ""
    properties: dict[str, Any] = {}


class EdgeModel(BaseModel):
    source: str
    target: str
    edge_type: EdgeType
    weight: float = 1.0
    source_file: str = ""


class ExtractionResult(BaseModel):
    source_file: str
    nodes: list[NodeModel] = []
    edges: list[EdgeModel] = []
