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

### Layered Architecture

```
┌────────────────────────────────────────────────────────────┐
│  HETEROGENEOUS CONTEXT SOURCES                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Docs (flat)  │  │ Knowledge    │  │ External     │    │
│  │ filesystem   │  │ Graph (graph)│  │ APIs         │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────┬──────────────────────────────────────┬────────────┘
         │                                      │
         ↓ [Resolver Adapters - Pluggable]     │
┌────────────────────────────────────────────────────────────┐
│  SYSTEMFS — VIRTUAL FILE SYSTEM (Unified Hierarchy)       │
│  ┌──────────────────────────────────────────────────┐    │
│  │ /docs/                   [DocsResolver]          │    │
│  │ /graph/nodes/            [GraphResolver]         │    │
│  │ /graph/edges/            [GraphResolver]         │    │
│  │ /context/memory/         [MemoryResolver]        │    │
│  │ /context/history/        [History Layer]         │    │
│  │ /context/scratchpad/     [Ephemeral]             │    │
│  │ /modules/                [ModuleResolver]        │    │
│  └──────────────────────────────────────────────────┘    │
└────────┬──────────────────────────────────────────────────┘
         │
         ↓ [Persistent Context Layers]
    ┌─────────────────────────────────────┐
    │ History:    append-only JSONL log   │
    │ Memory:     fact/episodic/proc JSON │
    │ Scratchpad: ephemeral workspace     │
    └─────────────────────────────────────┘
         │
         ↓ [Context Engineering Pipeline]
    ┌──────────────────────────────────────┐
    │ Constructor: query, rank, select     │
    │ Updater:     inject into LLM window  │
    │ Evaluator:   validate → write memory │
    └──────────────────────────────────────┘
         │
         ↓ [Agent Tools]
    ┌──────────────────────────────────────┐
    │ Traditional:  navigate, inspect, ... │
    │ VFS-native:   vfs_read, vfs_list, .. │
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

## Virtual File System (SystemFS)

### Overview

SystemFS projects all heterogeneous context sources—documentation, knowledge graph, memory, external APIs—into a **unified hierarchical directory structure**. This enables agents to navigate, query, and persist knowledge using standard file operations (`read`, `write`, `list`, `search`, `exec`) across disparate backends.

**Key design principle:** Adapters (resolvers) translate complex external data structures into standard VFS nodes without modifying underlying sources.

### Resolver Pattern

Each resolver implements a pluggable adapter that maps a data source into the VFS hierarchy:

```python
class BaseResolver(ABC):
    name: str              # resolver identifier
    readonly: bool         # read-only or writable
    
    read(path: str) → VFSResult        # fetch node content
    write(path, content, metadata)     # persist (if writable)
    list(path: str) → VFSResult        # list children
    search(query, path, max_results)   # keyword search
    exec(path, args) → VFSResult       # special operations
```

**Mounted Resolvers:**

| Mount | Resolver | Backend | Writable | Purpose |
|-------|----------|---------|----------|---------|
| `/docs/` | DocsResolver | kgraph.filesystem.FileSystem | No | Markdown documentation |
| `/graph/` | GraphResolver | ConceptGraph + GraphQuery | No | Knowledge graph nodes/edges/stats |
| `/context/memory/` | MemoryResolver | JSON files (fact/episodic/procedural) | Yes | Persistent memory entries |
| `/modules/` | ModuleResolver | Pluggable handlers | No | External API mounts |

**Resolver dispatch:** Longest-prefix match determines which resolver handles a path. E.g., `/docs/charges/create.md` → DocsResolver, `/graph/nodes/Charge` → GraphResolver.

---

## Persistent Context Layers

Addressing the statelessness problem of LLMs via three-layer storage built into the filesystem:

### History Layer: `/context/history/`

**Append-only JSON-lines log of all interactions and reasoning steps.**

- **Format:** One file per session: `data/history/{date}_{session_id}.jsonl`
- **Entry model:** `HistoryEntry(timestamp, event_type, actor, path, data, session_id)`
- **Events logged:** `read`, `write`, `search`, `context_injection`, `tool_call`, state transitions
- **Query API:** `query_history(session_id=None, event_type=None, limit=100)` — filtered retrieval

**Use case:** Audit trail, session replay, reasoning reconstruction.

### Memory Layer: `/context/memory/`

**Indexed structured knowledge in three categories.**

**Structure:**
```
data/memory/
├── fact/                    # Verified facts (high confidence)
├── episodic/               # Interaction memories (events, outcomes)
└── procedural/             # Procedural knowledge (how-to patterns)
```

**Entry model:** `MemoryEntry(key, content, memory_type, confidence, source_paths, access_count, tags)`

**Write API:** `resolver.write("/context/memory/fact/key", content, metadata={confidence, source_paths, tags})`

**Query API:** `resolver.list("/context/memory/fact/")`, `search(query, "/context/memory/")`

**Use case:** Long-term learning, fact persistence, procedural replay.

### Scratchpad Layer: `/context/scratchpad/`

**Ephemeral workspace for intermediate computations during active reasoning.**

- Writable directory
- Automatically cleared between sessions
- Used by agents for drafting, exploration, temporary results

---

## Context Engineering Pipeline

Solves the token-window constraint via dynamic context selection and injection:

### ContextConstructor

Queries the VFS, scores artifacts by composite metrics, selects within a token budget.

```python
constructor = ContextConstructor(vfs, max_tokens=8000)

# Build context manifest for a query
manifest = constructor.build_context("How do subscriptions work?")
# → ContextManifest(selected_paths=[...], freshness_scores={...}, 
#                   similarity_scores={...}, trust_scores={...})

# Materialize as a string for LLM injection
context_str = constructor.materialize(manifest)
# → markdown text with headers, ~8000 tokens
```

**Scoring metrics:**
- **Freshness:** nodes updated recently score higher (decay over 24h)
- **Similarity:** keyword overlap with query (TF-IDF approximation)
- **Trust:** provenance confidence; docs default 0.8, memory 0.6

**Token estimation:** ~4 characters per token (simple heuristic).

### ContextUpdater

Injects materialized context into LLM message window and logs injections.

```python
updater = ContextUpdater(history_layer)

# Inject context as a system message
messages = updater.inject_context(messages, manifest, context_str)

# Or rebuild context for a new query
messages, manifest = updater.refresh_context(messages, query, constructor)
```

**Behavior:**
- Inserts or replaces a system-role context message
- Logs injection as a history event with source metadata
- Maintains coherence across multiple context refreshes

### ContextEvaluator

Closes the loop by validating model outputs against VFS sources.

```python
evaluator = ContextEvaluator(vfs)

# Extract claims from output, score confidence against sources
memory_entries = evaluator.evaluate(llm_output, manifest)
# → MemoryEntry objects written to /context/memory/
```

**Workflow:**
1. Extract factual claims from LLM output (sentence-level)
2. Score confidence via keyword overlap against source material
3. **High confidence (>0.7):** write as `fact` entry (verified)
4. **Low confidence (<0.7):** write as `episodic` entry with `needs_review` tag
5. Return created `MemoryEntry` objects for auditing

---

## Agent Toolkit: Enhanced Tools

### Traditional Tools (unchanged)

| Tool | Purpose |
|------|---------|
| `navigate(concept)` | Get related concepts from graph |
| `inspect(concept)` | Full node details and relationships |
| `connect(source, target)` | Find shortest path |
| `search_graph(query)` | Semantic graph search |
| `search_files(query)` | Flat keyword search |
| `read(file_path)` | Read doc content |

### New VFS-Native Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `vfs_read(path)` | Read any VFS node | `vfs_read("/graph/nodes/Charge")` → JSON details |
| `vfs_list(path)` | List VFS directory | `vfs_list("/context/memory/fact/")` → fact entries |
| `vfs_search(query, path)` | Search within scope | `vfs_search("payment", "/docs/")` → matching docs |
| `vfs_write(path, content)` | Write to memory/scratchpad | `vfs_write("/context/memory/fact/charge-rule", "...")` |

**System prompt now describes the VFS hierarchy**, enabling agents to navigate proactively.

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

Single entry point for all graph, VFS, and context operations:

#### Graph Operations

```bash
# Build graph from docs
python run.py build [--no-llm]

# Query graph
python run.py query <concept>              # related concepts
python run.py connect <source> <target>    # shortest path
python run.py nodes <type>                 # list by type
python run.py search <query>               # keyword search
python run.py stats                        # graph statistics

# Export
python run.py export                       # graph JSON to stdout
```

#### Virtual File System Operations

```bash
# Explore the unified hierarchy
python run.py vfs mounts                   # list mounted resolvers
python run.py vfs list /                   # browse hierarchy
python run.py vfs list /docs/              # list docs
python run.py vfs list /graph/nodes/       # list graph nodes
python run.py vfs list /context/memory/    # list memory entries

# Read content
python run.py vfs read /docs/authentication.md
python run.py vfs read /graph/nodes/Charge
python run.py vfs read /context/memory/fact/my-key

# Search
python run.py vfs search "payment"         # global search
python run.py vfs search "auth" /docs/     # scoped to docs
```

#### Context Layer Operations

```bash
# History
python run.py context history              # recent interactions
python run.py context history --limit 50   # custom limit

# Memory
python run.py context memory               # all entries
python run.py context memory fact          # verified facts only
python run.py context memory episodic      # memories only
python run.py context memory procedural    # procedures only
```

#### Interactive Agent

```bash
# LLM agent with full VFS/context access
python run.py chat                         # requires OPENROUTER_API_KEY
```

---

## Testing Strategy

**86 unit tests** covering:

### Graph Engine (28 original tests, `tests/test_graph.py`, `test_extractor.py`, `test_query.py`)
- Node add/get/normalization
- Neighbor queries (in/out/both directions)
- Path finding and subgraph extraction
- Edge strengthening
- Serialization roundtrip
- Heuristic/LLM extraction
- Query interface (related concepts, type listing, fuzzy search)

### SystemFS & Resolvers (34 new tests)

**Core VFS** (`tests/test_vfs.py`):
- Mount/unmount, routing, root listing
- Longest-prefix resolver dispatch
- Read-only enforcement
- Writable resolver support
- Cross-resolver search merging

**Sandbox** (`tests/test_sandbox.py`):
- Path normalization, traversal prevention
- Boundary validation, relative path computation

**DocsResolver** (`tests/test_resolver_docs.py`):
- Read/list/search on markdown files
- Missing file errors, write rejection

**GraphResolver** (`tests/test_resolver_graph.py`):
- Node/edge/stats reads
- Virtual path layout
- exec() operations (find_path, subgraph, related_concepts)

**MemoryResolver** (`tests/test_resolver_memory.py`):
- Write/read roundtrip for all memory types
- Persistence across instances
- Access count tracking, search, type filtering

### Context Engineering (12 new tests)

**History Layer** (`tests/test_context_history.py`):
- Session startup, JSON-lines format
- Log entry, query by event type/session ID
- Session isolation

**Context Constructor** (`tests/test_context_constructor.py`):
- Query ranking by freshness/similarity/trust
- Token budget enforcement
- Hint inclusion, materialization

### Run tests:
```bash
pytest tests/ -v                # all 86 tests
pytest tests/test_vfs.py -v     # VFS only
pytest tests/test_*.py -v       # specific suite
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

## SystemFS: Design Philosophy

The Virtual File System answers the core challenge from arXiv:2512.05470: **how to project all heterogeneous context into a unified, programmable abstraction that doesn't require agents to learn multiple APIs.**

**Key innovations:**

1. **Unified hierarchy:** All context (docs, graph, memory, APIs) at `/` with standard file semantics
2. **Pluggable adapters:** Resolvers add new data sources without touching existing code
3. **Persistent layers:** History for auditability, memory for learning, scratchpad for workspace
4. **Context engineering:** Automatic selection & injection with quality metrics (freshness, similarity, trust)
5. **Closed feedback loop:** Evaluation validates outputs and routes high-confidence findings back to memory

This is the first implementation of a **context-centric agent architecture** where knowledge flows bidirectionally: agents read context, reason, write findings back to persistent memory.

---

## Future Directions

### Short Term

- **ModuleResolver handlers:** Integrate external APIs (GitHub, Jira, web search) as mounted directories
- **Confidence propagation:** Surface extraction confidence through the VFS
- **Context refresh heuristics:** Automatic re-querying when scratchpad changes
- **Memory decay:** Temporal weighting in constructor (recent facts score higher)

### Medium Term

- **Vector embeddings:** Semantic similarity for fuzzy entity linking and memory retrieval
- **Multi-hop reasoning:** Agent plans multi-step journeys through graph and memory
- **Human-in-the-loop:** Review loop for `needs_review` tagged outputs before memory commit
- **Temporal versioning:** Track how concepts evolve across doc versions

### Long Term

- **Distributed memory:** Shared memory pool across multiple agents
- **Collaborative refinement:** Agents update each other's memory; consensus scoring
- **Knowledge compilation:** Compress repeated reasoning patterns into new nodes/edges
- **Adaptive extraction:** Extraction weights learned from evaluator feedback
