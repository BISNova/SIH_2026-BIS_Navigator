"""
BISNova backend (Product Intelligence / "P2 API").

P1 (Evidence/RAG) is a SEPARATE service. This backend calls it
over HTTP (see integration/p1_client.py); it does not import P1's
code in-process.

Both services need to be running for /api/chat to return a real
grounded answer:

    Terminal 1 (P1):
        cd p1_service
        uvicorn api.server:app --port 8001

    Terminal 2 (P2):
        uvicorn backend.main:app --reload --port 8000

See the root README.md for full setup instructions, including the
sandbox-only mocked P1 variant if you don't have a Gemini API key
or internet access yet.

The frontend (Vite dev server, localhost:5173) is already
whitelisted in CORS - see config.py.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .dependencies import get_product_pipeline
from . import (
    routers_chat,
    routers_chat_history,
    routers_debug,
    routers_catalog,
    routers_feedback,
    routers_admin,
    routers_voice,
    routers_subscriptions,
)
from .auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize Product Intelligence once when P2 starts.

    This avoids making the first real user request pay the
    Product Intelligence / KB loading cost.
    """
    get_product_pipeline()
    yield


app = FastAPI(
    title="BISNova API (P2)",
    version="2.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# -------------------------------------------------------------------
# API routers
# -------------------------------------------------------------------

app.include_router(routers_chat.router, prefix="/api")
app.include_router(routers_debug.router, prefix="/api")
app.include_router(routers_catalog.router, prefix="/api")
app.include_router(routers_feedback.router, prefix="/api")
app.include_router(routers_admin.router, prefix="/api")
app.include_router(routers_voice.router, prefix="/api")
app.include_router(routers_subscriptions.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(
    routers_chat_history.router,
    prefix="/api",
)


@app.get("/")
def root():
    return {
        "service": "BISNova API (P2)",
        "status": "running",
        "docs": "/docs",
    }