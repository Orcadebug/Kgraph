"""
Heuristic concept extractor — regex/pattern-based, no API key required.
Parses markdown docs to extract entities and relationships.
"""
import re
from pathlib import Path

from .schema import (
    ExtractionResult, NodeModel, EdgeModel,
    NodeType, EdgeType,
)

# Patterns for API objects (capitalized bold references in text)
_BOLD_ENTITY = re.compile(r"\*\*([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)\*\*")
# REST endpoints
_ENDPOINT = re.compile(r"(GET|POST|PUT|PATCH|DELETE)\s+(/v\d+/[\w/:_.-]+)")
# Webhook event names
_EVENT = re.compile(r"`([a-z_]+\.[a-z_.]+)`")
# Relationship section lines: "- A **X** requires a **Y**"
_REL_REQUIRES = re.compile(r"\*\*(\w+)\*\*.*?requires.*?\*\*(\w+)\*\*", re.IGNORECASE)
_REL_TRIGGERS = re.compile(r"\*\*(\w+)\*\*.*?triggers.*?\*\*(\w+)\*\*", re.IGNORECASE)
_REL_GENERATES = re.compile(r"\*\*(\w+)\*\*.*?generates.*?\*\*(\w+)\*\*", re.IGNORECASE)
_REL_BELONGS = re.compile(r"\*\*(\w+)\*\*.*?belongs_to.*?\*\*(\w+)\*\*", re.IGNORECASE)
_REL_RETURNS = re.compile(r"returns.*?\*\*(\w+)\*\*", re.IGNORECASE)

# Known API object names
_KNOWN_OBJECTS = {
    "Charge", "Customer", "Paymentmethod", "Payment Method", "Subscription",
    "Invoice", "Webhook", "Refund", "Event", "Authentication", "Pagination",
    "Idempotency",
}


def extract(file_path: str | Path) -> ExtractionResult:
    path = Path(file_path)
    content = path.read_text()
    result = ExtractionResult(source_file=str(path))

    # ── Document node ────────────────────────────────────────────────────────
    doc_name = _title_from_content(content) or path.stem
    result.nodes.append(NodeModel(
        name=doc_name,
        type=NodeType.DOCUMENT,
        description=f"Documentation file: {path.name}",
        source_file=str(path),
    ))

    seen_nodes: set[str] = {doc_name.lower()}
    seen_edges: set[tuple] = set()

    def add_node(name: str, ntype: NodeType, desc: str = "") -> str:
        normalized = name.strip().title()
        if normalized.lower() not in seen_nodes:
            result.nodes.append(NodeModel(
                name=normalized, type=ntype, description=desc, source_file=str(path)
            ))
            seen_nodes.add(normalized.lower())
        return normalized

    def add_edge(src: str, tgt: str, etype: EdgeType) -> None:
        key = (src.lower(), tgt.lower(), etype.value)
        if key not in seen_edges:
            result.edges.append(EdgeModel(
                source=src, target=tgt, edge_type=etype, source_file=str(path)
            ))
            seen_edges.add(key)

    # ── Endpoints ────────────────────────────────────────────────────────────
    for m in _ENDPOINT.finditer(content):
        ep_name = f"{m.group(1)} {m.group(2)}"
        ep_node = add_node(ep_name, NodeType.ENDPOINT, f"API endpoint: {ep_name}")
        add_edge(doc_name, ep_node, EdgeType.CONTAINS)

    # ── Events ───────────────────────────────────────────────────────────────
    for m in _EVENT.finditer(content):
        name = m.group(1)
        if "." in name and not name.startswith("/"):
            ev_node = add_node(name, NodeType.EVENT, f"Webhook event: {name}")
            add_edge(doc_name, ev_node, EdgeType.CONTAINS)

    # ── Bold entity mentions ─────────────────────────────────────────────────
    for m in _BOLD_ENTITY.finditer(content):
        entity = m.group(1).strip()
        if len(entity) < 3:
            continue
        ntype = NodeType.API_OBJECT if entity.title() in _KNOWN_OBJECTS else NodeType.CONCEPT
        entity_node = add_node(entity, ntype)
        add_edge(doc_name, entity_node, EdgeType.REFERENCES)

    # ── Relationship lines ────────────────────────────────────────────────────
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("- ") and not line.startswith("* "):
            continue

        for m in _REL_REQUIRES.finditer(line):
            src = add_node(m.group(1), NodeType.API_OBJECT)
            tgt = add_node(m.group(2), NodeType.API_OBJECT)
            add_edge(src, tgt, EdgeType.REQUIRES)

        for m in _REL_TRIGGERS.finditer(line):
            src = add_node(m.group(1), NodeType.API_OBJECT)
            tgt = add_node(m.group(2), NodeType.API_OBJECT)
            add_edge(src, tgt, EdgeType.TRIGGERS)

        for m in _REL_GENERATES.finditer(line):
            src = add_node(m.group(1), NodeType.API_OBJECT)
            tgt = add_node(m.group(2), NodeType.API_OBJECT)
            add_edge(src, tgt, EdgeType.GENERATES)

        for m in _REL_BELONGS.finditer(line):
            src = add_node(m.group(1), NodeType.API_OBJECT)
            tgt = add_node(m.group(2), NodeType.API_OBJECT)
            add_edge(src, tgt, EdgeType.BELONGS_TO)

    # ── "Returns" pattern ────────────────────────────────────────────────────
    for m in _REL_RETURNS.finditer(content):
        # find the nearest endpoint already extracted
        returned = add_node(m.group(1), NodeType.API_OBJECT)
        # link all endpoints in this file to the returned object
        for ep_node in [n.name for n in result.nodes if n.type == NodeType.ENDPOINT]:
            add_edge(ep_node, returned, EdgeType.RETURNS)

    return result


def _title_from_content(content: str) -> str | None:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None
