# Architecture

## Layers

The backend is split into four layers. Each layer only talks to the layer below it —
nothing skips levels, and no layer knows about the concrete storage technology above it.

```
┌─────────────────────────────────┐
│            API routes           │  Receives HTTP requests, returns responses
├─────────────────────────────────┤
│            Services             │  Orchestrates the pipeline (what to do)
├─────────────────────────────────┤
│          Infrastructure         │  Storage backends (how to store/retrieve)
├─────────────────────────────────┤
│         Core / Interfaces       │  Contracts that backends must satisfy
└─────────────────────────────────┘
         rag/ (internal logic)        Loaders, chunkers, LLM calls — no storage
```

---

## Why this structure

The main goal is to make storage backends **swappable without touching business logic**.

Before this structure, swapping ChromaDB for another database would require edits in
six or more files across the codebase. Now it requires:

1. Implementing one interface (four methods)
2. Changing one env var

The same applies to the graph store. Everything that orchestrates retrieval and
generation is isolated in the service layer and has no knowledge of which database
is running underneath.

---

## Interfaces

Two protocols define the contracts:

**`VectorStoreProtocol`** — `build`, `load`, `similarity_search`, `fetch_by_indices`, `get_all_metadata`

**`GraphStoreProtocol`** — `build`, `load`, `retrieve`

Any class that implements these methods works as a drop-in replacement.
Python's `Protocol` type is used, so implementations don't need to inherit anything.

---

## Services

**`IngestService`** — runs once when you want to index documents. Calls loaders,
chunkers, entity extraction, then hands results to the vector and graph stores.

**`QueryService`** — runs on every user question. Calls both stores, merges results,
reranks, streams the answer. Contains the hybrid scoring logic.

Routes depend on `QueryService` only — they don't know stores exist.

---

## Configuration

All settings live in `settings.py` and can be overridden via `.env`.

Key backend selectors:

```
VECTOR_STORE_BACKEND=chroma      # chroma | postgres
GRAPH_STORE_BACKEND=networkx     # networkx | neo4j
```

See `docs/commands.md` for all available env vars.
