"""
Vector Store Module
Handles ChromaDB vector store creation and operations
"""

from typing import List
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from settings import settings


def create_vector_store(documents: List[Document]) -> Chroma:
    """
    Create and persist ChromaDB vector store.

    Args:
        documents: List of LangChain Document objects to store

    Returns:
        ChromaDB vectorstore instance
    """
    print("🔮 Creating embeddings and storing in ChromaDB...")

    embedding_model = OpenAIEmbeddings(model=settings.embedding_model)

    if settings.clear_existing:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=settings.vector_db_dir)

            # Check if collection exists
            try:
                existing_collection = client.get_collection(
                    name=settings.chroma_collection_name
                )
                print(
                    f"Found existing collection with {existing_collection.count()} documents"
                )
                print(
                    f"Deleting existing collection: {settings.chroma_collection_name}"
                )
                client.delete_collection(name=settings.chroma_collection_name)
                print("Existing collection deleted")

            except Exception:
                print(" No existing collection found - creating new one")
        except Exception as e:
            print(f"Could not check/clear existing collection: {e}")

    # Assign unique IDs to prevent duplicates
    print("Assigning unique IDs to documents...")

    for i, doc in enumerate(documents):
        # Create deterministic ID: source_file + chunk_index
        source_file = doc.metadata.get("source_file", "unknown")
        chunk_index = doc.metadata.get("chunk_index", i)
        doc.metadata["id"] = f"{source_file}::chunk_{chunk_index}"

    # Extract IDs for ChromaDB
    ids = [doc.metadata["id"] for doc in documents]

    # Create ChromaDB vector store
    print("--- Creating vector store ---")
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        ids=ids,
        persist_directory=settings.vector_db_dir,
        collection_name=settings.chroma_collection_name,
        collection_metadata={"hnsw:space": settings.chroma_distance_metric},
    )
    print("--- Finished creating vector store ---")

    return vectorstore
