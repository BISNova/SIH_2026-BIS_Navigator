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
    """
    return p1_service.run(p1_input)