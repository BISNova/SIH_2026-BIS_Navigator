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
