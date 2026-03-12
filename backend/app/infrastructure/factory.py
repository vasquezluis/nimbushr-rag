from app.core.interfaces.vector_store import VectorStoreProtocol
from app.core.interfaces.graph_store import GraphStoreProtocol
from app.settings import settings


def get_vector_store() -> VectorStoreProtocol:
    """
    Return the configured vector store backend.
    Controlled by settings.vector_store_backend (env: VECTOR_STORE_BACKEND).
    """

    backend = settings.vector_store_backend.lower()

    if backend == "chroma":
        from app.infrastructure.vector_stores.chroma import ChromaVectorStore

        return ChromaVectorStore()

    if backend == "postgres":
        from app.infrastructure.vector_stores.postgres import PgVectorStore

        return PgVectorStore()

    raise ValueError(
        f"Unknown VECTOR_STORE_BACKEND='{backend}'. "
        "Valid options: 'chroma', 'postgres'"
    )


def get_graph_store() -> GraphStoreProtocol:
    """
    Return the configured graph store backend.
    Controlled by settings.graph_store_backend (env: GRAPH_STORE_BACKEND).
    """

    backend = settings.graph_store_backend.lower()

    if backend == "networkx":
        from app.infrastructure.graph_stores.networkx_store import NetworkXGraphStore

        return NetworkXGraphStore()

    if backend == "neo4j":
        from app.infrastructure.graph_stores.neo4j_store import Neo4jGraphStore

        return Neo4jGraphStore()

    raise ValueError(
        f"Unknown GRAPH_STORE_BACKEND='{backend}'. "
        "Valid options: 'networkx', 'neo4j'"
    )
