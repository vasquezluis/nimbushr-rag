"""
Query Engine Module
Handles RAG queries, retrieval, and answer generation
"""

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_chroma import Chroma
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
    print(f"Retrieving top {settings.top_k_value} chunks for query: {query}")
    retriever = vectorstore.as_retriever(search_kwargs={"k": settings.top_k_value})
    chunks = retriever.invoke(query)
    print(f"Retrieved {len(chunks)} chunks")
    return chunks


def generate_final_answer(chunks: List, query: str) -> str:
    """
    Generate final answer using multimodal content from retrieved chunks.

    Args:
        chunks: List of retrieved document chunks
        query: Original query string

    Returns:
        Generated answer as string
    """
    try:
        # Initialize LLM (needs vision model for images)
        llm = ChatOpenAI(model=settings.llm_model, temperature=settings.llm_temperature)

        # Build the context from enhanced chunks
        context_parts = []

        for i, chunk in enumerate(chunks):
            source_file = chunk.metadata.get("source_file", "Unknown")
            chunk_index = chunk.metadata.get("chunk_index", "?")
            ai_summarized = chunk.metadata.get("ai_summarized", False)
            has_tables = chunk.metadata.get("has_tables", False)
            has_images = chunk.metadata.get("has_images", False)
            num_tables = chunk.metadata.get("num_tables", 0)
            num_images = chunk.metadata.get("num_images", 0)

            # Build context header
            context_header = f"--- Document {i+1} (Source: {source_file}, Chunk: {chunk_index}) ---"

            # Add content type indicators
            content_indicators = []

            if has_tables:
                content_indicators.append(f"{num_tables} table(s)")
            if has_images:
                content_indicators.append(f"{num_images} image(s)")

            if content_indicators:
                context_header += f"\n[Contains: {', '.join(content_indicators)}]"

            if ai_summarized:
                context_header += "\n[AI-enhanced summary of multimodal content]"

            # Add the enhanced content
            context_parts.append(f"{context_header}\n\n{chunk.page_content}\n")

        # Combine all context
        full_context = "\n".join(context_parts)

        # Build the text prompt
        prompt_text = f"""Based on the following documents, please answer this question: {query}

RETRIEVED DOCUMENTS:
{full_context}

INSTRUCTIONS:
- Provide a clear, comprehensive answer using the information above
- If documents contain tables or images, their content has been analyzed and included in the summaries
- Cite specific sources by their filename when referencing information (e.g., "According to employee_handbook.pdf..." or "As stated in benefits_policy.pdf...")
- If the documents don't contain sufficient information to answer the question, clearly state this
- Be specific and use concrete details from the documents

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
