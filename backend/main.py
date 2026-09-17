"""
BISNova backend (Product Intelligence / "P2 API").

P1 (Evidence/RAG) is now a SEPARATE service - this backend calls it
over HTTP (see integration/p1_client.py), it does not import P1's code
in-process. Both services need to be running for /api/chat to return a
real grounded answer:

    Terminal 1 (P1):  cd p1_service && uvicorn api.server:app --port 8001
    Terminal 2 (P2):  uvicorn backend.main:app --reload --port 8000

See the root README.md for full setup instructions, including the
sandbox-only mocked P1 variant if you don't have a Gemini API key /
internet access yet.

The frontend (Vite dev server, localhost:5173) is already whitelisted
in CORS - see config.py.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .dependencies import get_product_pipeline
from . import routers_chat, routers_debug, routers_catalog, routers_feedback, routers_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build Product Intelligence once at startup, not on the first
    # request - the first real user shouldn't pay the KB-loading cost.
    get_product_pipeline()
    yield


app = FastAPI(title="BISNova API (P2)", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers_chat.router, prefix="/api")
app.include_router(routers_debug.router, prefix="/api")
app.include_router(routers_catalog.router, prefix="/api")
app.include_router(routers_feedback.router, prefix="/api")
app.include_router(routers_admin.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "BISNova API (P2)", "status": "running", "docs": "/docs"}
