"""
Ingestion Pipeline
Orchestrates the complete RAG ingestion
"""

from typing import List
from langchain_core.documents import Document

from loaders.pdf_loader import load_pdfs_from_directory
from .document_processor import create_chunks_by_title
from .ai_summarizer import summarise_chunks
from .vector_store import create_vector_store


def run_complete_ingestion_pipeline() -> object:
    """
    Run the complete RAG ingestion pipeline.

    Process flow:
    1. Load all PDFs from directory
    2. Chunk each PDF separately
    3. Apply AI summarization (if enabled)
    4. Store all chunks in vector database

    Returns:
        ChromaDB vectorstore instance
    """

    print("🚀 Starting RAG Ingestion Pipeline")
    print("=" * 50)

    # 1: Partition
    pdfs = load_pdfs_from_directory()

    if not pdfs:
        raise ValueError("No PDFs found to process!")

    print(f"Loaded {len(pdfs)} PDF file(s)\n")

    all_documents: List[Document] = []

    for filename, elements in pdfs.items():
        print(f"\nProcessing: {filename}")
        print(f"{filename}: {len(elements)} elements")

        # 2: Chunk
        chunks = create_chunks_by_title(elements)
        print(f"Chunks: {len(chunks)}")

        # 3: AI Summarisation
        summarised_chunks = summarise_chunks(chunks)

        # 4: Add source metadata to all chunks from this PDF
        for doc in summarised_chunks:
            doc.metadata["source_file"] = filename
            doc.metadata["source_type"] = "pdf"

        all_documents.extend(summarised_chunks)
        print(f"Processed {len(summarised_chunks)} chunks from {filename}")

    # Step 4: Vector Store
    db = create_vector_store(all_documents)

    print(f"Vector store created with {len(all_documents)} chunks")
    return db
