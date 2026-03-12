# GraphRAG — Knowledge Graph

## What it adds

Standard vector search finds chunks that _sound like_ the query.
The knowledge graph finds chunks that are _structurally connected_ to what the query is about.

Both run on every query and their results are merged — each method covers the other's blind spots.

---

## When each method wins

| Query type                                            | Better method |
| ----------------------------------------------------- | ------------- |
| Vague/conceptual ("What is our Core Philosophy?")     | Graph         |
| Cross-document ("Which policies apply to engineers?") | Graph         |
| Specific factual ("What is the Pro plan price?")      | Vector        |
| Structured data (Excel/CSV)                           | Vector        |

---

## How it works

### 1 — Building the graph (ingestion)

Every chunk is passed to the LLM, which extracts:

- **Entities** — named things: policies, departments, roles, benefits, sections
- **Relationships** — how entities connect: `applies_to`, `requires`, `belongs_to`

Each entity becomes a **node**. The same entity appearing in multiple chunks = one node
that remembers all chunk indices where it appeared. This is how the graph bridges back
to actual text.

Every chunk's section heading is also added as a guaranteed `Section` node, so
headings are always findable even when the LLM misses them.

Near-duplicate node names (e.g. "Pro Plan" / "Pro Plans") are merged automatically
after the graph is built.

### 2 — Querying the graph

Given a user question:

1. Extract searchable concepts from the question
2. Fuzzy-match those concepts against graph nodes (threshold: 85% similarity)
3. Traverse one hop — collect direct neighbors in both directions
4. Return all chunk indices found on matched nodes and their neighbors

### 3 — Merging with vector results

Chunks found by both methods score highest. Graph-only chunks from a source file
the vector search already covered are excluded (the vector likely already found
the best chunk from that file). Graph-only chunks from a _new_ source file are
included — that's genuine cross-document discovery.

---

## Graph store

The graph is persisted as a JSON file after every ingestion run. The active backend
is set via `GRAPH_STORE_BACKEND` in `.env` (default: `networkx`).

To swap backends (e.g. Neo4j), implement `GraphStoreProtocol` in
`infrastructure/graph_stores/` and update the env var — nothing else changes.

---

## Known limitations

- Entity name consistency depends on the LLM — the same concept can get different names
  across chunks. Fuzzy matching reduces but doesn't eliminate this.
- The graph is fully rebuilt on every ingestion run (no incremental updates).
- Graph adds most value for conceptual/relational queries. For keyword-heavy factual
  lookups, vector search is more reliable.
