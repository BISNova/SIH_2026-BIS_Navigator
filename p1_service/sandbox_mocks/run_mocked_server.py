"""
SANDBOX-ONLY. Boots P1's real api/server.py with SentenceTransformer and
GeminiService mocked out - for environments with no internet access to
huggingface.co and no GEMINI_API_KEY configured.

On a real machine with internet + a real .env GEMINI_API_KEY, don't use
this file - just run directly from p1_service/:

    uvicorn api.server:app --port 8001

Sandbox usage (from p1_service/):

    python3 -m sandbox_mocks.run_mocked_server
    # or, to actually serve it:
    uvicorn sandbox_mocks.run_mocked_server:app --port 8001
"""

from unittest import mock

from .mock_embedder import MockSentenceTransformer
from .mock_gemini import MockGeminiService

_gemini_patch = mock.patch("rag.answer.gemini_generator.GeminiService", MockGeminiService)
_gemini_patch.start()

_embed_patch = mock.patch("rag.pipeline.evidence_pipeline.SentenceTransformer", MockSentenceTransformer)
_embed_patch.start()

from api.server import app  # noqa: E402
