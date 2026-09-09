from pathlib import Path
import sys

from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# Project path
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from retrieval.retriever import EvidenceRetriever


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MODEL_NAME = "all-MiniLM-L6-v2"

TOP_K = 5


# ---------------------------------------------------------
# Load embedding model
# ---------------------------------------------------------

print("=" * 70)
print("P1 — Semantic Retrieval Test")
print("=" * 70)

print("\nLoading embedding model...")

model = SentenceTransformer(MODEL_NAME)

print(f"Model loaded: {MODEL_NAME}")


# ---------------------------------------------------------
# Initialize retriever
# ---------------------------------------------------------

retriever = EvidenceRetriever()

print(f"ChromaDB records: {retriever.count()}")


# ---------------------------------------------------------
# Query embedding helper
# ---------------------------------------------------------

def create_query_embedding(query: str):
    """
    Convert a user query into the same 384-dimensional
    embedding space used for our document chunks.
    """

    embedding = model.encode(
        query,
        normalize_embeddings=True
    )

    return embedding.tolist()


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------

def display_results(
    query: str,
    results: list[dict],
    standard_ids: list[str] | None = None,
):
    print("\n" + "-" * 70)

    print(f"QUERY:")
    print(query)

    if standard_ids:
        print(f"STANDARD FILTER:")
        print(", ".join(standard_ids))
    else:
        print("STANDARD FILTER:")
        print("None — general retrieval")

    print("-" * 70)

    if not results:
        print("No results returned.")
        return

    for index, result in enumerate(results, start=1):

        print(f"\nRESULT #{index}")

        print(f"Chunk ID       : {result['chunk_id']}")
        print(f"Standard ID    : {result['standard_id']}")
        print(f"Document ID    : {result['document_id']}")
        print(f"Section        : {result['section']}")
        print(f"Section Header : {result['section_header']}")
        print(f"Page           : {result['page_number']}")
        print(f"Similarity     : {result['similarity_score']:.4f}")
        print(f"Authority      : {result['authority_level']}")

        print("Evidence:")
        print(result["text"])


# ---------------------------------------------------------
# Run one retrieval test
# ---------------------------------------------------------

def run_test(
    query: str,
    standard_ids: list[str] | None = None,
    top_k: int = TOP_K,
):

    query_embedding = create_query_embedding(query)

    results = retriever.retrieve(
        query_embedding=query_embedding,
        top_k=top_k,
        standard_ids=standard_ids,
    )

    display_results(
        query=query,
        results=results,
        standard_ids=standard_ids,
    )

    return results


# =========================================================
# TEST 1 — Single Standard
# =========================================================

print("\n\n")
print("=" * 70)
print("TEST 1 — SINGLE STANDARD")
print("=" * 70)

run_test(
    query="What are the inspection requirements?",
    standard_ids=["SYN-STD-101"],
    top_k=5,
)


# =========================================================
# TEST 2 — Multiple Standards
# =========================================================

print("\n\n")
print("=" * 70)
print("TEST 2 — MULTIPLE STANDARDS")
print("=" * 70)

run_test(
    query="What are the testing requirements?",
    standard_ids=[
        "SYN-STD-101",
        "SYN-STD-202",
    ],
    top_k=5,
)


# =========================================================
# TEST 3 — General Question
# =========================================================

print("\n\n")
print("=" * 70)
print("TEST 3 — GENERAL QUESTION")
print("=" * 70)

run_test(
    query="What documents are required for certification?",
    standard_ids=None,
    top_k=5,
)


# =========================================================
# TEST 4 — Unknown / Weak Query
# =========================================================

print("\n\n")
print("=" * 70)
print("TEST 4 — UNKNOWN QUERY")
print("=" * 70)

run_test(
    query="What is the procedure for something completely unrelated?",
    standard_ids=None,
    top_k=5,
)


# =========================================================
# Finished
# =========================================================

print("\n\n")
print("=" * 70)
print("RETRIEVAL TESTING COMPLETE")
print("=" * 70)