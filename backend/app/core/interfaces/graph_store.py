from typing import Protocol, runtime_checkable


@runtime_checkable
class GraphStoreProtocol(Protocol):
    """
    Contract for any graph store backend (NetworkX/JSON, Neo4j, etc.).

    Two modes:
      - ingest:  build() constructs the graph from entity extractions
      - query:   retrieve() returns chunks + traversal metadata
    """

    def build(self, extractions: list[tuple[dict, str, int]]) -> None:
        """
        Build (or rebuild) the graph from entity extraction results.

        extractions: list of (extraction_dict, source_file, chunk_index)
          where extraction_dict = {"entities": [...], "relationships": [...]}
        """
        ...

    def retrieve(self, query: str, max_chunks: int) -> tuple[list[int], list[dict]]:
        """
        Return (chunk_indices, matched_nodes) for a query.

        chunk_indices  — indices to fetch from the vector store
        matched_nodes  — traversal metadata for frontend visualization
        """
        ...

    def load(self) -> bool:
        """
        Load the persisted graph into memory.
        Returns True if successful, False if no graph exists yet.
        """
        ...

    def is_specific_match(
        self, chunk_index: int, specificity_threshold: int = 3
    ) -> bool:
        """
        Return True if chunk_index belongs to a small/specific node.
        Backends that don't support this concept should return False.
        """
        ...
