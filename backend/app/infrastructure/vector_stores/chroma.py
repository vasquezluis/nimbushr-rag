from typing import Optional
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.models import Chunk
from app.settings import settings


class ChromaVectorStore:
    """
    ChromaDB implementation of VectorStoreProtocol.

    Owns the Chroma client lifecycle
    """

    def __init__(self) -> None:
        self._store: Optional[Chroma] = None
        self._embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def build(self, documents: list[Document]) -> None:
        """Create (or overwrite) the ChromaDB collection from documents."""
        print("Creating embeddings and storing in ChromaDB...")

        if settings.clear_existing:
            self._drop_collection()

        # Assign deterministic IDs to prevent duplicates on re-ingestion
        for i, doc in enumerate(documents):
            source_file = doc.metadata.get("source_file", "unknown")
            chunk_index = doc.metadata.get("chunk_index", i)
            doc.metadata["id"] = f"{source_file}::chunk_{chunk_index}"

        ids = [doc.metadata["id"] for doc in documents]

        self._store = Chroma.from_documents(
            documents=documents,
            embedding=self._embeddings,
            ids=ids,
            persist_directory=settings.vector_db_dir,
            collection_name=settings.chroma_collection_name,
            collection_metadata={"hnsw:space": settings.chroma_distance_metric},
        )
        print(f"ChromaDB collection built with {len(documents)} documents")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load an existing persisted collection into memory."""
        print(f"Loading ChromaDB from {settings.vector_db_dir}...")

        self._store = Chroma(
            persist_directory=settings.vector_db_dir,
            collection_name=settings.chroma_collection_name,
            embedding_function=self._embeddings,
        )

        count = self._store._collection.count()

        if count == 0:
            raise ValueError("ChromaDB collection is empty — run ingestion first.")

        print(f"Loaded ChromaDB: {count} documents")

    def similarity_search(self, query: str, k: int) -> list[Chunk]:
        self._assert_loaded()

        if settings.use_mmr:
            retriever = self._store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": k,
                    "fetch_k": k * 3,
                    "lambda_mult": settings.mmr_lambda,
                },
            )
        else:
            retriever = self._store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"k": k, "score_threshold": 0.5},
            )

        docs = retriever.invoke(query)

        return [Chunk(content=d.page_content, metadata=d.metadata) for d in docs]

    def fetch_by_indices(self, indices: list[int]) -> list[Chunk]:
        """Bridge graph chunk_indices → actual text chunks."""

        self._assert_loaded()

        if not indices:
            return []

        results = self._store._collection.get(
            where={"chunk_index": {"$in": [int(i) for i in indices]}},
            include=["documents", "metadatas"],
        )

        if not results or not results.get("documents"):
            return []

        return [
            Chunk(content=text, metadata=meta)
            for text, meta in zip(results["documents"], results["metadatas"])
        ]

    def get_all_metadata(self) -> list[dict]:
        self._assert_loaded()

        data = self._store._collection.get(include=["metadatas"])

        return data.get("metadatas", [])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _drop_collection(self) -> None:
        try:
            client = chromadb.PersistentClient(path=settings.vector_db_dir)

            try:
                existing = client.get_collection(settings.chroma_collection_name)

                print(f"Dropping existing collection ({existing.count()} docs)...")

                client.delete_collection(settings.chroma_collection_name)
            except Exception:
                print("No existing collection found — creating fresh.")
        except Exception as e:
            print(f"Could not check/clear existing collection: {e}")

    def _assert_loaded(self) -> None:
        if self._store is None:
            raise RuntimeError(
                "ChromaVectorStore not loaded — call load() or build() first."
            )
