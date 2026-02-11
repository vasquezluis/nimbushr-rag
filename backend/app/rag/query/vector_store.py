"""
Vector Store Module
Handles ChromaDB vector store operations
"""

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.settings import settings


def load_vector_store() -> Chroma:
    """
    Load an existing ChromaDB vector store.

    Args:
        persist_directory: Directory path where the vector store is persisted

    Returns:
        ChromaDB vectorstore instance
    """
    print(f"Loading vector store from {settings.vector_db_dir}...")

    embedding_model = OpenAIEmbeddings(model=settings.embedding_model)

    try:
        vectorstore = Chroma(
            persist_directory=settings.vector_db_dir,
            collection_name=settings.chroma_collection_name,
            embedding_function=embedding_model,
        )

        collection_count = vectorstore._collection.count()

        print(f"Loaded vector store with {collection_count} documents")

        if collection_count == 0:
            raise ValueError("Collection exists but contains no documents")

        return vectorstore

    except Exception as e:
        raise ValueError(f"Could not load vector store: {e}")
