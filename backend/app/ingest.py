"""
Ingestion Pipeline Entry Point
Run this script to ingest all PDFs into the vector database
"""

import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from settings import settings
from app.infrastructure.factory import get_vector_store, get_graph_store
from app.services.ingest_service import IngestService

# Load environment variables
load_dotenv()


def main():
    """Main entry point for ingestion pipeline."""

    print("\n" + "=" * 70)
    print("NIMBUS HR - RAG INGESTION PIPELINE")
    print("=" * 70)

    # Display current configuration
    settings.display_config()

    # Validate environment
    try:
        settings.validate_paths()
    except FileNotFoundError as e:
        print(f"Configuration Error: {e}")
        return 1
    except Exception as e:
        print(f"Validation Error: {e}")
        return 1

    # Check for OpenAI API key
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with: OPENAI_API_KEY=your-key-here")
        return 1

    # Run the ingestion pipeline
    try:
        print("Starting ingestion...\n")
        vector_store = get_vector_store()
        graph_store = get_graph_store()
        IngestService(vector_store, graph_store).run()

        print("\n" + "=" * 70)
        print("INGESTION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Vector store saved to: {settings.vector_db_dir}")
        print(f"Collection: {settings.chroma_collection_name}")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        print(f"\nError during ingestion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
