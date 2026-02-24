"""
Query Engine Module - IMPROVED
Handles RAG queries, retrieval, and answer generation with enhanced metadata
"""

from typing import List

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.settings import settings


def retrieve_chunks(vectorstore: Chroma, query: str) -> List:
    """
    Retrieve relevant chunks from the vector store.

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
                "fetch_k": settings.top_k_chunks * 3,  # Fetch more, then filter
                "lambda_mult": settings.mmr_lambda,  # Balance between relevance and diversity
            },
        )
    else:
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": settings.top_k_chunks,
                "score_threshold": 0.5,
            },  # filter low relevance chunks
        )

    chunks = retriever.invoke(query)
    print(f"Retrieved {len(chunks)} chunks")

    # Log relevance scores if available
    if hasattr(chunks[0], "metadata") and "score" in chunks[0].metadata:
        for i, chunk in enumerate(chunks):
            score = chunk.metadata.get("score", "N/A")
            print(f"  Chunk {i + 1} score: {score}")

    return chunks


def rerank_chunks(chunks: List, query: str, top_n: int = 3) -> List:
    """
    Rerank retrieved chunks using cross-encoder for better relevance.

    Args:
        chunks: Retrieved chunks
        query: Original query
        top_n: Number of top chunks to return (default: all)

    Returns:
        Reranked list of chunks
    """
    if not chunks:
        return chunks

    try:
        from sentence_transformers import CrossEncoder

        # Load cross-encoder model for reranking
        model = CrossEncoder(settings.cross_encoder_model)

        # Prepare pairs for scoring
        pairs = [[query, chunk.page_content] for chunk in chunks]

        # Get relevance scores
        scores = model.predict(pairs)

        # Sort chunks by score
        ranked_indices = scores.argsort()[::-1]
        reranked_chunks = [chunks[idx] for idx in ranked_indices]

        # Optionally limit to top_n
        if top_n:
            reranked_chunks = reranked_chunks[:top_n]

        print(f"Reranked {len(reranked_chunks)} chunks")
        for i, idx in enumerate(ranked_indices[: len(reranked_chunks)]):
            print(f"  Rank {i + 1}: Score {scores[idx]:.4f}")

        return reranked_chunks

    except ImportError:
        print("sentence-transformers not installed, skipping reranking")
        print("Install with: pip install sentence-transformers")
        return chunks
    except Exception as e:
        print(f"Reranking failed, using original order: {e}")
        return chunks


def generate_final_answer(chunks: List, query: str) -> str:
    """
    Generate final answer using multimodal content from retrieved chunks.
    Includes metadata (section titles, page numbers) in context.

    Args:
        chunks: List of retrieved document chunks
        query: Original query string

    Returns:
        Generated answer as string
    """
    try:
        # Initialize LLM (needs vision model for images)
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_completion_tokens=settings.llm_max_tokens,
        )

        # Build context with length management
        context_parts = []
        current_length = 0
        chunks_used = 0

        for i, chunk in enumerate(chunks):
            metadata = chunk.metadata
            source_file = metadata.get("source_file", "Unknown")
            source_type = metadata.get("source_type", "pdf")
            chunk_index = metadata.get("chunk_index", "?")
            section_title = metadata.get("section_title", "Unknown Section")
            ai_summarized = metadata.get("ai_summarized", False)
            has_tables = metadata.get("has_tables", False)
            has_images = metadata.get("has_images", False)

            context_header = f"--- Document {i + 1} ---"
            context_header += f"\nSource: {source_file}"

            if source_type == "excel":
                sheet_name = metadata.get("sheet_name", section_title)
                row_start = metadata.get("row_start")
                row_end = metadata.get("row_end")
                total_rows = metadata.get("total_rows")

                context_header += f"\nSheet: {sheet_name}"
                if row_start and row_end:
                    context_header += f"\nRows: {row_start}–{row_end}"
                if total_rows:
                    context_header += f" (of {total_rows} total)"
                context_header += (
                    "\n[Tabular data — treat values as structured records]"
                )
            else:
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
                print(
                    f"Context limit reached at chunk {i + 1}, using {chunks_used} chunks"
                )
                break

            context_parts.append(chunk_text)
            current_length += chunk_length
            chunks_used += 1

        # Combine all context
        full_context = "\n".join(context_parts)

        # Build the text prompt with enhanced citation instructions
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
- Answer must be in markdown format so that the frontend displays it nicely.

ANSWER:"""

        # Send to AI and get response
        message = HumanMessage(content=prompt_text)
        response = llm.invoke([message])

        return response.content

    except Exception as e:
        print(f"Answer generation failed: {e}")
        import traceback

        traceback.print_exc()
        return "Sorry, I encountered an error while generating the answer."
