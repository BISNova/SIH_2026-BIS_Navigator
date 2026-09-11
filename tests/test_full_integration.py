"""
Tests the REAL integration: our adapter builds P1Input, and it's sent
via a real HTTP request/response cycle (ASGI transport, via
httpx.Client(app=...)) to P1's ACTUAL FastAPI app - not a hand-written
stub of what we think her API does. Only her embedding model and Gemini
calls are mocked (no internet/API key in this environment) - everything
else (her real request parsing, P4 evidence building, reranking,
selection, sufficiency checking, confidence scoring, citation building)
runs for real.
"""

import subprocess
import time
import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
P1_SERVICE_ROOT = PROJECT_ROOT / "p1_service"
sys.path.insert(0, str(PROJECT_ROOT))

from product_intelligence.src.pipeline import ProductIntelligencePipeline  # noqa: E402
from integration.adapter import adapt_to_p1_input  # noqa: E402
from integration.orchestrator import run_full_pipeline_with_context  # noqa: E402
from integration.p1_client import call_p1_api, P1ClientError  # noqa: E402

P1_TEST_PORT = 8091
P1_TEST_BASE_URL = f"http://127.0.0.1:{P1_TEST_PORT}"


@pytest.fixture(scope="module")
def p1_live_server():
    """
    Boots P1's REAL FastAPI app (sandbox_mocks.run_mocked_server - only
    the embedding model and Gemini calls are mocked) as an actual live
    subprocess on a real port. This exercises the exact same code path
    production traffic would: a real socket, real HTTP request/response,
    real serialization - not an in-process shortcut.
    """
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "sandbox_mocks.run_mocked_server:app",
            "--port", str(P1_TEST_PORT),
            "--host", "127.0.0.1",
        ],
        cwd=str(P1_SERVICE_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    ready = False
    for _ in range(60):
        try:
            r = httpx.get(f"{P1_TEST_BASE_URL}/health", timeout=1.0)
            if r.status_code == 200:
                ready = True
                break
        except httpx.RequestError:
            pass
        time.sleep(1)

    if not ready:
        output = proc.stdout.read() if proc.stdout else ""
        proc.kill()
        pytest.fail(f"P1 test server never became ready.\n{output}")

    yield P1_TEST_BASE_URL

    # Graceful shutdown (SIGTERM, not SIGKILL) - gives ChromaDB a chance
    # to close its SQLite connection cleanly. A hard kill() here was
    # observed to leave the vectorstore's SQLite file in a state that
    # made the NEXT test module's server hang trying to open it, when
    # both test files were run together in one pytest invocation.
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


@pytest.fixture()
def p1_client(p1_live_server):
    with httpx.Client(base_url=p1_live_server, timeout=30.0) as client:
        yield client


def get_product_pipeline():
    return ProductIntelligencePipeline()


# ---------- Adapter-level tests (no P1 call needed) ----------

def test_adapter_produces_valid_payload_shape():
    pipeline = get_product_pipeline()
    result = pipeline.process("domestic pressure cooker")
    payload = adapt_to_p1_input(result)
    assert payload.matched_product.product_id == "PROD-001"
    assert payload.matched_product.canonical_name == "Domestic Pressure Cooker"


def test_adapter_populates_both_rich_and_compatibility_standard_fields():
    pipeline = get_product_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    payload = adapt_to_p1_input(result)
    for std in payload.applicable_standards:
        # rich fields
        assert std.is_number is not None
        assert std.title is not None
        # compatibility fields, kept in sync with the rich ones
        assert std.standard_title == std.title
        assert std.relevance == std.relationship_type


def test_confidence_bucketed_to_string_for_her_schema():
    pipeline = get_product_pipeline()
    result = pipeline.process("domestic pressure cooker")
    payload = adapt_to_p1_input(result)
    for std in payload.applicable_standards:
        assert std.curated_confidence in {"high", "medium", "low", None}


# ---------- Real HTTP round-trip tests (ASGI transport, her real app) ----------

def test_p1_health_check_via_asgi(p1_client):
    r = p1_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_matched_pressure_cooker_returns_real_grounded_evidence(p1_client):
    pipeline = get_product_pipeline()
    result = pipeline.process("I manufacture domestic pressure cookers for household use")
    payload = adapt_to_p1_input(result)

    p1_output = call_p1_api(payload, client=p1_client)

    assert p1_output.answer
    assert len(p1_output.evidence) > 0
    # Real P4 evidence should be grounded in the actual QCO/standard data,
    # not empty or fabricated
    assert any(e.source_url for e in p1_output.evidence)


def test_gold_jewellery_end_to_end(p1_client):
    pipeline = get_product_pipeline()
    result = pipeline.process("gold jewellery hallmarking")
    payload = adapt_to_p1_input(result)

    p1_output = call_p1_api(payload, client=p1_client)
    assert p1_output.answer
    assert len(p1_output.evidence) > 0


def test_p1_client_raises_clean_error_on_unreachable_host():
    from integration.p1_contract import P1InputPayload
    payload = P1InputPayload(query="test", status="matched")
    with pytest.raises(P1ClientError):
        call_p1_api(payload, base_url="http://127.0.0.1:59999", timeout=1.0)


# ---------- Full orchestrator tests ----------

def test_orchestrator_matched_calls_p1_and_merges_context(p1_client):
    result = run_full_pipeline_with_context(
        "I manufacture domestic pressure cookers for household use",
        get_product_pipeline(),
        p1_http_client=p1_client,
    )
    assert result["p2_result"].status == "matched"
    assert result["p1_output"].answer
    assert len(result["p1_output"].evidence) > 0


def test_orchestrator_not_found_skips_p1_entirely():
    """If Product Intelligence can't confidently match, P1 must never be
    called - verified by passing a client that would raise if used."""
    class ExplodingClient:
        def post(self, *args, **kwargs):
            raise AssertionError("P1 should not be called for a not_found query")

    result = run_full_pipeline_with_context(
        "organic vegetables from my farm",
        get_product_pipeline(),
        p1_http_client=ExplodingClient(),
    )
    assert result["p1_output"].evidence == []
    assert result["p1_output"].clarification_needed is False


def test_orchestrator_clarification_skips_p1_entirely():
    from product_intelligence.src.schemas import ProductMatchResult

    class ForcedClarificationPipeline:
        def process(self, query):
            return ProductMatchResult(
                query=query,
                normalized_query=query,
                status="clarification_needed",
                needs_clarification=True,
                clarification_question="Which product do you mean?",
                confidence_score=0.2,
                confidence_label="low",
            )

    class ExplodingClient:
        def post(self, *args, **kwargs):
            raise AssertionError("P1 should not be called during clarification")

    result = run_full_pipeline_with_context(
        "ambiguous thing",
        ForcedClarificationPipeline(),
        p1_http_client=ExplodingClient(),
    )
    assert result["p1_output"].clarification_needed is True
    assert result["p1_output"].clarification_question == "Which product do you mean?"
