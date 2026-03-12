from typing import List
from langchain_core.documents import Document

from app.core.interfaces.vector_store import VectorStoreProtocol
from app.core.interfaces.graph_store import GraphStoreProtocol
from app.rag.graph.entity_extractor import extract_entities_from_chunk
from app.rag.loaders.pdf_loader import load_pdfs_from_directory
from app.rag.loaders.text_loader import load_text_files_from_directory
from app.rag.loaders.excel_loader import load_excel_files_from_directory
from app.rag.chunkers.pdf_processor import create_chunks_by_title
from app.rag.chunkers.text_processor import create_text_documents
from app.rag.chunkers.excel_processor import create_excel_documents
from app.rag.ingest.ai_summarizer import summarise_chunks


class IngestService:
    """
    Orchestrates the full ingestion pipeline.

    Depends on interfaces — swap ChromaDB for pgvector by passing a
    different vector_store implementation, zero code changes here.
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStoreProtocol,
    ) -> None:
        self._vector_store = vector_store
        self._graph_store = graph_store

    def run(self) -> None:
        """Load → chunk → summarize → build graph → build vector store."""
        print("🚀 Starting RAG Ingestion Pipeline")
        print("=" * 50)

        all_documents: List[Document] = []
        global_chunk_index = 0

        # ── PDFs ──────────────────────────────────────────────────────
        pdfs = load_pdfs_from_directory()
        if pdfs:
            print(f"\nProcessing {len(pdfs)} PDF file(s)...")
            for filename, elements in pdfs.items():
                print(f"\n  PDF: {filename} ({len(elements)} elements)")
                chunks = create_chunks_by_title(elements)
                summarised = summarise_chunks(chunks)
                for doc in summarised:
                    doc.metadata["source_file"] = filename
                    doc.metadata["source_type"] = "pdf"
                    doc.metadata["chunk_index"] = global_chunk_index
                    global_chunk_index += 1
                all_documents.extend(summarised)
                print(f"  → {len(summarised)} chunks")
        else:
            print("No PDF files found — skipping.")

        # ── Excel / CSV ───────────────────────────────────────────────
        excels = load_excel_files_from_directory()
        if excels:
            print(f"\nProcessing {len(excels)} Excel/CSV file(s)...")
            for filename, workbook_data in excels.items():
                print(f"\n  Excel: {filename}")
                docs = create_excel_documents(workbook_data, filename)
                for doc in docs:
                    doc.metadata["chunk_index"] = global_chunk_index
                    global_chunk_index += 1
                all_documents.extend(docs)
                print(f"  → {len(docs)} chunks")
        else:
            print("No Excel/CSV files found — skipping.")

        # ── Text / Markdown ───────────────────────────────────────────
        texts = load_text_files_from_directory()
        if texts:
            print(f"\nProcessing {len(texts)} text file(s)...")
            for filename, content in texts.items():
                print(f"\n  Text: {filename}")
                docs = create_text_documents(content, filename)
                for doc in docs:
                    doc.metadata["chunk_index"] = global_chunk_index
                    global_chunk_index += 1
                all_documents.extend(docs)
                print(f"  → {len(docs)} chunks")
        else:
            print("No text files found — skipping.")

        if not all_documents:
            raise ValueError("No documents found — add files to data/ directories.")

        # ── Knowledge Graph ───────────────────────────────────────────
        print(f"\nExtracting entities from {len(all_documents)} chunks...")
        extractions = self._build_extractions(all_documents)
        self._graph_store.build(extractions)

        # ── Vector Store ──────────────────────────────────────────────
        print(f"\nTotal documents to index: {len(all_documents)}")
        self._vector_store.build(all_documents)
        print(f"\n✅ Ingestion complete — {len(all_documents)} chunks indexed")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_extractions(
        self, documents: List[Document]
    ) -> list[tuple[dict, str, int]]:
        """Run entity extraction on every chunk and return extraction tuples."""
        extractions = []
        for doc in documents:
            chunk_index = doc.metadata.get("chunk_index", 0)
            source_file = doc.metadata.get("source_file", "unknown")
            source_type = doc.metadata.get("source_type", "pdf")

            result = extract_entities_from_chunk(
                chunk_text=doc.page_content,
                source_file=source_file,
                chunk_index=chunk_index,
            )

            # Inject section_title as a guaranteed Section entity
            section_title = doc.metadata.get("section_title")
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
        return extractions
