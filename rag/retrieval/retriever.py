from pathlib import Path
import sys

# Allow importing from the project root when running this file directly.
BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from vectorstore.chroma_store import ChromaEvidenceStore


class EvidenceRetriever:
    """
    P1 retrieval layer.

    This class hides the underlying vector database from
    the rest of the P1 pipeline.
    """

    def __init__(self):
        self.store = ChromaEvidenceStore()

    # -----------------------------------------------------
    # Retrieve evidence
    # -----------------------------------------------------

    def retrieve(
        self,
        query_embedding,
        top_k: int = 5,
        standard_ids: list[str] | None = None,
    ):

        results = self.store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            standard_ids=standard_ids,
        )

        return self._format_results(results)

    # -----------------------------------------------------
    # Format ChromaDB results
    # -----------------------------------------------------

    def _format_results(self, results):

        formatted_results = []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(ids)):

            metadata = metadatas[i]

            # Chroma cosine distance:
            # lower distance = more similar
            distance = distances[i]

            similarity = 1 - distance

            formatted_results.append({
                "chunk_id": ids[i],

                "text": documents[i],

                "similarity_score": similarity,

                "standard_id": metadata.get("standard_id"),

                "document_id": metadata.get("document_id"),

                "section": metadata.get("section"),

                "section_header": metadata.get("section_header"),

                "document_title": metadata.get("document_title"),

                "document_type": metadata.get("document_type"),

                "version": metadata.get("version"),

                "authority_level": metadata.get("authority_level"),

                "source_url": metadata.get("source_url"),

                "page_number": metadata.get("page_number"),
            })

        return formatted_results

    # -----------------------------------------------------
    # Collection information
    # -----------------------------------------------------

    def count(self):
        return self.store.count()


# ---------------------------------------------------------
# Basic test
# ---------------------------------------------------------

if __name__ == "__main__":

    print("=" * 60)
    print("P1 — Evidence Retriever")
    print("=" * 60)

    retriever = EvidenceRetriever()

    print("\nChromaDB evidence count:")
    print(retriever.count())

    print("\nRetriever initialized successfully.")

    print("=" * 60)