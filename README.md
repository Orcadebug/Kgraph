# Nia Docs — Conceptual Graph Engine

> Hybrid document navigation: flat filesystem + semantic knowledge graph.  
> Inspired by [arXiv:2512.05470](https://arxiv.org/abs/2512.05470) — *Everything is Context: Agentic File System Abstraction for Context Engineering*

---

## The Problem

Docs stored as a flat filesystem are great for keyword search. But they can't answer:

> *"How does a Subscription renewal create a Charge and trigger a Webhook?"*

That answer spans `subscriptions/`, `invoices/`, `charges/`, and `webhooks/` — four folders, zero explicit connections.

## The Solution

Layer a **conceptual knowledge graph** on top of the filesystem. Extract entities (API objects, endpoints, events, concepts) and typed relationships from every doc, then let an agent navigate by concept — not by folder.

```
docs/  (flat filesystem)
  ↓  [extraction]
ConceptGraph  (NetworkX DiGraph — nodes + typed edges)
  ↓  [query interface]
AgentToolkit  (file-system-like commands: navigate, inspect, connect, read)
```

## Graph Schema

**Node types:** `Document` · `APIObject` · `Endpoint` · `Event` · `Concept`

**Edge types:** `contains` · `requires` · `returns` · `triggers` · `belongs_to` · `generates` · `references`

Example — what the graph knows about `Charge`:
```
Charge --requires-->    Customer
Charge --requires-->    PaymentMethod
Charge --triggers-->    charge.succeeded  (Event)
Invoice --generates-->  Charge
POST /v1/charges --returns--> Charge
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # add OPENROUTER_API_KEY for LLM mode
```

## Usage

```bash
# Build the graph (heuristic mode — no API key needed)
python run.py build --no-llm

# Build with LLM extraction (richer output, requires OPENROUTER_API_KEY)
python run.py build

# Explore
python run.py stats                        # node/edge counts by type
python run.py query Charge                 # all concepts related to Charge
python run.py connect Subscription Customer # shortest path between concepts
python run.py nodes APIObject              # list all API objects
python run.py search "payment method"      # keyword search across files

# Agent chat (requires OPENROUTER_API_KEY)
python run.py chat
```

## Agent Tools

The LLM agent navigates using filesystem-metaphor commands (per arXiv:2512.05470):

| Tool | Description |
|------|-------------|
| `navigate(concept)` | Get related concepts — like `cd` + `ls` |
| `inspect(concept)` | Full node details — like `cat` |
| `connect(a, b)` | Shortest path between concepts |
| `search_graph(query)` | Semantic graph search |
| `search_files(query)` | Flat keyword search across docs |
| `read(file_path)` | Read a source document |

## Example: Cross-cutting Question

```
You: How does a subscription renewal create a charge?

Agent traversal:
  [navigate] Subscription → {Invoice, Customer, PaymentMethod}
  [connect] Subscription → Invoice → Charge
  [read] subscriptions/create-subscription.md
  [read] invoices/pay-invoice.md

Answer: When a Subscription billing cycle fires, it generates an Invoice.
The Invoice then initiates a Charge against the Customer's PaymentMethod.
If the Charge succeeds, the Invoice status becomes 'paid' and the
charge.succeeded webhook event fires...
```

## Architecture

```
nia/
├── schema.py           # NodeType, EdgeType enums, Pydantic models
├── graph.py            # ConceptGraph — NetworkX DiGraph wrapper
├── extractor_heuristic.py  # Regex/pattern extraction (no API key)
├── extractor_llm.py    # LLM extraction via OpenRouter
├── builder.py          # Orchestrates doc → graph pipeline
├── query.py            # GraphQuery — traversal, pathfinding, search
├── filesystem.py       # Flat file listing and keyword search
└── agent.py            # AgentToolkit — LLM tool-calling loop
```

## Tests

```bash
pytest tests/ -v
```

28 tests covering graph operations, extraction, query interface, and edge cases.
