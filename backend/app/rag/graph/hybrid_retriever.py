"""
Hybrid Retriever Module
Combines vector search results with graph retrieval results.

Scoring logic:
  - Chunk found by BOTH vector + graph  → highest priority (score 2)
  - Chunk found by vector only          → medium priority (score 1)
  - Chunk found by graph only           → medium priority (score 1)

This way chunks that are semantically similar AND structurally
connected to the query entities always rise to the top.
"""

from typing import Optional, TypedDict

import networkx as nx
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.rag.graph.graph_retriever import (
    GraphTraversalResult,
    retrieve_chunks_from_graph,
)
from app.settings import settings


class HybridRetrievalResult(TypedDict):
    chunks: list[Document]
    graph_traversal: list[dict]  # matched_nodes for frontend


def _fetch_chunks_by_indices(db: Chroma, chunk_indices: list[int]) -> list[Document]:
    """
    Fetch specific chunks from ChromaDB by their chunk_index metadata field.
    This is how we bridge the graph (which stores indices) back to actual text.
    """

    if not chunk_indices:
        return []

    results = db._collection.get(
        where={"chunk_index": {"$in": [int(i) for i in chunk_indices]}},  # int
        include=["documents", "metadatas"],
    )

    if not results or not results.get("documents"):
        return []

    docs = []
    for doc_text, metadata in zip(results["documents"], results["metadatas"]):
        docs.append(Document(page_content=doc_text, metadata=metadata))

    return docs


def hybrid_retrieve(
    query: str,
    db: Chroma,
    graph: Optional[nx.DiGraph],
) -> list[Document]:

    # --- Vector retrieval ---
    if settings.use_mmr:
        retriever = db.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.retrieval_k,
                "fetch_k": settings.retrieval_k * 3,
                "lambda_mult": settings.mmr_lambda,
            },
        )
    else:
        retriever = db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": settings.retrieval_k,
                "score_threshold": 0.5,
            },
        )

    vector_chunks = retriever.invoke(query)
    vector_indices = {doc.metadata.get("chunk_index") for doc in vector_chunks}
    print(f"  Vector: returned {len(vector_chunks)} chunks → indices {vector_indices}")

    # --- Graph retrieval ---
    graph_result: GraphTraversalResult = retrieve_chunks_from_graph(
        query, graph, max_chunks=settings.retrieval_k
    )
    graph_indices = set(graph_result["chunk_indices"])
    graph_traversal = graph_result["matched_nodes"]

    # --- Only use graph results that OVERLAP with vector results ---
    # OR are from a completely different source_file than vector results
    # This prevents graph from displacing strong vector matches
    vector_source_files = {doc.metadata.get("source_file") for doc in vector_chunks}

    # Build a map of chunk_index → doc for quick lookup
    all_chunks_by_index: dict[int, Document] = {
        doc.metadata.get("chunk_index"): doc for doc in vector_chunks
    }

    # Fetch graph-only chunks so we can inspect their metadata
    graph_only_indices = graph_indices - vector_indices
    graph_only_docs = _fetch_chunks_by_indices(db, list(graph_only_indices))

    for doc in graph_only_docs:
        idx = doc.metadata.get("chunk_index")
        all_chunks_by_index[idx] = doc

    # --- Scoring ---
    scores: dict[int, int] = {}

    for idx in vector_indices:
        scores[idx] = (
            scores.get(idx, 0) + 2
        )  # vector gets +2 (it's the reliable baseline)

    for idx in graph_indices:
        if idx in vector_indices:
            scores[idx] = scores.get(idx, 0) + 2
        else:
            doc = all_chunks_by_index.get(idx)
            if doc:
                graph_source = doc.metadata.get("source_file")
                if graph_source not in vector_source_files:
                    # New source file the vector missed → include
                    scores[idx] = scores.get(idx, 0) + 1
                else:
                    # Same source file — check if this came from a specific node
                    # (small node = precise match, should not be suppressed)
                    is_specific_match = _is_specific_graph_match(graph, idx)
                    if is_specific_match:
                        scores[idx] = scores.get(idx, 0) + 1
                    # else: score stays 0 → excluded (likely redundant)

    # Sort by score, remove zero-score graph-only same-source chunks
    ordered_indices = sorted(
        [idx for idx, s in scores.items() if s > 0],
        key=lambda idx: scores[idx],
        reverse=True,
    )

    both = {idx for idx in graph_indices if idx in vector_indices}
    graph_only = graph_indices - vector_indices
    vector_only = vector_indices - graph_indices

    print(
        f"  Hybrid: {len(both)} both, {len(vector_only)} vector-only, {len(graph_only)} graph-only"
    )
    print(f"  Scores: { {idx: scores[idx] for idx in ordered_indices} }")

    final_chunks = []
    for idx in ordered_indices:
        if idx in all_chunks_by_index:
            final_chunks.append(all_chunks_by_index[idx])

    final_chunks = final_chunks[: settings.top_k_chunks]
    print(f"  Hybrid: returning {len(final_chunks)} final chunks")

    return {
        "chunks": final_chunks,
        "graph_traversal": graph_traversal,
    }

def _is_specific_graph_match(graph: Optional[nx.Graph], chunk_idx: int, specificity_threshold: int = 3) -> bool:
    """
    Returns True if this chunk_idx belongs to a small/specific graph node.
    Small nodes (few chunks) = precise matches that should not be suppressed
    by the same-source-file exclusion rule.
    """
    if graph is None:
        return False
    for node, data in graph.nodes(data=True):
        node_chunks = data.get("chunk_indices", [])
        if chunk_idx in node_chunks and len(node_chunks) <= specificity_threshold:
            return True
    return False
