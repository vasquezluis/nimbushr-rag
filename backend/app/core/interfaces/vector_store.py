from typing import Protocol, runtime_checkable
from langchain_core.documents import Document
from app.core.models import Chunk


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """
    Contract for any vector store backend (ChromaDB, pgvector, Pinecone, etc.).

    Two modes:
      - ingest:  build() creates/overwrites the store from a list of Documents
      - query:   similarity_search() and fetch_by_indices() retrieve chunks

    The store owns its own connection lifecycle — callers never import
    chromadb, psycopg2, etc. directly.
    """

    def build(self, documents: list[Document]) -> None:
        """
        Create (or overwrite) the vector store from a list of LangChain Documents.
        Called once during ingestion.
        """
        ...

    def similarity_search(self, query: str, k: int) -> list[Chunk]:
        """
        Return the top-k semantically similar chunks for a query.
        MMR / score-threshold logic lives inside the implementation.
        """
        ...

    def fetch_by_indices(self, indices: list[int]) -> list[Chunk]:
        """
        Fetch specific chunks by their chunk_index metadata value.
        Used by the hybrid retriever to bridge graph indices → text.
        """
        ...

    def get_all_metadata(self) -> list[dict]:
        """
        Return raw metadata dicts for every stored chunk.
        Used by the /files endpoint to build file listings.
        """
        ...
