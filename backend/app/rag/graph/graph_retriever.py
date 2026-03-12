"""
Graph Retriever Module
Given a user query, extracts entities from it and traverses the graph
to find related chunks. This is the "graph" side of our hybrid retrieval.

The flow:
  1. Extract entities from the query (same extractor we use at ingestion)
  2. Find matching nodes in the graph (fuzzy match on entity names)
  3. Traverse 1-2 hops to find related nodes
  4. Collect chunk_indices from all found nodes
  5. Return those indices so the query engine can fetch the actual chunks
"""

from difflib import SequenceMatcher
from typing import Optional, TypedDict

import networkx as nx

from app.rag.graph.entity_extractor import extract_entities_from_query
from app.rag.graph.knowledge_graph import _normalize_name


class GraphTraversalResult(TypedDict):
    chunk_indices: list[int]
    matched_nodes: list[dict]  # {name, entity_type, chunk_indices, neighbors}


def _similarity(a: str, b: str) -> float:
    """
    Simple string similarity ratio between 0 and 1.
    We use this instead of exact matching because the LLM might extract
    "Remote Work Policy" from the query but the graph has "Remote Work Policy"
    stored with slightly different casing.
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_matching_nodes(
    graph: nx.DiGraph,
    entity_name: str,
    entity_type: str = "",
    threshold: float = 0.65,
) -> list[str]:
    """
    Find graph nodes matching an entity name.
    First tries full name match, then falls back to checking
    if either string contains the other (handles 'Pro Pricing Plan' → 'Pro Plan')
    """

    matches = []
    normalized_query = _normalize_name(entity_name).lower()

    for node, data in graph.nodes(data=True):
        normalized_node = node.lower()
        name_score = _similarity(normalized_query, normalized_node)

        # Partial containment fallback:
        # 'pro pricing plan' contains 'pro plan' → still a match
        containment_bonus = 0.0
        query_words = set(normalized_query.split())
        node_words = set(normalized_node.split())
        shared_words = query_words & node_words

        if len(node_words) > 0:
            word_overlap = len(shared_words) / len(node_words)
            if word_overlap >= 0.8:  # 80% of node words appear in query
                containment_bonus = 0.15

        type_bonus = (
            0.1
            if (
                entity_type
                and data.get("entity_type", "").lower() == entity_type.lower()
            )
            else 0.0
        )

        final_score = name_score + containment_bonus + type_bonus

        if final_score >= threshold:
            matches.append(node)

    return matches


def get_neighboring_chunks(
    graph: nx.DiGraph,
    node_id: str,
    hops: int = 1,
) -> set[int]:
    """
    Collect chunk_indices from a node and its neighbors up to `hops` away.

    hops=1 means: the node itself + its direct neighbors
    hops=2 means: the node + neighbors + neighbors of neighbors

    We keep hops low (default 1) to stay focused.
    Higher hops = more chunks but less precision.
    """

    chunk_indices = set()

    # Start with the node itself
    node_data = graph.nodes[node_id]
    for idx in node_data.get("chunk_indices", []):
        chunk_indices.add(idx)

    if hops == 0:
        return chunk_indices

    # Walk outgoing edges (what this entity relates to)
    for neighbor in graph.successors(node_id):
        neighbor_data = graph.nodes[neighbor]
        for idx in neighbor_data.get("chunk_indices", []):
            chunk_indices.add(idx)

    # Walk incoming edges (what relates to this entity)
    for neighbor in graph.predecessors(node_id):
        neighbor_data = graph.nodes[neighbor]
        for idx in neighbor_data.get("chunk_indices", []):
            chunk_indices.add(idx)

    return chunk_indices


def retrieve_chunks_from_graph(
    query: str,
    graph: Optional[nx.DiGraph],
    max_chunks: int = 5,
) -> GraphTraversalResult:
    """
    Main entry point for graph retrieval.

    Flow:
    1. Extract entities from query
    2. Fuzzy-match entities to graph nodes
    3. Score chunk indices by node specificity — nodes with fewer chunks
       are more precise, so their indices rank higher. This prevents
       mega-nodes like 'onboarding.md' (33 chunks) from drowning out
       specific nodes like 'Week 3 Goals' (1 chunk).
    4. Return top-ranked indices + traversal metadata for the frontend.
    """
    empty_result: GraphTraversalResult = {"chunk_indices": [], "matched_nodes": []}

    if graph is None:
        return empty_result

    entities = extract_entities_from_query(query)

    if not entities:
        print("  Graph: no entities found in query")
        return empty_result

    print(f"  Graph: found {len(entities)} entities in query")

    # index → accumulated specificity score
    # Indices from small/specific nodes score higher than those from large generic nodes
    index_scores: dict[int, float] = {}
    matched_nodes: list[dict] = []

    direct_match_indices: set[int] = set()
    for entity in entities:
        entity_name = _normalize_name(entity["name"])
        entity_type = entity.get("type", "")
        matching_nodes = find_matching_nodes(graph, entity_name, entity_type)
        for node_id in matching_nodes:
            for idx in graph.nodes[node_id].get("chunk_indices", []):
                direct_match_indices.add(idx)

    # Sort all indices by score
    ranked_indices = sorted(
        index_scores.keys(),
        key=lambda i: index_scores[i],
        reverse=True,
    )

    # Build result: direct matches first (guaranteed), then fill with top-scored
    result_indices: list[int] = []
    seen: set[int] = set()

    for idx in direct_match_indices:
        if idx not in seen:
            result_indices.append(idx)
            seen.add(idx)

    for idx in ranked_indices:
        if len(result_indices) >= max_chunks:
            break
        if idx not in seen:
            result_indices.append(idx)
            seen.add(idx)

    result_indices = result_indices[:max_chunks]

    print(f"  Graph: returning {len(result_indices)} chunk indices → {result_indices}")
    return {"chunk_indices": result_indices, "matched_nodes": matched_nodes}
