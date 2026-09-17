from pathlib import Path
import sys

# from sentence_transformers import SentenceTransformer
from fastembed import TextEmbedding

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

K_VALUES = [1, 3, 5]


# ---------------------------------------------------------
# Ground-truth evaluation queries
# ---------------------------------------------------------
#
# relevant_sections contains the sections we expect to be
# relevant for the query.
#
# These are based on our synthetic BIS documents.
# ---------------------------------------------------------

TEST_CASES = [

    {
        "name": "Inspection requirements — Standard A",
        "query": "What are the inspection requirements?",
        "standard_ids": ["SYN-STD-101"],
        "relevant_sections": {
            "7.1",
            "7.2",
            "7.3",
            "7.4",
        },
    },

    {
        "name": "Testing requirements — Standard A",
        "query": "What are the testing requirements?",
        "standard_ids": ["SYN-STD-101"],
        "relevant_sections": {
            "6.1",
            "6.2",
            "6.3",
            "6.4",
            "6.5",
        },
    },

    {
        "name": "Certification route — Standard B",
        "query": "What is the certification route?",
        "standard_ids": ["SYN-STD-202"],
        "relevant_sections": {
            "9.1",
            "9.2",
            "9.3",
        },
    },

    {
        "name": "General certification documents",
        "query": "What documents are required for certification?",
        "standard_ids": None,
        "relevant_sections": {
            "9.2",
            "10.2",
        },
    },

]


# ---------------------------------------------------------
# Load model
# ---------------------------------------------------------

print("=" * 70)
print("P1 — Retrieval Evaluation")
print("=" * 70)

print("\nLoading embedding model...")

# model = SentenceTransformer(MODEL_NAME)
model = TextEmbedding(model_name=f"sentence-transformers/{MODEL_NAME}")

print(f"Model loaded: {MODEL_NAME}")


# ---------------------------------------------------------
# Retriever
# ---------------------------------------------------------

retriever = EvidenceRetriever()

print(f"ChromaDB records: {retriever.count()}")


# ---------------------------------------------------------
# Query embedding
# ---------------------------------------------------------

def create_query_embedding(query: str):

    embedding = model.encode(
        query,
        normalize_embeddings=True
    )

    return embedding.tolist()


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def recall_at_k(results, relevant_sections, k):

    top_results = results[:k]

    retrieved_sections = {
        result["section"]
        for result in top_results
    }

    if not relevant_sections:
        return 0.0

    hits = retrieved_sections.intersection(
        relevant_sections
    )

    return len(hits) / len(relevant_sections)


def precision_at_k(results, relevant_sections, k):

    top_results = results[:k]

    if not top_results:
        return 0.0

    relevant_count = 0

    for result in top_results:

        if result["section"] in relevant_sections:
            relevant_count += 1

    return relevant_count / len(top_results)


def reciprocal_rank(results, relevant_sections):

    for rank, result in enumerate(results, start=1):

        if result["section"] in relevant_sections:
            return 1 / rank

    return 0.0


# ---------------------------------------------------------
# Evaluate one test case
# ---------------------------------------------------------

def evaluate_case(test_case):

    query = test_case["query"]

    standard_ids = test_case["standard_ids"]

    relevant_sections = test_case["relevant_sections"]

    query_embedding = create_query_embedding(query)

    results = retriever.retrieve(
        query_embedding=query_embedding,
        top_k=5,
        standard_ids=standard_ids,
    )

    print("\n" + "-" * 70)

    print(f"TEST: {test_case['name']}")

    print(f"Query: {query}")

    if standard_ids:
        print(
            "Standard filter:",
            ", ".join(standard_ids)
        )
    else:
        print("Standard filter: None")

    print(
        "Expected relevant sections:",
        ", ".join(sorted(relevant_sections))
    )

    print("\nRetrieved:")

    for rank, result in enumerate(results, start=1):

        is_relevant = (
            result["section"]
            in relevant_sections
        )

        marker = "✓" if is_relevant else "✗"

        print(
            f"{rank}. "
            f"{marker} "
            f"{result['section']} "
            f"| "
            f"{result['standard_id']} "
            f"| "
            f"similarity={result['similarity_score']:.4f}"
        )

    print("\nMetrics:")

    metrics = {}

    for k in K_VALUES:

        recall = recall_at_k(
            results,
            relevant_sections,
            k
        )

        precision = precision_at_k(
            results,
            relevant_sections,
            k
        )

        metrics[f"recall@{k}"] = recall
        metrics[f"precision@{k}"] = precision

        print(
            f"Recall@{k}:    {recall:.4f}"
        )

        print(
            f"Precision@{k}: {precision:.4f}"
        )

    mrr = reciprocal_rank(
        results,
        relevant_sections
    )

    metrics["mrr"] = mrr

    print(f"MRR:           {mrr:.4f}")

    return metrics


# ---------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------

all_metrics = []

for test_case in TEST_CASES:

    metrics = evaluate_case(test_case)

    all_metrics.append(metrics)


# ---------------------------------------------------------
# Overall averages
# ---------------------------------------------------------

print("\n\n")
print("=" * 70)
print("OVERALL RETRIEVAL RESULTS")
print("=" * 70)

for k in K_VALUES:

    recall_values = [
        metrics[f"recall@{k}"]
        for metrics in all_metrics
    ]

    precision_values = [
        metrics[f"precision@{k}"]
        for metrics in all_metrics
    ]

    average_recall = (
        sum(recall_values)
        / len(recall_values)
    )

    average_precision = (
        sum(precision_values)
        / len(precision_values)
    )

    print(
        f"\nRecall@{k}:    "
        f"{average_recall:.4f}"
    )

    print(
        f"Precision@{k}: "
        f"{average_precision:.4f}"
    )


mrr_values = [
    metrics["mrr"]
    for metrics in all_metrics
]

average_mrr = (
    sum(mrr_values)
    / len(mrr_values)
)

print(
    f"\nMRR:           "
    f"{average_mrr:.4f}"
)


# ---------------------------------------------------------
# Finished
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RETRIEVAL EVALUATION COMPLETE")
print("=" * 70)