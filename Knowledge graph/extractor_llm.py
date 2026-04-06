"""
LLM-based concept extractor using OpenRouter (OpenAI-compatible API).
Produces richer, semantically accurate extraction than the heuristic approach.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .schema import (
    ExtractionResult, NodeModel, EdgeModel,
    NodeType, EdgeType,
)

load_dotenv()

_SYSTEM_PROMPT = """You are a knowledge graph extractor for API documentation.
Extract entities and typed relationships from the given documentation page.

Entity types:
- Document: the doc page itself
- APIObject: domain objects (Charge, Customer, Invoice, etc.)
- Endpoint: REST endpoints (e.g. "POST /v1/charges")
- Event: webhook/system events (e.g. "charge.succeeded")
- Concept: abstract concepts (Authentication, Pagination, Idempotency)

Relationship types (directed: source → target):
- contains: Document → entity
- requires: APIObject → APIObject
- returns: Endpoint → APIObject
- triggers: APIObject → Event
- belongs_to: APIObject → APIObject
- generates: APIObject → APIObject
- references: generic cross-doc link

Respond ONLY with valid JSON in this exact format:
{
  "nodes": [
    {"name": "Charge", "type": "APIObject", "description": "A payment attempt"}
  ],
  "edges": [
    {"source": "Charge", "target": "Customer", "edge_type": "requires"}
  ]
}
"""

_NODE_TYPE_MAP = {t.value: t for t in NodeType}
_EDGE_TYPE_MAP = {t.value: t for t in EdgeType}


def extract(file_path: str | Path, model: str | None = None) -> ExtractionResult:
    """
    Extract concepts using OpenRouter LLM. Falls back to heuristic on error.
    """
    path = Path(file_path)
    content = path.read_text()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        from . import extractor_heuristic
        return extractor_heuristic.extract(file_path)

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        used_model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

        response = client.chat.completions.create(
            model=used_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract from this documentation page ({path.name}):\n\n{content}",
                },
            ],
            temperature=0.0,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        return _parse_response(data, str(path))

    except Exception as e:
        print(f"  [LLM extractor] Error on {path.name}: {e}. Falling back to heuristic.")
        from . import extractor_heuristic
        return extractor_heuristic.extract(file_path)


def _parse_response(data: dict, source_file: str) -> ExtractionResult:
    result = ExtractionResult(source_file=source_file)

    for node_data in data.get("nodes", []):
        ntype_str = node_data.get("type", "Concept")
        ntype = _NODE_TYPE_MAP.get(ntype_str, NodeType.CONCEPT)
        result.nodes.append(NodeModel(
            name=node_data.get("name", "Unknown"),
            type=ntype,
            description=node_data.get("description", ""),
            source_file=source_file,
        ))

    for edge_data in data.get("edges", []):
        etype_str = edge_data.get("edge_type", "references")
        etype = _EDGE_TYPE_MAP.get(etype_str, EdgeType.REFERENCES)
        result.edges.append(EdgeModel(
            source=edge_data.get("source", ""),
            target=edge_data.get("target", ""),
            edge_type=etype,
            source_file=source_file,
        ))

    return result
