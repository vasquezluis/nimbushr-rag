"""
Application Settings
Centralized configuration using Pydantic Settings
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # ======================
    # API Keys
    # ======================
    openai_api_key: str

    # ======================
    # Paths
    # ======================
    # Automatically resolve project root
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "backend" / "data" / "pdfs"
    vector_db_dir: str = "chroma_db"

    # ======================
    # Embedding Model Config
    # ======================
    embedding_model: str = "text-embedding-3-small"

    # ======================
    # LLM Config (for AI summarization)
    # ======================
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0

    # ======================
    # PDF Processing Config
    # ======================
    pdf_strategy: str = "hi_res"  # Options: "fast", "hi_res", "ocr_only"
    infer_table_structure: bool = True
    extract_images: bool = True

    # ======================
    # Chunking Config
    # ======================
    chunk_max_chars: int = 3000
    chunk_new_after: int = 2400
    chunk_combine_under: int = 500

    # ======================
    # AI Summarization Config
    # ======================
    # WARNING: Setting this to True will use GPT-4o for every chunk with tables/images
    use_ai_summarization: bool = True

    # ======================
    # Retriever Config
    # ======================
    top_k_value: int = 2

    # Only use AI summarization for chunks with this many tables or more
    ai_summary_min_tables: int = 2

    # Only use AI summarization for chunks with images
    ai_summary_require_images: bool = False

    # ======================
    # ChromaDB Config
    # ======================
    clear_existing: bool = True
    chroma_collection_name: str = "nimbus_hr_docs"
    chroma_distance_metric: str = "cosine"  # Options: "cosine", "l2", "ip"

    # ======================
    # Pydantic Config
    # ======================
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    def validate_paths(self):
        """Validate that required directories exist."""
        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"PDF directory not found: {self.data_dir}\n"
                f"Please create it and add PDF files."
            )

        # Create vector DB directory if it doesn't exist
        os.makedirs(self.vector_db_dir, exist_ok=True)

    def get_chunk_config(self) -> dict:
        """Get chunking configuration as a dictionary."""
        return {
            "max_characters": self.chunk_max_chars,
            "new_after_n_chars": self.chunk_new_after,
            "combine_text_under_n_chars": self.chunk_combine_under,
        }

    def should_use_ai_summary(self, num_tables: int, num_images: int) -> bool:
        """
        Determine if AI summarization should be used for a chunk.

        Args:
            num_tables: Number of tables in the chunk
            num_images: Number of images in the chunk

        Returns:
            bool: Whether to use AI summarization
        """
        if not self.use_ai_summarization:
            return False

        # Check table threshold
        if num_tables >= self.ai_summary_min_tables:
            return True

        # Check image requirement
        if self.ai_summary_require_images and num_images > 0:
            return True

        # If images not required, any image triggers summarization
        if not self.ai_summary_require_images and num_images > 0:
            return True

        return False

    def display_config(self):
        """Print current configuration (for debugging)."""
        print("\n" + "=" * 60)
        print("CONFIGURATION")
        print("=" * 60)
        print(f"Data Directory: {self.data_dir}")
        print(f"Vector DB Directory: {self.vector_db_dir}")
        print(f"Embedding Model: {self.embedding_model}")
        print(f"LLM Model: {self.llm_model}")
        print(f"PDF Strategy: {self.pdf_strategy}")
        print(f"Chunk Max Chars: {self.chunk_max_chars}")
        print(
            f"AI Summarization: {'Enabled' if self.use_ai_summarization else 'Disabled'}"
        )
        if self.use_ai_summarization:
            print(f"   └─ Min Tables: {self.ai_summary_min_tables}")
            print(f"   └─ Require Images: {self.ai_summary_require_images}")
        print("=" * 60 + "\n")


# Create global settings instance
settings = Settings()
