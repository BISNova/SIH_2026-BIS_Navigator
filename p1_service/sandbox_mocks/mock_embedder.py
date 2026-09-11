"""
SANDBOX-ONLY MOCK. This exists purely because this development sandbox
has no network access to huggingface.co, so the real
sentence-transformers model (all-MiniLM-L6-v2) cannot be downloaded
here. On any machine with normal internet access, none of this file is
needed - her real EvidencePipeline/embed.py work as-is.

What this mock does NOT do: understand meaning. It produces a
deterministic 384-dim vector from a hash of the text, so identical
text always gets the identical vector (needed for indexing/retrieval
to behave consistently), but two semantically similar sentences with
different words will NOT score as similar the way the real model would.

This is good enough to prove the WIRING works end-to-end (chunks index
correctly, retrieval returns results, reranking/selection/confidence/
answer/citation code all run for real against real data shapes) - it
is NOT good enough to judge actual answer quality. Regenerate real
embeddings with the real model before trusting any answer content.
"""

import hashlib
import numpy as np


class MockSentenceTransformer:
    """Same .encode() call signature as sentence_transformers.SentenceTransformer,
    so it can be swapped in via monkeypatch without touching her code."""

    def __init__(self, model_name: str = "mock"):
        self.model_name = model_name

    def _embed_one(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat the 32-byte digest to fill 384 dims, then map to floats
        raw = np.frombuffer((digest * 12)[:384], dtype=np.uint8).astype(np.float32)
        vec = raw / np.linalg.norm(raw)
        return vec

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        if isinstance(texts, str):
            return self._embed_one(texts)
        return np.array([self._embed_one(t) for t in texts])
