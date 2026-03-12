"""
Files API Route
Returns list of files loaded into the vector store and serves PDF files
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.api.deps import get_query_service
from app.services.query_service import QueryService

from app.settings import settings

router = APIRouter(tags=["Files"])


class FileInfo(BaseModel):
    """Information about a loaded file"""

    filename: str
    source_type: str
    chunk_count: int
    has_tables: bool
    has_images: bool
    ai_summarized_chunks: int


class FilesListResponse(BaseModel):
    """Response containing list of loaded files"""

    files: List[FileInfo]
    total_files: int
    total_chunks: int


@router.get("/files", response_model=FilesListResponse)
async def list_loaded_files(service: QueryService = Depends(get_query_service)):
    """
    Get list of all files loaded into the vector store.

    Returns:
        FilesListResponse with file metadata and statistics
    """
    try:

        # Aggregate data by source file
        files_dict = {}

        metadatas = service._vector_store.get_all_metadata()

        for metadata in metadatas:
            source_file = metadata.get("source_file", "Unknown")
            source_type = metadata.get("source_type", "unknown")

            if source_file not in files_dict:
                files_dict[source_file] = {
                    "filename": source_file,
                    "source_type": source_type,
                    "chunk_count": 0,
                    "has_tables": False,
                    "has_images": False,
                    "ai_summarized_chunks": 0,
                }

            # Update statistics
            files_dict[source_file]["chunk_count"] += 1

            if metadata.get("has_tables", False):
                files_dict[source_file]["has_tables"] = True

            if metadata.get("has_images", False):
                files_dict[source_file]["has_images"] = True

            if metadata.get("ai_summarized", False):
                files_dict[source_file]["ai_summarized_chunks"] += 1

        # Convert to list and sort by filename
        files_list = sorted(files_dict.values(), key=lambda x: x["filename"])

        return FilesListResponse(
            files=files_list,
            total_files=len(files_list),
            total_chunks=len(metadatas),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving files list: {str(e)}"
        )


@router.get("/files/{filename}")
async def get_file(filename: str):
    """
    Serve a file from the correct data directory based on its extension.
    Supports: PDF, Excel (.xlsx, .xls, .csv), and text (.txt, .md).
    """
    try:
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        if suffix == "pdf":
            file_path = settings.pdf_data_dir / filename
            media_type = "application/pdf"
        elif suffix in ("xlsx", "xls"):
            file_path = settings.excel_data_dir / filename
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif suffix == "csv":
            file_path = settings.excel_data_dir / filename
            media_type = "text/csv"
        elif suffix in ("txt", "md"):
            file_path = settings.text_data_dir / filename
            media_type = "text/plain; charset=utf-8"
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file type: .{suffix}"
            )

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        return FileResponse(
            path=str(file_path), media_type=media_type, filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")


@router.get("/files/{filename}/chunks")
async def get_file_chunks(
    filename: str, service: QueryService = Depends(get_query_service)
):
    """
    Get all chunks for a specific file with their metadata.
    Useful for showing which parts of the document were used in RAG responses.

    Args:
        filename: Name of the source file

    Returns:
        List of chunks with metadata for the specified file
    """
    try:
        metadatas = service._vector_store.get_all_metadata()

        # Build response with chunk details
        chunks = []
        for i, (doc, metadata) in enumerate(metadatas):
            chunk_info = {
                "chunk_index": metadata.get("chunk_index", i),
                "content_preview": doc[:200] + "..." if len(doc) > 200 else doc,
                "content_length": len(doc),
                "has_tables": metadata.get("has_tables", False),
                "has_images": metadata.get("has_images", False),
                "num_tables": metadata.get("num_tables", 0),
                "num_images": metadata.get("num_images", 0),
                "ai_summarized": metadata.get("ai_summarized", False),
                "content_types": metadata.get("content_types", ""),
                "text_preview": metadata.get("text_preview", ""),
            }
            chunks.append(chunk_info)

        # Sort by chunk_index
        chunks.sort(key=lambda x: x["chunk_index"])

        return {"filename": filename, "total_chunks": len(chunks), "chunks": chunks}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving chunks: {str(e)}"
        )
