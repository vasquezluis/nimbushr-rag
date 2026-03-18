from typing import Any, AsyncGenerator, Dict

from app.core.interfaces.vector_store import VectorStoreProtocol
from app.core.interfaces.graph_store import GraphStoreProtocol
from app.core.models import Chunk, HybridRetrievalResult
from app.rag.query.streaming_query_engine import rerank_chunks_async, stream_answer
from app.settings import settings
from langchain_core.documents import Document


class QueryService:
    """
    Orchestrates hybrid retrieval + reranking + LLM streaming.

    Depends on interfaces
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStoreProtocol,
    ) -> None:
        self._vector_store = vector_store
        self._graph_store = graph_store

    async def run_streaming(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Full streaming query pipeline.
        Yields SSE-ready event dicts consumed by the route.
        """

        try:
            yield {"type": "status", "data": "Retrieving relevant documents..."}

            result = self._hybrid_retrieve(query)

            if not result.chunks:
                yield {"type": "error", "data": "No relevant documents found."}
                return

            if settings.use_reranking:
                yield {"type": "status", "data": "Reranking results..."}

                # stream_answer expects LangChain Documents; convert back
                lc_docs = self._to_langchain_docs(result.chunks)
                lc_docs = await rerank_chunks_async(lc_docs, query)
            else:
                lc_docs = self._to_langchain_docs(result.chunks)

            yield {"type": "status", "data": "Generating answer..."}

            if result.graph_traversal:
                yield {"type": "graph", "data": result.graph_traversal}

            async for event in stream_answer(lc_docs, query):
                yield event

        except Exception as e:
            import traceback

            traceback.print_exc()
            yield {"type": "error", "data": f"Error processing query: {str(e)}"}

    def run_sync(self, query: str) -> dict:
        """Non-streaming path used by the /query endpoint and CLI."""
        from app.rag.query.streaming_query_engine import build_context_from_chunks
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        result = self._hybrid_retrieve(query)
        if not result.chunks:
            return {
                "answer": "No relevant documents found.",
                "sources": [],
                "num_chunks": 0,
            }

        lc_docs = self._to_langchain_docs(result.chunks)

        if settings.use_reranking:
            import asyncio

            lc_docs = asyncio.get_event_loop().run_until_complete(
                rerank_chunks_async(lc_docs, query)
            )

        context, sources = build_context_from_chunks(lc_docs)
        llm = ChatOpenAI(model=settings.llm_model, temperature=settings.llm_temperature)
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        response = llm.invoke([HumanMessage(content=prompt)])

        return {
            "answer": response.content,
            "sources": sources,
            "num_chunks": len(lc_docs),
            "chunks_reranked": settings.use_reranking,
        }

    # ------------------------------------------------------------------
    # Hybrid retrieval
    # ------------------------------------------------------------------

    def _hybrid_retrieve(self, query: str) -> HybridRetrievalResult:
        # Vector retrieval via protocol
        vector_chunks = self._vector_store.similarity_search(
            query, k=settings.retrieval_k
        )
        vector_indices = {c.chunk_index for c in vector_chunks}
        vector_source_files = {c.source_file for c in vector_chunks}
        print(f"  Vector: {len(vector_chunks)} chunks → indices {vector_indices}")

        # Graph retrieval via protocol
        graph_indices_list, graph_traversal = self._graph_store.retrieve(
            query, max_chunks=settings.retrieval_k
        )
        graph_indices = set(graph_indices_list)
        print(f"  Graph: {len(graph_indices)} indices")

        # Fetch graph-only docs to inspect their source_file
        graph_only_indices = graph_indices - vector_indices
        graph_only_chunks = self._vector_store.fetch_by_indices(
            list(graph_only_indices)
        )

        # Build index → chunk map
        all_chunks: dict[int, Chunk] = {c.chunk_index: c for c in vector_chunks}
        for c in graph_only_chunks:
            all_chunks[c.chunk_index] = c

        # Scoring
        scores: dict[int, int] = {}
        for idx in vector_indices:
            scores[idx] = scores.get(idx, 0) + 2

        for idx in graph_indices:
            if idx in vector_indices:
                scores[idx] = scores.get(idx, 0) + 2
            else:
                chunk = all_chunks.get(idx)
                if chunk:
                    if chunk.source_file not in vector_source_files:
                        scores[idx] = scores.get(idx, 0) + 1
                    elif self._graph_store.is_specific_match(idx):
                        scores[idx] = scores.get(idx, 0) + 1
                    # else score stays 0 → excluded

        ordered = sorted(
            [idx for idx, s in scores.items() if s > 0],
            key=lambda i: scores[i],
            reverse=True,
        )

        final_chunks = [all_chunks[idx] for idx in ordered if idx in all_chunks][
            : settings.top_k_chunks
        ]

        print(f"  Hybrid: returning {len(final_chunks)} final chunks")
        return HybridRetrievalResult(
            chunks=final_chunks, graph_traversal=graph_traversal
        )

    def _is_specific_graph_match(
        self, chunk_idx: int, specificity_threshold: int = 3
    ) -> bool:
        """
        Delegates to the graph store backend — no concrete type knowledge needed.
        """
        return self._graph_store.is_specific_match(chunk_idx, specificity_threshold)

    @staticmethod
    def _to_langchain_docs(chunks: list[Chunk]) -> list[Document]:
        """Convert our Chunk dataclass back to LangChain Documents for reranker/LLM."""
        return [Document(page_content=c.content, metadata=c.metadata) for c in chunks]
