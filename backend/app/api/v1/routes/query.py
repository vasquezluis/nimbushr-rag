import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_query_service
from app.limiter import limiter
from app.services.query_service import QueryService

router = APIRouter(tags=["RAG"])


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sources: list
    num_chunks: int
    chunks_reranked: bool | None = None


@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_rag(
    request: Request,
    query_request: QueryRequest,
    service: QueryService = Depends(get_query_service),
):
    return service.run_sync(query_request.query)


@router.post("/query/stream")
@limiter.limit("5/minute")
async def query_rag_stream(
    request: Request,
    query_request: QueryRequest,
    service: QueryService = Depends(get_query_service),
):
    async def event_generator():
        try:
            async for event in service.run_streaming(query_request.query):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
