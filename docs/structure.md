# Project Structure

## Directory layout

```
backend/
├── app/
│   ├── core/                        # Abstractions — no third-party imports
│   │   ├── models.py                # Shared data types (Chunk, HybridRetrievalResult)
│   │   └── interfaces/
│   │       ├── vector_store.py      # VectorStoreProtocol
│   │       └── graph_store.py       # GraphStoreProtocol
│   │
│   ├── infrastructure/              # Concrete backend implementations
│   │   ├── factory.py               # Wires up backends from settings
│   │   ├── vector_stores/
│   │   │   ├── chroma.py            # ChromaDB (active)
│   │   │   └── postgres.py          # pgvector (skeleton)
│   │   └── graph_stores/
│   │       ├── networkx_store.py    # NetworkX + JSON (active)
│   │       └── neo4j_store.py       # Neo4j (skeleton)
│   │
│   ├── services/                    # Orchestration — owns the pipelines
│   │   ├── ingest_service.py        # Load → chunk → embed → store
│   │   └── query_service.py         # Retrieve → rerank → stream
│   │
│   ├── rag/                         # Internal processing logic (no storage)
│   │   ├── loaders/                 # pdf_loader, excel_loader, text_loader
│   │   ├── chunkers/                # pdf_processor, excel_processor, text_processor
│   │   ├── ingest/
│   │   │   ├── ai_summarizer.py     # GPT-4o summaries for complex chunks
│   │   │   └── content_analyzer.py  # Extracts tables, images, section titles
│   │   ├── query/
│   │   │   └── streaming_query_engine.py  # Reranker + LLM streaming
│   │   └── graph/
│   │       ├── entity_extractor.py  # LLM entity/relationship extraction
│   │       ├── knowledge_graph.py   # Graph build, merge, save, load
│   │       └── graph_retriever.py   # Fuzzy node match + neighbor traversal
│   │
│   ├── api/
│   │   ├── deps.py                  # get_query_service() FastAPI dependency
│   │   └── v1/routes/
│   │       ├── query.py             # /query and /query/stream endpoints
│   │       └── files.py             # /files endpoints
│   │
│   ├── main.py                      # FastAPI app + lifespan startup
│   ├── ingest.py                    # Ingestion entry point (CLI)
│   ├── limiter.py                   # Rate limiting
│   └── settings.py                  # All config (Pydantic + .env)
│
├── data/
│   ├── pdfs/
│   ├── excels/
│   └── texts/
├── vector_db/                       # Auto-created by active vector store backend
├── graph_db/                        # Auto-created by active graph store backend
└── tests/

frontend/
├── app/
├── components/                      # chat, message, sources, graph-traversal, document viewers
├── hooks/                           # use-streaming-query, use-files
├── api/                             # query.ts, files.ts
└── types/                           # chat.ts, query.ts, files.ts
```

---

## Query flow

```
User question
     ↓
QueryService._hybrid_retrieve()
     ├── VectorStore.similarity_search()   → semantic chunks
     └── GraphStore.retrieve()             → entity-linked chunk indices
              ↓
         Hybrid scorer (vector + graph)
              ↓
         Reranker (cross-encoder)
              ↓
         LLM — streaming answer
              ↓
     Answer + Sources + Graph Traversal
```

## Ingestion flow

```
PDFs / Excel / Text files
     ↓
IngestService.run()
     ├── Loaders      → raw content
     ├── Chunkers     → LangChain Documents
     ├── AI Summarizer (optional, PDF only)
     ├── GraphStore.build()    → entity graph persisted
     └── VectorStore.build()   → embeddings persisted
```

## Hybrid scoring

```
Vector result only              +2
Graph + Vector agree            +4   (highest confidence)
Graph only, new source file     +1   (cross-document discovery)
Graph only, same source file     0   (excluded — likely redundant)
```
