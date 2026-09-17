"""
HTTP client for P1's service (POST /p1/process). P1 is a separately
deployed FastAPI app - this is a real network call in production, not
an in-process Python import.

For testing, `client` can be injected as an httpx.Client constructed
with `app=<her FastAPI app>` (ASGI transport) instead of a real
base_url - this exercises the exact same serialization path over a
real ASGI request/response cycle, without needing an actual socket or
a running subprocess. See tests/test_full_integration.py.
"""

import httpx

from .p1_contract import P1InputPayload, P1OutputPayload

DEFAULT_TIMEOUT = 30.0


class P1ClientError(Exception):
    pass


def call_p1_api(
    payload: P1InputPayload,
    base_url: str = "http://127.0.0.1:8001",
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> P1OutputPayload:
    """
    Sends P1Input to POST {base_url}/p1/process and returns the parsed
    P1Output. Raises P1ClientError on any network failure or non-2xx
    response, so callers can handle it explicitly rather than letting a
    raw httpx exception propagate to the frontend.
    """
    owns_client = client is None
    if owns_client:
        client = httpx.Client(base_url=base_url, timeout=timeout)

    try:
        response = client.post("/p1/process", json=payload.model_dump())
    except httpx.RequestError as exc:
        raise P1ClientError(
            f"Could not reach P1 service at {base_url}: {exc}"
        ) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code != 200:
        raise P1ClientError(
            f"P1 service returned HTTP {response.status_code}: {response.text[:300]}"
        )

    return P1OutputPayload(**response.json())


def check_p1_health(base_url: str = "http://127.0.0.1:8001", timeout: float = 5.0) -> bool:
    try:
        with httpx.Client(base_url=base_url, timeout=timeout) as client:
            response = client.get("/health")
            return response.status_code == 200
    except httpx.RequestError:
        return False
