"""
Full end-to-end demo, exactly as the backend calls it.

Requires P1's service to actually be running (real: `uvicorn api.server:app
--port 8001` from p1_service/, with a real .env GEMINI_API_KEY and real
internet for the embedding model; sandbox: `uvicorn
sandbox_mocks.run_mocked_server:app --port 8001` from p1_service/).

Run:  python3 -m integration.run_pipeline
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from product_intelligence.src.pipeline import ProductIntelligencePipeline
from integration.orchestrator import run_full_pipeline_with_context
from integration.p1_client import check_p1_health


def run(query, product_pipeline, p1_base_url):
    print(f"\n{'='*70}\nQUERY: {query}\n{'='*70}")
    result = run_full_pipeline_with_context(query, product_pipeline, p1_base_url=p1_base_url)
    p2 = result["p2_result"]
    p1 = result["p1_output"]
    print(f"[P2] status={p2.status} confidence={p2.confidence_label}")
    print(f"[P1] answer: {p1.answer[:300]}")
    print(f"[P1] evidence_sufficient={p1.evidence_sufficient} sources={p1.sources}")


if __name__ == "__main__":
    P1_BASE_URL = "http://127.0.0.1:8001"

    if not check_p1_health(P1_BASE_URL):
        print(f"P1 service is not reachable at {P1_BASE_URL}.")
        print("Start it first - see p1_service/README.md or the root README.md.")
        sys.exit(1)

    product_pipeline = ProductIntelligencePipeline()

    for q in [
        "I manufacture domestic pressure cookers for household use",
        "we make electric geysers for homes",
        "gold jewellery hallmarking",
        "organic vegetables from my farm",
    ]:
        run(q, product_pipeline, P1_BASE_URL)
