"""
The complete request lifecycle: run Product Intelligence first; if it's
not confident, short-circuit with a clarification/not-found response
and skip the network call to P1 entirely; only call P1's HTTP API once
a product is confidently matched.

Note: P1's own service (rag/service/p1_service.py) ALSO safely handles
clarification_needed/not_found internally, so sending her an
unconfident result wouldn't actually break anything - the short-circuit
here is purely to avoid a wasted network round-trip, not a correctness
requirement.
"""

import sys
from pathlib import Path
from typing import Optional

import httpx

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from product_intelligence.src.pipeline import ProductIntelligencePipeline  # noqa: E402

from .adapter import adapt_to_p1_input
from .p1_client import call_p1_api, P1ClientError
from .p1_contract import P1OutputPayload


def _short_circuit_output(p1_input) -> P1OutputPayload:
    if p1_input.needs_clarification:
        return P1OutputPayload(
            answer="",
            evidence=[],
            sources=[],
            confidence_score=p1_input.confidence_score,
            confidence_label=p1_input.confidence_label,
            evidence_sufficient=False,
            clarification_needed=True,
            clarification_question=p1_input.clarification_question,
        )
    # status == "not_found"
    return P1OutputPayload(
        answer="We don't have this product in our curated knowledge base yet.",
        evidence=[],
        sources=[],
        confidence_score=0.0,
        confidence_label="low",
        evidence_sufficient=False,
        clarification_needed=False,
    )


def run_full_pipeline_with_context(
    query: str,
    product_pipeline: ProductIntelligencePipeline,
    p1_base_url: str = "http://127.0.0.1:8001",
    p1_http_client: Optional[httpx.Client] = None,
) -> dict:
    """
    Returns {"p2_result": ProductMatchResult, "p1_output": P1OutputPayload}.

    p1_http_client can be injected for testing (an httpx.Client built
    with app=<her FastAPI app> for ASGI-transport testing, no real
    network needed) - production code leaves it as None and a real
    client is created against p1_base_url.
    """
    p2_result = product_pipeline.process(query)
    p1_input = adapt_to_p1_input(p2_result)

    if p1_input.needs_clarification or p1_input.status == "not_found":
        return {"p2_result": p2_result, "p1_output": _short_circuit_output(p1_input)}

    # status == "matched" - safe to call P1 now
    try:
        p1_output = call_p1_api(p1_input, base_url=p1_base_url, client=p1_http_client)
    except P1ClientError as exc:
        p1_output = P1OutputPayload(
            answer=f"Sorry, I couldn't reach the evidence service right now ({exc}).",
            evidence=[],
            sources=[],
            confidence_score=0.0,
            confidence_label="low",
            evidence_sufficient=False,
            clarification_needed=False,
        )

    return {"p2_result": p2_result, "p1_output": p1_output}
