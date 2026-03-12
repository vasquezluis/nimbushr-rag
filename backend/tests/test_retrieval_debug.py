"""
Diagnostic test: "which are our goals at week 3?"

Runs each retrieval layer independently so you can see exactly
what each one returns and why the final answer might be wrong.

Usage (from backend/):
    uv run python tests/test_retrieval_debug.py
"""

import sys
import json
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.settings import settings
from app.rag.query.vector_store import load_vector_store
from app.rag.graph.knowledge_graph import load_graph
from app.rag.graph.entity_extractor import extract_entities_from_query
from app.rag.graph.graph_retriever import retrieve_chunks_from_graph, find_matching_nodes
from app.rag.graph.hybrid_retriever import hybrid_retrieve, _fetch_chunks_by_indices
from app.rag.graph.knowledge_graph import _normalize_name

QUERY = "according to our onboarding, which are our goals at week 3?"
DIVIDER = "=" * 70


def section(title: str):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


# ── 1. Load resources ─────────────────────────────────────────────────────────
section("LOADING RESOURCES")
db = load_vector_store()
graph = load_graph()
total_docs = db._collection.count()
print(f"  ChromaDB documents : {total_docs}")
print(f"  Graph nodes        : {graph.number_of_nodes() if graph else 'N/A'}")
print(f"  Graph edges        : {graph.number_of_edges() if graph else 'N/A'}")


# ── 2. Inspect what's actually stored for onboarding.md ──────────────────────
section("CHROMADB — onboarding.md chunks")
all_data = db._collection.get(
    where={"source_file": {"$eq": "onboarding.md"}},
    include=["documents", "metadatas"],
)
onboarding_chunks = list(zip(all_data["documents"], all_data["metadatas"]))
print(f"  Total onboarding.md chunks in DB: {len(onboarding_chunks)}\n")

for doc_text, meta in sorted(onboarding_chunks, key=lambda x: x[1].get("chunk_index", 0)):
    idx = meta.get("chunk_index")
    section_title = meta.get("section_title", "?")
    preview = doc_text[:120].replace("\n", " ")
    print(f"  [{idx:>4}] section='{section_title}'")
    print(f"         preview: {preview}")
    # Flag the Week 3 chunk explicitly
    if "week 3" in doc_text.lower() or "week 3" in section_title.lower():
        print(f"         *** THIS IS THE WEEK 3 CHUNK ***")
    print()


# ── 3. Raw vector retrieval (before hybrid) ───────────────────────────────────
section("VECTOR RETRIEVAL — top chunks for query")
if settings.use_mmr:
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.retrieval_k,
            "fetch_k": settings.retrieval_k * 3,
            "lambda_mult": settings.mmr_lambda,
        },
    )
else:
    retriever = db.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": settings.retrieval_k, "score_threshold": 0.5},
    )

vector_chunks = retriever.invoke(QUERY)
vector_indices = {doc.metadata.get("chunk_index") for doc in vector_chunks}
print(f"  Retrieved {len(vector_chunks)} chunks → indices {vector_indices}\n")

for i, chunk in enumerate(vector_chunks, 1):
    meta = chunk.metadata
    idx = meta.get("chunk_index")
    src = meta.get("source_file")
    sec = meta.get("section_title", "?")
    preview = chunk.page_content[:120].replace("\n", " ")
    print(f"  [{i}] idx={idx} | {src} | section='{sec}'")
    print(f"       {preview}")
    print()


# ── 4. Direct similarity search (no MMR) — shows what's semantically closest ─
section("SIMILARITY SEARCH — top 8 (no MMR, for comparison)")
sim_results = db.similarity_search_with_score(QUERY, k=8)
print(f"  {'IDX':>5}  {'SCORE':>6}  {'FILE':<20}  SECTION")
print(f"  {'-'*5}  {'-'*6}  {'-'*20}  {'-'*30}")
for doc, score in sim_results:
    idx = doc.metadata.get("chunk_index", "?")
    src = doc.metadata.get("source_file", "?")[:20]
    sec = doc.metadata.get("section_title", "?")[:40]
    week3 = " *** WEEK 3 ***" if "week 3" in doc.page_content.lower() else ""
    print(f"  {idx:>5}  {score:>6.4f}  {src:<20}  {sec}{week3}")


# ── 5. Graph entity extraction from query ─────────────────────────────────────
section("GRAPH — entity extraction from query")
entities = extract_entities_from_query(QUERY)
print(f"  Extracted {len(entities)} entities:")
for e in entities:
    print(f"    name='{e['name']}'  type='{e.get('type', '?')}'")


# ── 6. Graph node matching — show scores for each entity ─────────────────────
section("GRAPH — node matching (with scores)")
if graph:
    from difflib import SequenceMatcher

    for entity in entities:
        entity_name = _normalize_name(entity["name"])
        print(f"\n  Query entity: '{entity_name}'")

        # Show top 5 closest nodes by score
        scored = []
        for node, data in graph.nodes(data=True):
            a = entity_name.lower()
            b = node.lower()
            score = SequenceMatcher(None, a, b).ratio()

            query_words = set(a.split())
            node_words = set(b.split())
            shared = query_words & node_words
            containment_bonus = 0.15 if (len(node_words) > 0 and len(shared) / len(node_words) >= 0.8) else 0.0
            type_bonus = 0.1 if (entity.get("type") and data.get("entity_type", "").lower() == entity.get("type", "").lower()) else 0.0
            final = score + containment_bonus + type_bonus
            scored.append((node, final, score, containment_bonus, type_bonus, data.get("entity_type", "?"), data.get("chunk_indices", [])))

        scored.sort(key=lambda x: x[1], reverse=True)
        print(f"  {'NODE':<35} {'FINAL':>6}  {'BASE':>6}  TYPE  CHUNKS")
        print(f"  {'-'*35} {'-'*6}  {'-'*6}  {'-'*15}  ------")
        for node, final, base, cb, tb, etype, cidxs in scored[:8]:
            matched = " ← MATCHED" if final >= 0.75 else ""
            print(f"  {node:<35} {final:>6.3f}  {base:>6.3f}  {etype:<15}  {cidxs}{matched}")
else:
    print("  No graph loaded.")


# ── 7. Graph retrieval result ─────────────────────────────────────────────────
section("GRAPH — full retrieval result")
graph_result = retrieve_chunks_from_graph(QUERY, graph, max_chunks=settings.retrieval_k)
graph_indices = set(graph_result["chunk_indices"])
print(f"  Graph returned indices: {graph_indices}")
print(f"  Matched nodes ({len(graph_result['matched_nodes'])}):")
for node in graph_result["matched_nodes"]:
    print(f"    node='{node['name']}' type='{node['entity_type']}' chunk_indices={node['chunk_indices']}")

# Fetch and preview those chunks
if graph_indices:
    graph_docs = _fetch_chunks_by_indices(db, [int(i) for i in graph_indices])
    print(f"\n  Fetched {len(graph_docs)} docs from graph indices:")
    for doc in graph_docs:
        meta = doc.metadata
        idx = meta.get("chunk_index")
        src = meta.get("source_file")
        sec = meta.get("section_title", "?")
        preview = doc.page_content[:100].replace("\n", " ")
        print(f"    [{idx}] {src} | '{sec}' → {preview}")


# ── 8. Hybrid result ──────────────────────────────────────────────────────────
section("HYBRID — final chunks sent to LLM")
hybrid_result = hybrid_retrieve(QUERY, db, graph)
final_chunks = hybrid_result["chunks"]
print(f"\n  Final {len(final_chunks)} chunk(s):\n")
for i, chunk in enumerate(final_chunks, 1):
    meta = chunk.metadata
    idx = meta.get("chunk_index")
    src = meta.get("source_file")
    sec = meta.get("section_title", "?")
    week3 = " *** WEEK 3 ***" if "week 3" in chunk.page_content.lower() else ""
    print(f"  [{i}] idx={idx} | {src} | section='{sec}'{week3}")
    print(f"       {chunk.page_content[:200].replace(chr(10), ' ')}")
    print()


# ── 9. Summary / diagnosis ────────────────────────────────────────────────────
section("DIAGNOSIS SUMMARY")

week3_chunk = next(
    ((t, m) for t, m in onboarding_chunks if "week 3" in m.get("section_title", "").lower()),
    None,
)
week3_in_db = week3_chunk is not None
week3_idx = week3_chunk[1].get("chunk_index") if week3_chunk else None
week3_in_similarity = any("week 3" in doc.metadata.get("section_title", "").lower() for doc, _ in sim_results)
week3_in_vector = any("week 3" in c.metadata.get("section_title", "").lower() for c in vector_chunks)
week3_in_final = any("week 3" in c.metadata.get("section_title", "").lower() for c in final_chunks)

# Check graph node existence
week3_graph_node = None
if graph:
    for node, data in graph.nodes(data=True):
        if "week 3" in node.lower():
            week3_graph_node = (node, data)
            break

print(f"  Week 3 chunk exists in ChromaDB (idx={week3_idx}) : {'✅' if week3_in_db else '❌'}")
print(f"  Week 3 node exists in graph                       : {'✅ ' + str(week3_graph_node[0]) if week3_graph_node else '❌ (section title not injected or index collision)'}")
print(f"  Week 3 in similarity search top 8                 : {'✅' if week3_in_similarity else '❌ (embedding score too low — chunk lacks context)'}")
print(f"  Week 3 in MMR/vector top {settings.retrieval_k}                    : {'✅' if week3_in_vector else '❌ (not retrieved)'}")
print(f"  Week 3 in final hybrid chunks                     : {'✅' if week3_in_final else '❌ (scoring excluded it)'}")

if not week3_in_db:
    print("\n  ⚠️  Re-run ingestion — chunk missing from ChromaDB")
elif not week3_graph_node:
    print("\n  ⚠️  Re-run ingestion — section title not making it into the graph (likely chunk_index collision)")
elif not week3_in_similarity:
    print("\n  ⚠️  Embedding issue — apply the section-title prefix fix to text_processor.py then re-ingest")
elif not week3_in_vector:
    print("\n  ⚠️  MMR diversity is suppressing it — increase retrieval_k or lower mmr_lambda")
elif not week3_in_final:
    print("\n  ⚠️  Hybrid scoring excluded it — check top_k_chunks and scoring logic")
else:
    print("\n  ✅  Week 3 chunk is in the final context")
