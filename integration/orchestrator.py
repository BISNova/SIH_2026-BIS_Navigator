"""
P2 -> P1 integration orchestrator.

The complete request lifecycle: run Product Intelligence first.
Only genuine ambiguity is short-circuited. A "not_found" result is
still sent to P1 because P1 supports general BIS retrieval.
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


def run_full_pipeline_with_context(
    query: str,
    product_pipeline: ProductIntelligencePipeline,
    p1_base_url: str = "http://127.0.0.1:8001",
    p1_http_client: Optional[httpx.Client] = None,
    context_hint: Optional[str] = None,
) -> dict:
    """
    Returns:
        {
            "p2_result": ProductMatchResult,
            "p1_output": P1OutputPayload,
            "p1_success": bool,
        }

    P2 performs product intelligence first.

    Genuine ambiguity is short-circuited because clarification is needed
    before useful retrieval can happen.

    A "not_found" result is still sent to P1 because P1 supports general
    BIS/Indian Standards retrieval even when no product was matched.
    """

    p2_result = product_pipeline.process(
        query,
        context_hint=context_hint,
    )

    p1_input = adapt_to_p1_input(p2_result)

    # Only genuine ambiguity is short-circuited.
    if p1_input.needs_clarification:
        return {
            "p2_result": p2_result,
            "p1_output": _short_circuit_output(p1_input),
            "p1_success": False,
        }

    # Both "matched" and "not_found" go to P1.
    try:
        p1_output = call_p1_api(
            p1_input,
            base_url=p1_base_url,
            client=p1_http_client,
        )

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

        # P1 failed, therefore this response must NOT be cached.
        return {
            "p2_result": p2_result,
            "p1_output": p1_output,
            "p1_success": False,
        }

    # P1 successfully returned a valid response.
    return {
        "p2_result": p2_result,
        "p1_output": p1_output,
        "p1_success": True,
    }