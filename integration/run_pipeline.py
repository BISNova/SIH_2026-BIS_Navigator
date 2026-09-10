"""
The full request lifecycle, exactly as a real backend would call it.

SANDBOX NOTE: constructs EvidencePipeline under the mock embedder patch,
since this sandbox has no internet access to download the real
all-MiniLM-L6-v2 model. On any machine with normal internet, delete the
`mock.patch(...)` block below and just do `EvidencePipeline()` directly
- nothing else in this file or in orchestrator.py needs to change.

Run:  python3 -m integration.run_pipeline
(requires integration/generate_mock_embeddings_and_index.py to have
been run once first, to populate ChromaDB)
"""

import sys
import json
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ENGINE_RAG = PROJECT_ROOT / "evidence_engine" / "rag"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EVIDENCE_ENGINE_RAG))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mock_embedder import MockSentenceTransformer  # noqa: E402
from product_intelligence.src.pipeline import ProductIntelligencePipeline  # noqa: E402
from integration.orchestrator import run_full_pipeline  # noqa: E402


def build_evidence_pipeline():
    # SANDBOX-ONLY - see module docstring above.
    with mock.patch("pipeline.evidence_pipeline.SentenceTransformer", MockSentenceTransformer):
        from pipeline.evidence_pipeline import EvidencePipeline
        return EvidencePipeline()


def run(query, product_pipeline, evidence_pipeline):
    print(f"\n{'='*70}\nQUERY: {query}\n{'='*70}")
    result = run_full_pipeline(query, product_pipeline, evidence_pipeline)
    print(json.dumps(json.loads(result.model_dump_json()), indent=2)[:1500])


if __name__ == "__main__":
    product_pipeline = ProductIntelligencePipeline()
    evidence_pipeline = build_evidence_pipeline()

    for q in [
        "I manufacture domestic pressure cookers for household use",
        "we make electric geysers for homes",
        "gold jewellery hallmarking",
        "organic vegetables from my farm",
    ]:
        run(q, product_pipeline, evidence_pipeline)
