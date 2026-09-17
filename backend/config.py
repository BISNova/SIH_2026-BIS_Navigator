"""
Backend settings.
"""

import os

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sih-2026-bis-navigator.vercel.app",
]

# P1's service base URL. Defaults to her documented local address; override
# via env var for any other deployment (e.g. a real staging/production URL).
P1_API_BASE_URL = os.environ.get("P1_API_BASE_URL", "http://127.0.0.1:8001")
