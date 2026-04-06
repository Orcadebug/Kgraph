# Knowledge Graph — Semantic Navigation for Documentation

> **A conceptual knowledge graph engine for document systems.**  
> Bridges flat filesystem search with semantic relationship discovery.  
> Inspired by [arXiv:2512.05470](https://arxiv.org/abs/2512.05470) — *Everything is Context: Agentic File System Abstraction for Context Engineering*

---

## Problem Statement

Traditional documentation systems treat documents as isolated files in a flat directory. While keyword search works for single-topic queries, it fails for cross-cutting questions:

**Example:** *"How does a subscription renewal create a charge and trigger a webhook?"*

- ❌ Flat search: finds 3 isolated files, no connections
- ✓ Graph: discovers the causal chain → Subscription → Invoice → Charge → Event

This engine layers a **semantic knowledge graph** on top of the flat filesystem, enabling agents to navigate by **concepts** rather than folders.

---

## Architecture Overview

```
┌─────────────────────┐
│  Markdown Docs      │  (flat filesystem)
│  (15 files)         │
└──────────┬──────────┘
           │
           ↓ [Extraction]
┌──────────────────────────────────────┐
│  ConceptGraph (NetworkX DiGraph)     │
│  ├─ 59 nodes (Objects, Endpoints)    │
│  ├─ 167 edges (typed relationships)  │
│  └─ Bidirectional traversal          │
└──────────┬──────────────────────────┘
           │
           ↓ [Query Interface]
┌──────────────────────────────────────┐
│  GraphQuery                          │
│  ├─ related_concepts(entity)         │
│  ├─ find_connection(a, b)            │
│  ├─ concepts_by_type(type)           │
│  └─ search_graph(query)              │
└──────────┬──────────────────────────┘
           │
           ↓ [Agent Tools]
┌──────────────────────────────────────┐
│  AgentToolkit (LLM tool-calling)     │
│  ├─ navigate(concept)                │
│  ├─ inspect(concept)                 │
│  ├─ connect(a, b)                    │
│  ├─ search_files(query)              │
│  └─ read(file_path)                  │
└──────────────────────────────────────┘
```

---

## Core Concepts

### Schema: Node Types

Five semantic node types extracted from documentation:

| Type | Description | Example |
|------|-------------|---------|
| **Document** | Source markdown file | `Create A Charge`, `Webhooks` |
| **APIObject** | Domain entity extracted from docs | `Charge`, `Customer`, `Invoice` |
| **Endpoint** | REST endpoint | `POST /v1/charges`, `GET /v1/customers/:id` |
| **Event** | Webhook/system event | `charge.succeeded`, `invoice.paid` |
| **Concept** | Abstract concept spanning multiple docs | `Authentication`, `Pagination`, `Idempotency` |

### Schema: Edge Types (Relationships)

Seven directed relationship types model how concepts connect:

| Edge Type | Semantics | Example |
|-----------|-----------|---------|
| `contains` | Document → entity (hierarchical) | Document "Create A Charge" contains Endpoint `POST /v1/charges` |
| `requires` | APIObject → APIObject (dependency) | `Charge` requires `Customer` |
| `returns` | Endpoint → APIObject (output) | `POST /v1/charges` returns `Charge` |
| `triggers` | APIObject → Event (causality) | `Charge` triggers `charge.succeeded` event |
| `belongs_to` | APIObject → APIObject (ownership) | `PaymentMethod` belongs_to `Customer` |
| `generates` | APIObject → APIObject (production) | `Subscription` generates `Invoice` |
| `references` | Cross-document generic link | Generic mention/relationship |

### Node Properties

Each node carries metadata:
- `type` — one of the five NodeType enums
- `source_file` — which markdown file it came from
- `description` — extracted or provided text
- `properties` — arbitrary key-value attributes

### Edge Properties

Each edge carries:
- `edge_type` — one of the seven relationship types
- `weight` — float (1.0 default, increases with co-occurrence)
- `source_file` — which document contributed this relationship

---

## Data Flow: From Docs to Graph

### 1. Document Ingestion

Raw markdown files in `docs/` contain:
- Headers (entity names)
- REST endpoint patterns
- Backtick-quoted event names
- Bold-referenced entities
- Explicit "Relationships" sections

**Sample section:**
```markdown
## Relationships
- A **Charge** requires a **Customer**
- A **Charge** requires a **PaymentMethod**
- On success, triggers `charge.succeeded` event
```

### 2. Concept Extraction (Dual Strategy)

**Heuristic Extractor** (`kgraph/extractor_heuristic.py`):
- Regex patterns for REST endpoints: `(GET|POST|PUT|DELETE) /v1/\w+`
- Bold entity detection: `\*\*(\w+)\*\*`
- Backtick events: `` `([\w.]+)` ``
- Relationship line parsing: `**X** requires **Y**`
- **Pros:** Zero dependencies, instant, works without API key
- **Cons:** Misses implicit relationships, lower semantic accuracy

**LLM Extractor** (`kgraph/extractor_llm.py`):
- Sends document + structured prompt to OpenRouter (Claude, GPT-4, etc.)
- Returns JSON: `{nodes: [{name, type, description}], edges: [{source, target, edge_type}]}`
- Falls back to heuristic on API error
- **Pros:** Understands semantics, captures implicit relationships
- **Cons:** API costs, latency, requires credentials

Both extractors return `ExtractionResult` (Pydantic model) with consistent interface.

### 3. Graph Assembly

`kgraph/builder.py` orchestrates:
```python
1. Walk docs/ directory
2. For each .md file:
   a. Extract using heuristic OR LLM
   b. Collect nodes and edges
3. Merge into single NetworkX DiGraph:
   a. Normalize node names (title case)
   b. Deduplicate nodes (merge by name)
   c. Strengthen edges (co-occurrence → weight boost)
4. Serialize to data/graph.json using node_link_data()
```

**Graph stats from sample docs:**
```
Total nodes: 59
  Document: 17
  Endpoint: 13
  Event: 20
  APIObject: 8
  Concept: 1

Total edges: 167
  contains: 51
  references: 99
  returns: 13
  requires: 1
  generates: 1
  belongs_to: 2
```

---

## Graph Engine Design

### ConceptGraph (`kgraph/graph.py`)

Thin NetworkX wrapper with semantic operations:

**Mutation:**
- `add_node(NodeModel)` — insert/merge nodes by name
- `add_edge(EdgeModel)` — insert/strengthen edges

**Query:**
- `get_node(name)` → full node data
- `get_neighbors(name, edge_type=None, direction='both')` → list of {node, edge_type, weight}
- `find_path(source, target)` → shortest undirected path with edge types
- `subgraph(center, depth)` → BFS neighborhood within depth hops
- `nodes_by_type(NodeType)` → all nodes of a given type
- `search(query)` → fuzzy name match across all nodes

**Serialization:**
- `to_json()` → NetworkX node_link_data format (JSON-serializable dict)
- `save(path)` → write to file
- `load(path)` → class method, deserialize from file

**Normalization:**
- Node names normalized to title case: `"charge"` → `"Charge"`
- Bidirectional edges: `find_path()` uses undirected graph for discovery
- Weighted edges: repeated relationships boost weight (up to 5.0)

---

## Query Interface

### GraphQuery (`kgraph/query.py`)

High-level semantic query layer on top of ConceptGraph:

```python
# Get all related entities
related = gq.related_concepts("Charge")
# → {entity, type, description, relationships: [{node, edge_type, direction, weight}]}

# Find how two concepts connect
path = gq.find_connection("Subscription", "Customer")
# → {source, target, path_length, path: [{node, edge_to_next}]}

# Full node context
details = gq.explain_node("Invoice")
# → {entity, type, description, outgoing_relationships, incoming_relationships}

# List all of a type
objects = gq.concepts_by_type("APIObject")
# → {type, count, entities: [{name, description, source_file}]}

# Fuzzy search
results = gq.search_graph("payment")
# → {query, count, results: [{name, type, description, score}]}

# Local neighborhood for context windows
sub = gq.subgraph_context("Charge", depth=2)
# → {center, depth, stats, nodes}
```

---

## Agent Toolkit Design

### AgentToolkit (`kgraph/agent.py`)

Wraps graph + filesystem as LLM tools. Implements the "filesystem-metaphor" pattern from arXiv:2512.05470:

**Tools (file-system-like commands):**

| Tool | Semantics | Example |
|------|-----------|---------|
| `navigate(concept)` | `cd` + `ls` — explore neighbors | `navigate("Charge")` → related entities |
| `inspect(concept)` | `cat` — full details | `inspect("Customer")` → all relationships |
| `connect(a, b)` | `find` — discover paths | `connect("Subscription", "Event")` → path |
| `search_graph(query)` | Graph search | `search_graph("payment")` → fuzzy matches |
| `search_files(query)` | Flat keyword search | `search_files("idempotency")` → file list |
| `read(file_path)` | `cat file` — doc content | `read("charges/create-charge.md")` → markdown |

**Tool Calling Loop:**

```
User question
    ↓
LLM sees tools + question
    ↓
LLM calls tools in sequence (e.g., navigate → connect → read)
    ↓
Collect results, record traversal log
    ↓
Send results back to LLM
    ↓
LLM reasons and composes answer
    ↓
Return: {answer, traversal_log, sources}
```

**Traversal Log Example:**
```json
{
  "answer": "When a Subscription cycles, it generates an Invoice...",
  "traversal_log": [
    {"tool": "navigate", "args": {"concept": "Subscription"}, "result_summary": "3 relationships found"},
    {"tool": "connect", "args": {"source": "Subscription", "target": "Event"}, "result_summary": "Subscription → Invoice → Charge → Event"},
    {"tool": "read", "args": {"file_path": "subscriptions/create-subscription.md"}, "result_summary": "read file (1200 chars)"}
  ],
  "sources": ["subscriptions/create-subscription.md", "invoices/pay-invoice.md"]
}
```

---

## Implementation Details

### Extraction Pipeline

**kgraph/schema.py:**
- `NodeType` enum: Document, APIObject, Endpoint, Event, Concept
- `EdgeType` enum: contains, requires, returns, triggers, belongs_to, generates, references
- `NodeModel`, `EdgeModel`, `ExtractionResult` Pydantic classes for type safety

**kgraph/extractor_heuristic.py:**
- Regex patterns for common structures
- Parses markdown headings, endpoints, bold refs, backtick events
- Returns ExtractionResult with nodes and edges

**kgraph/extractor_llm.py:**
- OpenRouter-compatible OpenAI SDK client
- Structured prompt requesting JSON output
- Fallback to heuristic on error
- Configurable model (default: anthropic/claude-sonnet-4-5)

### Graph Normalization

- Node names: `.title()` case (e.g., "charge" → "Charge")
- Document nodes: extracted from markdown filename or H1 heading
- Deduplication: nodes merged by normalized name
- Edge strengthening: repeated relationships increase weight

### Serialization Format

Graph stored as NetworkX `node_link_data()` JSON:
```json
{
  "directed": true,
  "multigraph": false,
  "graph": {},
  "nodes": [
    {"id": "Charge", "type": "APIObject", "description": "...", "source_file": "..."},
    ...
  ],
  "links": [
    {"source": "Charge", "target": "Customer", "edge_type": "requires", "weight": 1.0},
    ...
  ]
}
```

---

## Filesystem Layer

### FileSystem (`kgraph/filesystem.py`)

Handles flat document operations:

```python
fs = FileSystem(Path("docs"))

# Recursive file listing
files = fs.list_files()  # → [{path, name, title}]

# Keyword search with snippets
results = fs.search("payment method")
# → [{path, title, match_count, snippets: [context_snippets]}]

# Read file content
content = fs.read_file("charges/create-charge.md")  # → markdown string
```

Used by:
- Agent `search_files` tool (for flat search fallback)
- Agent `read` tool (to fetch source documents)

---

## CLI Interface

### run.py

Single entry point for all operations:

```bash
# Build graph from docs
python run.py build [--no-llm]

# Query graph
python run.py query <concept>              # related concepts
python run.py connect <source> <target>    # shortest path
python run.py nodes <type>                 # list by type
python run.py search <query>               # keyword search
python run.py stats                        # graph statistics

# Interactive agent
python run.py chat                         # LLM agent REPL (requires OPENROUTER_API_KEY)

# Export
python run.py export                       # graph JSON to stdout
```

---

## Testing Strategy

**28 unit tests** covering:

**Graph engine** (`tests/test_graph.py`):
- Node add/get/normalization
- Neighbor queries (in/out/both directions)
- Path finding and subgraph extraction
- Edge strengthening
- Serialization roundtrip

**Extraction** (`tests/test_extractor.py`):
- Heuristic endpoint/event/entity parsing
- Relationship line extraction
- Source file recording

**Query interface** (`tests/test_query.py`):
- Related concepts discovery
- Path finding
- Type-based listing
- Fuzzy search
- Graph statistics

**Run tests:**
```bash
pytest tests/ -v
```

---

## Sample Data

Included: 18 markdown files modeling a Stripe-like payment API:
- **Core objects:** Charge, Customer, PaymentMethod, Invoice, Subscription
- **Operations:** create, retrieve, update, list, attach, detach, pay, cancel
- **Events & lifecycle:** charge.succeeded, invoice.paid, subscription.deleted, etc.
- **Cross-cutting:** Authentication, Errors, Pagination, Webhooks

Files are structured with explicit "Relationships" sections to maximize extraction accuracy.

---

## Dependencies

```
networkx>=3.0           # Graph data structure
openai>=1.0.0           # OpenRouter API client (OpenAI-compatible)
pydantic>=2.0.0         # Type validation
python-dotenv>=1.0.0    # Environment config
pytest>=7.0.0           # Testing
```

---

## Design Rationale

**NetworkX over Neo4j:**
- Zero infrastructure overhead
- In-memory for fast queries
- Serializes to standard JSON
- Sufficient for this scale (59 nodes, 167 edges)

**OpenRouter for LLM:**
- OpenAI-compatible API (swap models easily)
- No vendor lock-in
- User's choice of model/provider

**Heuristic fallback:**
- Works without credentials
- Fast for simple docs
- Graceful degradation

**File-system metaphor (tools):**
- Intuitive for LLMs: `navigate`, `inspect`, `read`
- Aligns with arXiv:2512.05470 design
- Reduces cognitive overhead for reasoning

**Bidirectional traversal:**
- Answers "what points to X?" (incoming edges)
- Answers "what does X point to?" (outgoing edges)
- Undirected pathfinding for discovery

---

## Future Directions

- **Temporal versioning:** Track how concepts evolve across doc versions
- **Confidence scoring:** Weight nodes/edges by extraction confidence
- **Multi-hop reasoning:** Agent plans multi-step journeys through graph
- **Vector embeddings:** Semantic similarity for fuzzy entity linking
- **Interactive refinement:** User feedback improves extraction weights
