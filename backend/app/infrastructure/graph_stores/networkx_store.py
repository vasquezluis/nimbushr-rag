from typing import Optional
import networkx as nx

from app.rag.graph.knowledge_graph import (
    build_graph_from_extractions,
    merge_duplicate_nodes,
    save_graph,
    load_graph,
)
from app.rag.graph.graph_retriever import retrieve_chunks_from_graph


class NetworkXGraphStore:
    """
    NetworkX + JSON file implementation of GraphStoreProtocol.

    All graph logic in rag/graph/
    """

    def __init__(self) -> None:
        self._graph: Optional[nx.DiGraph] = None

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def build(self, extractions: list[tuple[dict, str, int]]) -> None:
        """Build the graph from entity extraction results and persist it."""

        print(f"Building knowledge graph from {len(extractions)} extractions...")

        graph = build_graph_from_extractions(extractions)
        graph = merge_duplicate_nodes(graph)

        save_graph(graph)
        self._graph = graph

        print("✅ Knowledge graph built and saved")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """Load graph from disk. Returns False if no graph file exists yet."""

        try:
            self._graph = load_graph()

            return True
        except Exception as e:
            print(f"Could not load knowledge graph: {e}")

            return False

    def retrieve(self, query: str, max_chunks: int) -> tuple[list[int], list[dict]]:
        """Return (chunk_indices, matched_nodes) for hybrid retrieval."""

        result = retrieve_chunks_from_graph(query, self._graph, max_chunks=max_chunks)

        return result["chunk_indices"], result["matched_nodes"]

    @property
    def graph(self) -> Optional[nx.DiGraph]:
        """Expose raw graph for components that still need it (hybrid retriever)."""

        return self._graph
