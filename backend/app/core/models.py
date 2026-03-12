from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """
    Canonical representation of a retrieved document chunk.
    Decouples the rest of the app from LangChain's Document type.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    # Convenience accessors so callers don't dig into metadata
    @property
    def source_file(self) -> str:
        return self.metadata.get("source_file", "Unknown")

    @property
    def chunk_index(self) -> int:
        return self.metadata.get("chunk_index", 0)

    @property
    def has_tables(self) -> bool:
        return self.metadata.get("has_tables", False)

    @property
    def has_images(self) -> bool:
        return self.metadata.get("has_images", False)

    @property
    def ai_summarized(self) -> bool:
        return self.metadata.get("ai_summarized", False)


@dataclass
class HybridRetrievalResult:
    """What the query service gets back from the stores."""

    chunks: list[Chunk]
    graph_traversal: list[dict]  # matched_nodes for frontend visualization
