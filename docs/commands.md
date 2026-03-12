# Commands

## Setup

```bash
cd backend
uv venv
uv sync
cp .env.example .env   # add OPENAI_API_KEY
```

## Ingest documents

Place files in the appropriate directory, then run:

```bash
cd backend
uv run python -m app.ingest
```

| File type       | Directory              |
| --------------- | ---------------------- |
| PDFs            | `backend/data/pdfs/`   |
| Excel / CSV     | `backend/data/excels/` |
| Text / Markdown | `backend/data/texts/`  |

## Run backend

```bash
cd backend
uv run uvicorn app.main:app --reload
# http://localhost:8000
# http://localhost:8000/docs
```

## Run frontend

```bash
cd frontend
pnpm install
pnpm run dev
# http://localhost:3000
```

---

## Key env vars

```bash
# Required
OPENAI_API_KEY=sk-...

# Backend selectors (default values shown)
VECTOR_STORE_BACKEND=chroma      # chroma | postgres
GRAPH_STORE_BACKEND=networkx     # networkx | neo4j

# Cost control
USE_AI_SUMMARIZATION=false       # disable to save cost during testing
PDF_STRATEGY=fast                # fast | hi_res | ocr_only

# Retrieval
TOP_K_CHUNKS=5
RETRIEVAL_K=8
USE_RERANKING=true
USE_MMR=true
```
