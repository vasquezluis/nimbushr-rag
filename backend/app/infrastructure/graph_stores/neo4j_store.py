# Future: Neo4j implementation
# To activate: set GRAPH_STORE_BACKEND=neo4j in .env


class Neo4jGraphStore:
    """Neo4j implementation of GraphStoreProtocol — not yet implemented."""

    def build(self, extractions: list[tuple[dict, str, int]]) -> None:
        raise NotImplementedError("Neo4jGraphStore.build() not implemented yet")

    def load(self) -> bool:
        raise NotImplementedError

    def retrieve(self, query: str, max_chunks: int) -> tuple[list[int], list[dict]]:
        raise NotImplementedError
