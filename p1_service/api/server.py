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


@app.get("/debug/model")
def debug_model():
    """
    Temporary diagnostic endpoint.
    Tests whether the SentenceTransformer embedding model
    can be loaded successfully on the Render instance.
    """
    try:
        model = p1_service.pipeline._get_model()

        return {
            "status": "ok",
            "model_loaded": True,
            "model_name": p1_service.pipeline.model_name,
            "embedding_dimension": model.get_sentence_embedding_dimension(),
        }

    except Exception as exc:
        return {
            "status": "error",
            "model_loaded": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


@app.post("/p1/process", response_model=P1Output)
def process_p1(p1_input: P1Input) -> P1Output:
    """
    Receive P1Input from P2, run P1, and return P1Output.

    P1 never receives raw user queries directly.
    """
    return p1_service.run(p1_input)