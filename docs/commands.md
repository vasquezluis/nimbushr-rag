# Comands

## Run commands

### ingest setup

```bash
(backend)
uv run app/ingest.py
```

### query setup

```bash
(backend)
uv run python -m app.rag.query.query_pipeline
```

### fastapi

```bash
uvicorn main:app --reload
```

```
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```
