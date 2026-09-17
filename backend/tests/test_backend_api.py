"""
Boots P1's real service (sandbox-mocked embedding/Gemini calls) as a
live subprocess, points this backend at it, and tests the real
end-to-end /api/chat flow through actual HTTP calls between the two
services - not a stub of what we assume P1 returns.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
P1_SERVICE_ROOT = PROJECT_ROOT / "p1_service"
sys.path.insert(0, str(PROJECT_ROOT))

P1_TEST_PORT = 8092
P1_TEST_BASE_URL = f"http://127.0.0.1:{P1_TEST_PORT}"


@pytest.fixture(scope="module", autouse=True)
def p1_live_server():
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

    yield

    # Graceful shutdown - see the matching comment in
    # tests/test_full_integration.py for why this matters when running
    # multiple test modules (each with their own P1 subprocess) together.
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


@pytest.fixture(scope="module")
def client(p1_live_server):
    # Must set this BEFORE importing backend.main, since backend/config.py
    # reads the env var at import time.
    os.environ["P1_API_BASE_URL"] = P1_TEST_BASE_URL
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["products_loaded"] == 3
    assert body["standards_loaded"] == 7
    assert body["p1_service_reachable"] is True


def test_chat_matched_product_returns_grounded_answer(client):
    r = client.post("/api/chat", json={"query": "I manufacture domestic pressure cookers for household use"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "matched"
    assert body["matched_product_name"] == "Domestic Pressure Cooker"
    assert len(body["standards"]) >= 1
    assert body["answer"]
    assert len(body["evidence"]) > 0  # real evidence, not a stub


def test_chat_multiple_standards_all_returned_not_just_one(client):
    r = client.post("/api/chat", json={"query": "we make electric geysers for homes"})
    body = r.json()
    assert len(body["standards"]) == 3
    relationship_types = {s["relationship_type"] for s in body["standards"]}
    assert relationship_types == {"primary", "secondary"}


def test_chat_not_found_returns_honest_message_no_standards(client):
    r = client.post("/api/chat", json={"query": "organic vegetables from my farm"})
    body = r.json()
    assert body["status"] == "not_found"
    assert body["standards"] == []
    assert body["evidence"] == []


def test_chat_response_never_crashes_on_empty_query(client):
    r = client.post("/api/chat", json={"query": ""})
    assert r.status_code == 200


def test_debug_match_product_skips_p1(client):
    r = client.post("/api/debug/match-product", json={"query": "gold jewellery"})
    assert r.status_code == 200
    body = r.json()
    assert body["matched_product_name"] == "Gold Jewellery / Gold Articles"
    assert len(body["standards"]) >= 1


def test_clarification_options_carry_ready_to_send_queries(client):
    r = client.post("/api/chat", json={"query": "bottle"})
    body = r.json()
    for opt in body["clarification_options"]:
        assert opt["label"]
        assert opt["query"]


def test_catalog_standards_returns_all_kb_standards(client):
    r = client.get("/api/catalog/standards")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 7
    for std in body:
        assert std["standard_id"]
        assert std["is_number"]
        assert std["ask_query"]  # ready-to-send chat query


def test_catalog_standards_distinguishes_shared_is_numbers(client):
    """IS 302 Part 1 and Part 2/Section 21 share an is_number+year -
    the catalog must still show them as distinct entries."""
    r = client.get("/api/catalog/standards")
    displays = [s["is_number"] for s in r.json()]
    assert len(displays) == len(set(displays))


def test_catalog_labs_returns_real_data_not_placeholders(client):
    r = client.get("/api/catalog/labs")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 15
    for lab in body:
        assert lab["lab_id"]
        assert lab["lab_name"]
        # no fabricated distance/geolocation field should ever appear here
        assert "distance" not in lab


def test_chat_conversation_memory_resolves_followup(client):
    """A follow-up like 'what tests are needed' has no product info of
    its own - it should resolve against the last matched product in the
    same session, but NOT in a different session."""
    session_id = "test-session-memory-1"
    r1 = client.post("/api/chat", json={
        "query": "I manufacture domestic pressure cookers",
        "session_id": session_id,
    })
    assert r1.json()["status"] == "matched"

    r2 = client.post("/api/chat", json={
        "query": "what tests are needed",
        "session_id": session_id,
    })
    assert r2.json()["status"] == "matched"
    assert r2.json()["matched_product_name"] == "Domestic Pressure Cooker"

    # A different session has no memory of the first session's product
    r3 = client.post("/api/chat", json={
        "query": "what tests are needed",
        "session_id": "a-completely-different-session",
    })
    assert r3.json()["status"] == "not_found"


def test_chat_repeat_query_served_from_cache(client):
    r1 = client.post("/api/chat", json={"query": "gold jewellery hallmarking unique cache test"})
    assert r1.json()["from_cache"] is False

    r2 = client.post("/api/chat", json={"query": "gold jewellery hallmarking unique cache test"})
    assert r2.json()["from_cache"] is True
    assert r2.json()["answer"] == r1.json()["answer"]


def test_chat_list_query_short_circuits_to_structured_answer(client):
    r = client.post("/api/chat", json={"query": "list all mandatory standards"})
    body = r.json()
    assert body["status"] == "matched"
    assert body["evidence_sufficient"] is True
    assert len(body["standards"]) > 0
    assert all(s["is_mandatory"] is True for s in body["standards"])


def test_chat_response_disclaimer_present(client):
    r = client.post("/api/chat", json={"query": "domestic pressure cooker"})
    assert "informational guidance" in r.json()["disclaimer"].lower()


def test_hindi_query_end_to_end(client):
    """Real end-to-end proof the language pipeline is wired into the
    actual HTTP endpoint, not just unit-tested in isolation. Translation
    itself is mocked (see product_intelligence/src/language.py for why
    this sandbox can't reach the real translation endpoint), but
    everything else - detection, routing into Product Intelligence,
    the real P1 call - is genuine."""
    from unittest import mock
    with mock.patch("deep_translator.GoogleTranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = "domestic pressure cooker"
        r = client.post("/api/chat", json={"query": "घरेलू प्रेशर कुकर"})
        body = r.json()
        assert body["detected_language"] == "hi"
        assert body["status"] == "matched"


def test_feedback_submission_and_stats(client):
    r = client.post("/api/feedback", json={
        "query": "domestic pressure cooker",
        "answer": "IS 2347 applies",
        "rating": "up",
        "session_id": "test-session",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "recorded"

    stats = client.get("/api/feedback/stats")
    assert stats.json()["total"] >= 1


def test_admin_staged_changes_empty_by_default(client):
    r = client.get("/api/admin/staged-changes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_review_unknown_document_reports_not_found(client):
    r = client.post("/api/admin/review", json={"document_id": "DOES-NOT-EXIST", "approve": True})
    assert r.status_code == 200
    assert r.json()["found"] is False
