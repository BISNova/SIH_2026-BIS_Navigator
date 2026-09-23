from fastapi import FastAPI
from rag.schemas.p1_input import P1Input
from rag.schemas.p1_output import P1Output
from rag.service.p1_service import P1Service


app = FastAPI(
    title="BIS Navigator - P1 Evidence API",
    version="1.0.0",
)

p1_service = P1Service()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "P1",
    }


@app.post("/p1/process", response_model=P1Output)
def process_p1(p1_input: P1Input) -> P1Output:
    """
    Receive P1Input from P2, run P1, and return P1Output.
    P1 never receives raw user queries directly.

    Previously this had no error handling at all, so any exception
    that wasn't a Gemini 503 (which gemini_service.py already retries)
    - a 429 rate limit, a timeout, anything else anywhere in the
    pipeline - propagated straight up as a raw, unhandled HTTP 500.
    That's what produced "P1 service returned HTTP 500: Internal
    Server Error" for "And what about the marking requirements?" in
    testing. This wraps the call so any unexpected failure degrades to
    a valid, low-confidence P1Output instead of crashing the request -
    P2/the frontend always gets a well-formed response to show the
    user, even when something upstream genuinely broke.
    """
    try:
        return p1_service.run(p1_input)
    except Exception as exc:
        print(f"Unhandled error in P1 pipeline: {exc}")
        return P1Output(
            answer=(
                "The BIS evidence service hit an unexpected error "
                "while processing this question. Please try again "
                "in a moment."
            ),
            evidence=[],
            sources=[],
            confidence_score=0.0,
            confidence_label="low",
            evidence_sufficient=False,
            clarification_needed=False,
        )