# Vector Store

## What it does

The vector store turns document chunks into numerical representations (embeddings)
and lets us search them by meaning, not just keywords.

When a user asks a question, the question is also embedded and the store returns
whichever chunks are closest in meaning — even if they use different words.

---

## How it fits in

```
Ingestion:  VectorStore.build(documents)   → embeds and persists all chunks
Query:      VectorStore.similarity_search() → returns top-k similar chunks
            VectorStore.fetch_by_indices()  → fetches chunks by index (for graph bridge)
            VectorStore.get_all_metadata()  → used by the /files endpoint
```

The rest of the application never imports the storage library directly.
Routes, services, and the graph layer all talk to `VectorStoreProtocol` — an interface
that any backend can satisfy.

---

## Switching backends

The active backend is controlled by one env var:

```
# .env
VECTOR_STORE_BACKEND=chroma    # default
VECTOR_STORE_BACKEND=postgres  # future
```

To add a new backend:

1. Create `infrastructure/vector_stores/new_backend.py`
2. Implement the four methods: `build`, `load`, `similarity_search`, `fetch_by_indices`, `get_all_metadata`
3. Add an `elif` branch in `infrastructure/factory.py`
4. Set the env var

Nothing in services, routes, or the graph layer needs to change.

---

## Retrieval modes

Two retrieval modes are supported, toggled via `USE_MMR` in settings:

**MMR (Maximal Marginal Relevance)** — default. Balances relevance with diversity,
so you don't get five chunks that all say the same thing.

**Similarity threshold** — returns only chunks above a confidence floor.
Useful when you'd rather get fewer results than risk irrelevant ones.

---

## Embeddings

Documents and queries are embedded with the same model so distances are comparable.
The embedding model is set via `EMBEDDING_MODEL` in settings (default: `text-embedding-3-small`).
