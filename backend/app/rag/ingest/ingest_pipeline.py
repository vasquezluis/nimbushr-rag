"""
Ingestion Pipeline
Orchestrates the complete RAG ingestion for PDFs and Excel/CSV files.
"""

from typing import List

from langchain_core.documents import Document

from app.rag.graph.entity_extractor import extract_entities_from_chunk
from app.rag.graph.knowledge_graph import (
    build_graph_from_extractions,
    merge_duplicate_nodes,
    save_graph,
)
from app.rag.loaders.pdf_loader import load_pdfs_from_directory
from app.rag.loaders.text_loader import load_text_files_from_directory
from app.rag.loaders.excel_loader import load_excel_files_from_directory
from app.rag.chunkers.pdf_processor import create_chunks_by_title
from app.rag.chunkers.text_processor import create_text_documents
from app.rag.chunkers.excel_processor import create_excel_documents
from app.rag.ingest.ai_summarizer import summarise_chunks
from app.rag.ingest.vector_store import create_vector_store
from app.settings import settings


def run_complete_ingestion_pipeline() -> object:
    """
    Run the complete RAG ingestion pipeline.

    Process flow:
    1. Load all PDFs  → unstructured elements → chunk_by_title → AI summarise
    2. Load all Excel/CSV → sheet rows → row-batch chunks (no AI summarise needed,
       tabular data is already structured)
    3. Store everything in the vector database.

    Returns:
        ChromaDB vectorstore instance
    """
    print("🚀 Starting RAG Ingestion Pipeline")
    print("=" * 50)

    all_documents: List[Document] = []
    global_chunk_index = 0 # single counter for all chunks

    # ── PDFs ──────────────────────────────────────────────────────────────────
    pdfs = load_pdfs_from_directory()

    if pdfs:
        print(f"\nProcessing {len(pdfs)} PDF file(s)...")
        for filename, elements in pdfs.items():
            print(f"\n  PDF: {filename} ({len(elements)} elements)")

            chunks = create_chunks_by_title(elements)
            summarised_chunks = summarise_chunks(chunks)

            for doc in summarised_chunks:
                doc.metadata["source_file"] = filename
                doc.metadata["source_type"] = "pdf"
                doc.metadata["chunk_index"] = global_chunk_index
                global_chunk_index += 1

            all_documents.extend(summarised_chunks)
            print(f"  → {len(summarised_chunks)} chunks")
    else:
        print("No PDF files found — skipping PDF ingestion.")

    # ── Excel / CSV ───────────────────────────────────────────────────────────
    excel_files = load_excel_files_from_directory(settings.excel_data_dir)

    if excel_files:
        print(f"\nProcessing {len(excel_files)} Excel/CSV file(s)...")
        for filename, sheets in excel_files.items():
            print(f"\n  Excel: {filename} ({len(sheets)} sheet(s))")

            docs = create_excel_documents(sheets, filename)
            for doc in docs:
                doc.metadata["chunk_index"] = global_chunk_index
                global_chunk_index += 1
            all_documents.extend(docs)
    else:
        print("No Excel/CSV files found — skipping Excel ingestion.")

    # ── Text / Markdown ───────────────────────────────────────────────────────
    text_files = load_text_files_from_directory(settings.text_data_dir)

    if text_files:
        print(f"\nProcessing {len(text_files)} text/markdown file(s)...")
        text_docs = create_text_documents(text_files)
        for doc in text_docs:
            doc.metadata["chunk_index"] = global_chunk_index
            global_chunk_index += 1
        all_documents.extend(text_docs)
    else:
        print("No .txt / .md files found — skipping text ingestion.")

    # ── Guard ─────────────────────────────────────────────────────────────────
    if not all_documents:
        raise ValueError(
            "No documents found to process! Addfiles to the data directories."
        )

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    # Build the graph from ALL documents (PDFs, Excel, text) after they're
    # all collected. We extract entities from each doc's page_content.
    print(f"\nBuilding knowledge graph from {len(all_documents)} chunks...")

    extractions = []

    for doc in all_documents:
        chunk_index = doc.metadata.get("chunk_index", 0)
        source_file = doc.metadata.get("source_file", "unknown")
        source_type = doc.metadata.get("source_type", "pdf")

        result = extract_entities_from_chunk(
            chunk_text=doc.page_content,
            source_file=source_file,
            chunk_index=chunk_index,
        )

        # inject section_title as an entity if it exists
        section_title = doc.metadata.get("section_title")

        # Excel section_title is "filename › SheetName" — strip filename prefix for the graph
        # The node is just "SheetName", which is matchable from queries
        if source_type == "excel" and section_title and "›" in section_title:
            section_title = section_title.split("›", 1)[-1].strip()

        if section_title and section_title != "Unknown Section":
            result["entities"].append(
                {
                    "name": section_title,
                    "type": "Section",
                    "description": f"Section from {source_file}",
                }
            )
            result["relationships"].append(
                {
                    "source": source_file,
                    "target": section_title,
                    "relation": "contains_section",
                }
            )

        extractions.append((result, source_file, chunk_index))

    graph = build_graph_from_extractions(extractions)
    graph = merge_duplicate_nodes(graph)
    save_graph(graph)

    # ── Vector Store ──────────────────────────────────────────────────────────
    print(f"\nTotal documents to index: {len(all_documents)}")
    db = create_vector_store(all_documents)

    print(f"\n✅ Vector store created with {len(all_documents)} chunks")
    return db
