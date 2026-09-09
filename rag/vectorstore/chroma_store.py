from pathlib import Path
import json

import chromadb


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

EMBEDDINGS_FILE = BASE_DIR / "data" / "embeddings" / "all_embeddings.json"
CHROMA_DIR = BASE_DIR / "data" / "vectorstore" / "chroma"

COLLECTION_NAME = "bis_evidence"


# ---------------------------------------------------------
# ChromaDB Store
# ---------------------------------------------------------

class ChromaEvidenceStore:

    def __init__(
        self,
        persist_directory: str | Path = CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
    ):
        self.persist_directory = str(persist_directory)

        Path(self.persist_directory).mkdir(
            parents=True,
            exist_ok=True
        )

        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={
                "hnsw": {
                    "space": "cosine"
                }
            }
        )

    # -----------------------------------------------------
    # Load embeddings JSON
    # -----------------------------------------------------

    def load_embeddings(self, path: str | Path = EMBEDDINGS_FILE):
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"Embeddings file not found: {path}"
            )

        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            raise ValueError(
                "Embeddings file must contain a list of records."
            )

        return records

    # -----------------------------------------------------
    # Validate records
    # -----------------------------------------------------

    def validate_records(self, records):
        if not records:
            raise ValueError("No embedding records found.")

        required_fields = {
            "chunk_id",
            "embedding",
            "text",
            "document_id",
            "standard_id",
            "section",
            "section_header",
            "document_title",
            "document_type",
            "version",
            "authority_level",
            "source_url",
            "page_number",
        }

        seen_ids = set()

        for record in records:

            missing = required_fields - record.keys()

            if missing:
                raise ValueError(
                    f"Record {record.get('chunk_id')} "
                    f"is missing fields: {missing}"
                )

            chunk_id = record["chunk_id"]

            if chunk_id in seen_ids:
                raise ValueError(
                    f"Duplicate chunk_id found: {chunk_id}"
                )

            seen_ids.add(chunk_id)

            embedding = record["embedding"]

            if len(embedding) != 384:
                raise ValueError(
                    f"{chunk_id}: expected 384 dimensions, "
                    f"got {len(embedding)}"
                )

            if not record["text"].strip():
                raise ValueError(
                    f"{chunk_id}: empty evidence text."
                )

    # -----------------------------------------------------
    # Convert metadata to Chroma-safe format
    # -----------------------------------------------------

    def build_metadata(self, record):
        return {
            "document_id": str(record["document_id"]),
            "standard_id": str(record["standard_id"]),
            "section": str(record["section"]),
            "section_header": (
                record["section_header"]
                if record["section_header"] is not None
                else ""
            ),
            "document_title": str(record["document_title"]),
            "document_type": str(record["document_type"]),
            "version": str(record["version"]),
            "authority_level": int(record["authority_level"]),
            "source_url": str(record["source_url"]),
            "page_number": int(record["page_number"]),
        }

    # -----------------------------------------------------
    # Index records
    # -----------------------------------------------------

    def index_records(self, records):

        self.validate_records(records)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for record in records:

            ids.append(record["chunk_id"])

            embeddings.append(record["embedding"])

            # Original text is preserved for evidence/citations.
            documents.append(record["text"])

            metadatas.append(
                self.build_metadata(record)
            )

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(records)

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    def search(
        self,
        query_embedding,
        top_k: int = 5,
        standard_ids: list[str] | None = None,
    ):

        where = None

        if standard_ids:

            if len(standard_ids) == 1:
                where = {
                    "standard_id": standard_ids[0]
                }

            else:
                where = {
                    "$or": [
                        {"standard_id": standard_id}
                        for standard_id in standard_ids
                    ]
                }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return results

    # -----------------------------------------------------
    # Collection information
    # -----------------------------------------------------

    def count(self):
        return self.collection.count()


# ---------------------------------------------------------
# Main test / indexing script
# ---------------------------------------------------------

if __name__ == "__main__":

    print("=" * 60)
    print("P1 — ChromaDB Evidence Store")
    print("=" * 60)

    store = ChromaEvidenceStore()

    print("\nLoading embeddings...")
    records = store.load_embeddings()

    print(f"Loaded records: {len(records)}")

    print("\nValidating records...")
    store.validate_records(records)

    print("Validation passed.")

    print("\nIndexing into ChromaDB...")
    count = store.index_records(records)

    print(f"Indexed records: {count}")

    print("\nChromaDB collection count:")
    print(store.count())

    print("\nCollection ready.")
    print("=" * 60)