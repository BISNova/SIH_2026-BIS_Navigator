from __future__ import annotations

from pathlib import Path
import sys

# from sentence_transformers import SentenceTransformer
from fastembed import TextEmbedding

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from retrieval.retriever import EvidenceRetriever
from retrieval.reranker import EvidenceReranker


# ============================================================
# Configuration
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"

RETRIEVAL_TOP_K = 10
FINAL_TOP_K = 5


# ============================================================
# Ground-truth evaluation cases
# ============================================================

TEST_CASES = [
    {
        "name": "Inspection requirements — STD-A",
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
        "name": "Testing requirements — STD-A",
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
        "name": "Certification route — STD-B",
        "query": "What is the certification procedure?",
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


# ============================================================
# Metrics
# ============================================================

def recall_at_k(
    retrieved_sections: list[str],
    relevant_sections: set[str],
    k: int,
) -> float:

    retrieved = set(retrieved_sections[:k])

    if not relevant_sections:
        return 0.0

    return len(
        retrieved.intersection(relevant_sections)
    ) / len(relevant_sections)


def precision_at_k(
    retrieved_sections: list[str],
    relevant_sections: set[str],
    k: int,
) -> float:

    retrieved = retrieved_sections[:k]

    if not retrieved:
        return 0.0

    relevant_count = sum(
        1
        for section in retrieved
        if section in relevant_sections
    )

    return relevant_count / len(retrieved)


def reciprocal_rank(
    retrieved_sections: list[str],
    relevant_sections: set[str],
) -> float:

    for rank, section in enumerate(
        retrieved_sections,
        start=1
    ):

        if section in relevant_sections:
            return 1.0 / rank

    return 0.0


# ============================================================
# Evaluation helper
# ============================================================

def evaluate_results(
    retrieved_sections: list[str],
    relevant_sections: set[str],
) -> dict:

    return {
        "recall@1": recall_at_k(
            retrieved_sections,
            relevant_sections,
            1,
        ),
        "precision@1": precision_at_k(
            retrieved_sections,
            relevant_sections,
            1,
        ),
        "recall@3": recall_at_k(
            retrieved_sections,
            relevant_sections,
            3,
        ),
        "precision@3": precision_at_k(
            retrieved_sections,
            relevant_sections,
            3,
        ),
        "recall@5": recall_at_k(
            retrieved_sections,
            relevant_sections,
            5,
        ),
        "precision@5": precision_at_k(
            retrieved_sections,
            relevant_sections,
            5,
        ),
        "mrr": reciprocal_rank(
            retrieved_sections,
            relevant_sections,
        ),
    }


# ============================================================
# Main evaluation
# ============================================================

def main():

    print("=" * 70)
    print("P1 — Retrieval + Reranking Evaluation")
    print("=" * 70)

    print("\nLoading embedding model...")

    # model = SentenceTransformer(MODEL_NAME)
    model = TextEmbedding(model_name=f"sentence-transformers/{MODEL_NAME}")

    print("Model loaded.")

    print("\nInitializing retriever...")

    retriever = EvidenceRetriever()

    print(
        f"ChromaDB evidence count: "
        f"{retriever.count()}"
    )

    print("\nInitializing reranker...")

    reranker = EvidenceReranker()

    print("Reranker initialized.")

    all_metrics = []

    # --------------------------------------------------------
    # Run test cases
    # --------------------------------------------------------

    for case_number, case in enumerate(
        TEST_CASES,
        start=1
    ):

        print("\n")
        print("=" * 70)
        print(
            f"TEST {case_number}: "
            f"{case['name']}"
        )
        print("=" * 70)

        query = case["query"]
        standard_ids = case["standard_ids"]
        relevant_sections = case["relevant_sections"]

        print(f"\nQuery: {query}")

        if standard_ids:
            print(
                f"Standard filter: "
                f"{', '.join(standard_ids)}"
            )
        else:
            print("Standard filter: None")

        # ----------------------------------------------------
        # Create query embedding
        # ----------------------------------------------------

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        # ----------------------------------------------------
        # Stage 1 — Semantic retrieval
        # ----------------------------------------------------

        retrieved_candidates = retriever.retrieve(
            query_embedding=query_embedding,
            top_k=RETRIEVAL_TOP_K,
            standard_ids=standard_ids,
        )

        print(
            f"\nSemantic candidates retrieved: "
            f"{len(retrieved_candidates)}"
        )

        # ----------------------------------------------------
        # Stage 2 — Reranking
        # ----------------------------------------------------

        reranked_results = reranker.rerank(
            query=query,
            candidates=retrieved_candidates,
            top_k=FINAL_TOP_K,
            standard_ids=standard_ids,
        )

        print(
            f"Final reranked results: "
            f"{len(reranked_results)}"
        )

        # ----------------------------------------------------
        # Display results
        # ----------------------------------------------------

        print("\nReranked evidence:")

        print("-" * 70)

        retrieved_sections = []

        for rank, result in enumerate(
            reranked_results,
            start=1
        ):

            section = result["section"]

            retrieved_sections.append(section)

            print(
                f"\nRank {rank}"
            )

            print(
                f"Chunk:          "
                f"{result['chunk_id']}"
            )

            print(
                f"Section:        "
                f"{section}"
            )

            print(
                f"Standard:       "
                f"{result['standard_id']}"
            )

            print(
                f"Semantic:       "
                f"{result['similarity_score']:.4f}"
            )

            print(
                f"Keyword:        "
                f"{result['keyword_score']:.4f}"
            )

            print(
                f"Section score:  "
                f"{result['section_score']:.4f}"
            )

    

            print(
                f"Rerank score:   "
                f"{result['rerank_score']:.4f}"
            )

            print(
                f"Relevant:       "
                f"{section in relevant_sections}"
            )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        metrics = evaluate_results(
            retrieved_sections,
            relevant_sections,
        )

        all_metrics.append(metrics)

        print("\nMetrics:")

        print(
            f"Recall@1:     "
            f"{metrics['recall@1']:.4f}"
        )

        print(
            f"Precision@1:  "
            f"{metrics['precision@1']:.4f}"
        )

        print(
            f"Recall@3:     "
            f"{metrics['recall@3']:.4f}"
        )

        print(
            f"Precision@3:  "
            f"{metrics['precision@3']:.4f}"
        )

        print(
            f"Recall@5:     "
            f"{metrics['recall@5']:.4f}"
        )

        print(
            f"Precision@5:  "
            f"{metrics['precision@5']:.4f}"
        )

        print(
            f"MRR:          "
            f"{metrics['mrr']:.4f}"
        )

    # ========================================================
    # Overall metrics
    # ========================================================

    print("\n")
    print("=" * 70)
    print("OVERALL RERANKED RESULTS")
    print("=" * 70)

    metric_names = [
        "recall@1",
        "precision@1",
        "recall@3",
        "precision@3",
        "recall@5",
        "precision@5",
        "mrr",
    ]

    averages = {}

    for metric_name in metric_names:

        average = sum(
            metrics[metric_name]
            for metrics in all_metrics
        ) / len(all_metrics)

        averages[metric_name] = average

        print(
            f"{metric_name:<15}: "
            f"{average:.4f}"
        )

    # ========================================================
    # Important comparison
    # ========================================================

    print("\n")
    print("=" * 70)
    print("CURRENT BASELINE vs RERANKER")
    print("=" * 70)

    print(
        "\nBaseline semantic retrieval:"
    )

    print(
        "Recall@5     = 0.9000"
    )

    print(
        "Precision@5  = 0.6000"
    )

    print(
        "MRR          = 1.0000"
    )

    print(
        "\nReranked retrieval:"
    )

    print(
        f"Recall@5     = "
        f"{averages['recall@5']:.4f}"
    )

    print(
        f"Precision@5  = "
        f"{averages['precision@5']:.4f}"
    )

    print(
        f"MRR          = "
        f"{averages['mrr']:.4f}"
    )

    print("\n")
    print("=" * 70)
    print("Evaluation completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()