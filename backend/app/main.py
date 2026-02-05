from fastapi import FastAPI

app = FastAPI()


@app.post("/ingest/pubmed")
def ingest():
    return "ingest pubmed"


@app.post("/query")
def query():
    return "query"


@app.get("/papers/{pmid}")
def query(pmid: int):
    return f"query {pmid}"


@app.get("/health")
def health():
    return "Server running"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
