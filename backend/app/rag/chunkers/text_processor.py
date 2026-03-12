"""
Text/Markdown Document Processor
Converts TextChunk objects into LangChain Documents for RAG ingestion.

Metadata mirrors the PDF/Excel convention so the query engine and frontend
need zero changes:

  | Field           | Value                                         |
  |-----------------|-----------------------------------------------|
  | chunk_index     | global counter across all text files          |
  | page_number     | paragraph index (.txt) / heading index (.md)  |
  | section_title   | heading text (.md) or filename stem (.txt)    |
  | has_tables      | False (not extracted from plain text)         |
  | has_images      | False                                         |
  | ai_summarized   | False                                         |
  | source_file     | original filename                             |
  | source_type     | "text" | "markdown"                           |
"""

from __future__ import annotations

from typing import Dict, List

from langchain_core.documents import Document

from app.rag.loaders.text_loader import TextChunk


def create_text_documents(chunks: List[TextChunk], filename: str) -> List[Document]:
    """
    Convert a mapping of {filename: [TextChunk]} into LangChain Documents.

    Args:
        file_chunks: Output of load_text_files_from_directory()

    Returns:
        List of LangChain Document objects ready for the vector store.
    """
    documents: List[Document] = []
    global_chunk_index = 0

    file_stem = filename.rsplit(".", 1)[0]

    for chunk in chunks:
        metadata = {
            # ── location (mirrors PDF / Excel keys) ──────────────────────
            "chunk_index": global_chunk_index,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title or file_stem,
            # ── content type flags ────────────────────────────────────────
            "has_tables": False,
            "has_images": False,
            "ai_summarized": False,
            # ── source ───────────────────────────────────────────────────
            "source_file": filename,
            "source_type": chunk.source_type,  # "text" | "markdown"
        }

        # Prepend section title so the embedding captures the topic
        titled_content = (
            f"{chunk.section_title}\n\n{chunk.text}"
            if chunk.section_title
            else chunk.text
        )
        documents.append(Document(page_content=titled_content, metadata=metadata))

        global_chunk_index += 1

        print(f"  Created {len(chunks)} chunk(s) from {filename}")

    return documents
