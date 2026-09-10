"""
SANDBOX-ONLY test setup. Runs Person 1's REAL embed.py/chroma_store.py
code, with only the SentenceTransformer swapped for the mock (see
mock_embedder.py for why). Everything else here is her actual code,
unmodified.

Run once before running run_pipeline.py in this sandbox:
    python3 -m integration.generate_mock_embeddings_and_index

On a real machine with internet, skip this file entirely and run her
own rag/embeddings/embed.py + rag/vectorstore/chroma_store.py directly.
"""

import sys
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ENGINE_RAG = PROJECT_ROOT / "evidence_engine" / "rag"
INTEGRATION_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVIDENCE_ENGINE_RAG))
sys.path.insert(0, str(INTEGRATION_DIR))

from mock_embedder import MockSentenceTransformer  # noqa: E402


def main():
    import os
    # Her embed.py uses paths relative to CWD ("data/processed"), matching
    # how she runs it herself (from inside evidence_engine/rag/). Match
    # that here rather than editing her file.
    original_cwd = os.getcwd()
    os.chdir(EVIDENCE_ENGINE_RAG)
    try:
        with mock.patch("embeddings.embed.SentenceTransformer", MockSentenceTransformer):
            import embeddings.embed as embed_mod
            embed_mod.main()

        from vectorstore.chroma_store import ChromaEvidenceStore
        store = ChromaEvidenceStore()
        records = store.load_embeddings()
        store.validate_records(records)
        count = store.index_records(records)
        print(f"\nIndexed {count} records into ChromaDB (mock embeddings).")
        print(f"Collection count: {store.count()}")
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
