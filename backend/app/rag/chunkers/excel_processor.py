"""
Excel Document Processor
Converts raw Excel sheet data into LangChain Documents suitable for RAG.

Chunking strategy:
  - Each chunk covers a contiguous batch of data rows from a single sheet.
  - The header row is always prepended to the chunk text so the LLM has column context.
  - Chunk size is controlled by EXCEL_CHUNK_ROWS (rows per chunk).

Metadata mapping vs PDF:
  | PDF field       | Excel equivalent                              |
  |-----------------|-----------------------------------------------|
  | page_number     | sheet_index  (1-based sheet position)         |
  | section_title   | "{filename} › {sheet_name}"                   |
  | has_tables      | True  (every Excel chunk IS tabular data)     |
  | has_images      | False (not supported yet)                     |
  | chunk_index     | global chunk counter across all sheets        |
  | source_file     | original filename                             |
  | source_type     | "excel"                                       |
"""

from typing import Dict, List, Tuple

from langchain_core.documents import Document

from app.settings import settings

# How many data rows (excluding the header) per chunk.


def _rows_to_text(header: List[str], rows: List[List[str]]) -> str:
    """
    Render a list of rows as a Markdown-style table string.

    Example output:
        | Name | Age | Salary |
        | Alice | 30 | 50000 |
        | Bob   | 25 | 45000 |
    """

    def fmt_row(r: List[str]) -> str:
        return "| " + " | ".join(str(v) for v in r) + " |"

    lines = [fmt_row(header)]
    # Add a separator after the header to make it easier for the LLM to parse
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        # Pad or trim row to match header length
        padded = row[: len(header)] + [""] * max(0, len(header) - len(row))
        lines.append(fmt_row(padded))
    return "\n".join(lines)


def chunk_excel_sheets(
    sheets: Dict[str, List[List[str]]],
    filename: str,
    chunk_rows: int = settings.excel_chunk_rows,
) -> List[Tuple[str, dict]]:
    """
    Convert sheet data into (text_content, metadata) tuples.

    Args:
        sheets:     {sheet_name: [[row], ...]}  (first row = header)
        filename:   source filename for metadata
        chunk_rows: max data rows per chunk

    Returns:
        List of (page_content, metadata) tuples ready for Document creation.
    """
    results: List[Tuple[str, dict]] = []

    for sheet_index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
        if not rows:
            continue

        header = rows[0]
        data_rows = rows[1:]  # everything after the header

        if not data_rows:
            # Sheet has only a header row — still worth indexing as context
            text = _rows_to_text(header, [])
            text = f"Sheet: {sheet_name}\n\n{text}\n\n[This sheet has no data rows]"
            metadata = _build_metadata(
                filename=filename,
                sheet_name=sheet_name,
                sheet_index=sheet_index,
                row_start=1,
                row_end=1,
                total_rows=0,
            )
            results.append((text, metadata))
            continue

        # Split data rows into batches
        for batch_start in range(0, len(data_rows), chunk_rows):
            batch = data_rows[batch_start : batch_start + chunk_rows]
            row_start = batch_start + 2  # +2: 1-based + skip header row
            row_end = row_start + len(batch) - 1

            table_text = _rows_to_text(header, batch)
            text = f"Sheet: {sheet_name} (rows {row_start}–{row_end})\n\n{table_text}"

            metadata = _build_metadata(
                filename=filename,
                sheet_name=sheet_name,
                sheet_index=sheet_index,
                row_start=row_start,
                row_end=row_end,
                total_rows=len(data_rows),
            )
            results.append((text, metadata))

    return results


def _build_metadata(
    filename: str,
    sheet_name: str,
    sheet_index: int,
    row_start: int,
    row_end: int,
    total_rows: int,
) -> dict:
    return {
        # ── location (mirrors PDF metadata keys) ──────────────────────────────
        "page_number": sheet_index,  # "page" == sheet
        "section_title": f"{filename} › {sheet_name}",
        # ── content type flags ────────────────────────────────────────────────
        "has_tables": True,  # Excel is always tabular
        "has_images": False,
        "ai_summarized": False,
        # ── excel-specific (extra context for display / filtering) ────────────
        "sheet_name": sheet_name,
        "sheet_index": sheet_index,
        "row_start": row_start,
        "row_end": row_end,
        "total_rows": total_rows,
        # ── populated by ingest_pipeline ─────────────────────────────────────
        "source_file": filename,
        "source_type": "excel",
    }


def create_excel_documents(
    sheets: Dict[str, List[List[str]]],
    filename: str,
    chunk_rows: int = settings.excel_chunk_rows,
) -> List[Document]:
    """
    Public entry point: convert sheet data directly into LangChain Documents.
    """
    chunks = chunk_excel_sheets(sheets, filename, chunk_rows)
    docs = []
    for page_content, metadata in chunks:
        docs.append(Document(page_content=page_content, metadata=metadata))

    print(f"  Created {len(docs)} chunk(s) from {filename}")
    return docs
