"""
Streaming Query Engine Module
Handles RAG queries with real-time token streaming and metadata
"""

from typing import Any, AsyncGenerator, Dict, List

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.settings import settings


async def retrieve_chunks_async(vectorstore: Chroma, query: str) -> List:
    """
    Retrieve relevant chunks from the vector store (async version).

    Args:
        vectorstore: ChromaDB vector store instance
        query: Query string to search for

    Returns:
        List of retrieved document chunks
    """
    print(f"Retrieving top {settings.top_k_chunks} chunks for query: {query}")

    if settings.use_mmr:
        # Use MMR for diverse results (reduces redundancy)
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.top_k_chunks,
                "fetch_k": settings.top_k_chunks * 3,
                "lambda_mult": settings.mmr_lambda,
            },
        )
    else:
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": settings.top_k_chunks,
                "score_threshold": 0.5,
            },
        )

    # Use ainvoke for async retrieval
    chunks = await retriever.ainvoke(query)
    print(f"Retrieved {len(chunks)} chunks")

    return chunks


async def rerank_chunks_async(chunks: List, query: str, top_n: int = 0) -> List:
    """
    Rerank retrieved chunks using cross-encoder (async version).

    Args:
        chunks: Retrieved chunks
        query: Original query
        top_n: Number of top chunks to return

    Returns:
        Reranked list of chunks
    """
    if not chunks:
        return chunks

    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(settings.cross_encoder_model)
        pairs = [[query, chunk.page_content] for chunk in chunks]
        scores = model.predict(pairs)
        ranked_indices = scores.argsort()[::-1]
        reranked_chunks = [chunks[idx] for idx in ranked_indices]

        if top_n:
            reranked_chunks = reranked_chunks[:top_n]

        print(f"Reranked {len(reranked_chunks)} chunks")
        return reranked_chunks

    except ImportError:
        print("sentence-transformers not installed, skipping reranking")
        return chunks
    except Exception as e:
        print(f"Reranking failed: {e}")
        return chunks


def build_context_from_chunks(chunks: List) -> tuple[str, List[Dict[str, Any]]]:
    """
    Build context string from chunks and extract source metadata.

    Args:
        chunks: List of retrieved document chunks

    Returns:
        Tuple of (context_string, sources_list)
    """

    context_parts = []
    sources = []
    current_length = 0
    chunks_used = 0

    for i, chunk in enumerate(chunks):
        metadata = chunk.metadata
        source_file = metadata.get("source_file", "Unknown")
        source_type = metadata.get("source_type", "pdf")  # "pdf" | "excel"
        chunk_index = metadata.get("chunk_index", "?")
        section_title = metadata.get("section_title", "Unknown Section")
        ai_summarized = metadata.get("ai_summarized", False)
        has_tables = metadata.get("has_tables", False)
        has_images = metadata.get("has_images", False)

        context_header = f"--- Document {i + 1} ---"
        context_header += f"\nSource: {source_file}"

        if source_type == "excel":
            # Excel: sheet-aware location info
            sheet_name = metadata.get("sheet_name", section_title)
            row_start = metadata.get("row_start")
            row_end = metadata.get("row_end")
            total_rows = metadata.get("total_rows")

            context_header += f"\nSheet: {sheet_name}"
            if row_start and row_end:
                context_header += f"\nRows: {row_start}–{row_end}"
            if total_rows:
                context_header += f" (of {total_rows} total)"
            context_header += "\n[Tabular data — treat values as structured records]"
        else:
            # PDF: page/section location info
            page_number = metadata.get("page_number")
            page_span = metadata.get("page_span")

            context_header += f"\nSection: {section_title}"
            if page_span:
                context_header += f"\nPages: {page_span}"
            elif page_number:
                context_header += f"\nPage: {page_number}"

            content_indicators = []
            if has_tables:
                content_indicators.append("tables")
            if has_images:
                content_indicators.append("images")
            if content_indicators:
                context_header += f"\n[Contains: {', '.join(content_indicators)}]"
            if ai_summarized:
                context_header += "\n[AI-enhanced summary]"

        context_header += f"\nChunk: {chunk_index}"

        chunk_text = f"{context_header}\n\n{chunk.page_content}\n"
        chunk_length = len(chunk_text)

        if current_length + chunk_length > settings.max_context_length:
            print(f"Context limit reached at chunk {i + 1}, using {chunks_used} chunks")
            break

        context_parts.append(chunk_text)
        current_length += chunk_length
        chunks_used += 1

        sources.append(
            {
                "file": source_file,
                "source_type": source_type,
                "section": section_title,
                # PDF fields
                "page": metadata.get("page_number"),
                "page_span": metadata.get("page_span"),
                # Excel fields
                "sheet_name": metadata.get("sheet_name"),
                "row_start": metadata.get("row_start"),
                "row_end": metadata.get("row_end"),
                # Common
                "chunk_index": chunk_index,
                "has_tables": has_tables,
                "has_images": has_images,
                "ai_summarized": ai_summarized,
            }
        )

    return "\n".join(context_parts), sources


async def stream_answer(
    chunks: List, query: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream answer tokens in real-time from the LLM.

    Args:
        chunks: List of retrieved document chunks
        query: Original query string

    Yields:
        Dictionary with streaming events:
        - {"type": "sources", "data": [...]} - Source information
        - {"type": "token", "data": "..."} - Individual token
        - {"type": "done", "data": None} - Streaming complete
    """

    try:
        # Build context and get sources
        full_context, sources = build_context_from_chunks(chunks)

        # First, yield source information
        yield {"type": "sources", "data": sources, "num_chunks": len(chunks)}

        # Initialize streaming LLM
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            streaming=True,  # Enable streaming
            max_completion_tokens=settings.llm_max_tokens,
        )

        # Build the prompt with citation instructions
        prompt_text = f"""Based on the following documents, please answer this question: {query}

RETRIEVED DOCUMENTS:
{full_context}

INSTRUCTIONS:
- Provide a clear, comprehensive answer using the information above.
- Adapt your citation style to the source type:
    • PDF:   "According to [filename] ([Section], Page [N])…"
    • Excel: "According to [filename] (Sheet: [sheet], rows [X]–[Y])…"
- For Excel/tabular data: reference specific column values, highlight patterns,
  summarise aggregates, or compare rows as appropriate to the question.
- For PDF content: use section names and page numbers to anchor your answer.
- If documents contain tables or images whose content has been AI-analysed, use that analysis.
- Be specific — use concrete values and details from the documents.
- If information is insufficient, clearly state what is missing.
- If sources conflict, acknowledge the discrepancy and explain both sides.

ANSWER:"""

        message = HumanMessage(content=prompt_text)

        # Stream tokens from the LLM
        finish_reason = None

        async for chunk in llm.astream([message]):
            if chunk.content:
                yield {"type": "token", "data": chunk.content}
            # Capture finish_reason from response metadata
            if hasattr(chunk, "response_metadata") and chunk.response_metadata:
                finish_reason = chunk.response_metadata.get("finish_reason")

        # Signal completion — warn frontend if truncated
        if finish_reason == "length":
            yield {
                "type": "token",
                "data": "\n\n⚠️ *Response was truncated due to length limits.*",
            }

        yield {"type": "done", "data": None}

    except Exception as e:
        print(f"Streaming failed: {e}")
        import traceback

        traceback.print_exc()
        yield {
            "type": "error",
            "data": f"Error generating answer: {str(e)}",
        }
