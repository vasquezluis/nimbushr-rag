# Future: pgvector implementation
# To activate: set VECTOR_STORE_BACKEND=postgres in .env
# Then implement each method using psycopg2 + pgvector extension.

from langchain_core.documents import Document
from app.core.models import Chunk


class PgVectorStore:
    """pgvector implementation of VectorStoreProtocol — not yet implemented."""

    def build(self, documents: list[Document]) -> None:
        raise NotImplementedError("PgVectorStore.build() not implemented yet")

    def load(self) -> None:
        raise NotImplementedError("PgVectorStore.load() not implemented yet")

    def similarity_search(self, query: str, k: int) -> list[Chunk]:
        raise NotImplementedError

    def fetch_by_indices(self, indices: list[int]) -> list[Chunk]:
        raise NotImplementedError

    def get_all_metadata(self) -> list[dict]:
        raise NotImplementedError
