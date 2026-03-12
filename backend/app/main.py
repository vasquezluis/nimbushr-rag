from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.routes import files, query
from app.limiter import limiter
from app.infrastructure.factory import get_vector_store, get_graph_store
from app.services.query_service import QueryService

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing vector store...")
    vector_store = get_vector_store()
    vector_store.load()

    print("Initializing graph store...")
    graph_store = get_graph_store()
    graph_store.load()

    # Wire the query service — routes only touch this, not raw stores
    app.state.query_service = QueryService(
        vector_store=vector_store,
        graph_store=graph_store,
    )

    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(title="RAG API", version="2.0.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(query.router, prefix="/api/v1")
    app.include_router(files.router, prefix="/api/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
