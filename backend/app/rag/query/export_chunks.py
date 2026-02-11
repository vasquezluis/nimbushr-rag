"""
Export Chunks Module
Helper to export chunks to json
"""

import json
from typing import List


def export_chunks_to_json(chunks: List) -> List:
    """
    Export processed chunks to clean JSON format.

    Args:
        chunks: List of document chunks to export
        filename: Output filename for the JSON export

    Returns:
        List of exported chunk data
    """
    export_data = []

    for i, doc in enumerate(chunks):
        chunk_data = {
            "chunk_id": doc.id,
            "enhanced_content": doc.page_content,
            "metadata": {
                "id": doc.metadata.get("id"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "has_tables": doc.metadata.get("has_tables"),
                "has_images": doc.metadata.get("has_images"),
                "num_tables": doc.metadata.get("num_tables"),
                "num_images": doc.metadata.get("num_images"),
                "ai_summarized": doc.metadata.get("ai_summarized"),
                "content_types": doc.metadata.get("content_types", "{}"),
                "text_length": doc.metadata.get("text_length"),
                "text_preview": doc.metadata.get("text_preview"),
                "content_summary": doc.metadata.get("content_summary", "{}"),
                "source_file": doc.metadata.get("source_file"),
                "source_type": doc.metadata.get("source_type"),
            },
        }
        export_data.append(chunk_data)

    # Save to file
    with open("chunks_export.json", "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(export_data)} chunks to {'chunks_export.json'}")
    return export_data
