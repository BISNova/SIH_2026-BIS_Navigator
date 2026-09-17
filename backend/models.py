"""
External API contract. Deliberately its own set of models, separate
from product_intelligence's ProductMatchResult and evidence_engine's
P1Output - the API can stay stable for the frontend even if internal
pipeline shapes change (same "freeze the interface, not the internals"
principle used everywhere else in this project).

This is a superset of what any single frontend component needs right
now - the frontend integration layer picks out what it wants to render
(e.g. today's UI shows one standard card; this API returns all of them,
so nothing is lost if the UI is extended later).
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # accepted but unused for now - see README section on statelessness


class StandardOut(BaseModel):
    standard_id: str
    is_number: str
    title: str
    status: str                        # "current" | "withdrawn"
    relationship_type: Optional[str] = None  # "primary" | "secondary" - None for catalog/list-driven answers with no single product context
    is_mandatory: Optional[bool] = None  # None = no conformity route on file yet, NOT "not mandatory"
    source_url: Optional[str] = None
    confidence: Optional[float] = None
    last_verified: Optional[str] = None  # "data as of" - see product_intelligence/src/pipeline.py


class ClarificationOptionOut(BaseModel):
    label: str
    query: str  # pre-built follow-up query the frontend can send verbatim on click


class EvidenceOut(BaseModel):
    chunk_id: str
    standard_id: str
    text: str
    section_header: Optional[str] = None
    source_url: Optional[str] = None


class ChatResponse(BaseModel):
    status: str  # "matched" | "clarification_needed" | "not_found"

    answer: str

    matched_product_name: Optional[str] = None
    standards: List[StandardOut] = []

    confidence_score: float = 0.0
    confidence_label: str = "low"
    evidence_sufficient: bool = False

    evidence: List[EvidenceOut] = []
    sources: List[str] = []

    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[ClarificationOptionOut] = []

    detected_language: str = "en"       # ISO 639-1; "en" if no translation happened
    from_cache: bool = False             # true if this exact query was served from cache
    disclaimer: str = (
        "Informational guidance only - not a substitute for official BIS "
        "certification advice. Always confirm with BIS or a licensed "
        "consultant before making compliance decisions."
    )


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: str   # "up" | "down"
    session_id: Optional[str] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    total_feedback_count: int


class HealthResponse(BaseModel):
    status: str
    products_loaded: int
    standards_loaded: int
    p1_service_reachable: bool


class CatalogStandardOut(BaseModel):
    """One row in the Explore Standards catalog - broader than
    ChatResponse's StandardOut since there's no single matched product
    to scope it to here (this lists EVERY standard in the KB)."""
    standard_id: str
    is_number: str
    title: str
    status: str                          # "current" | "withdrawn"
    scope_summary: Optional[str] = None
    product_category: Optional[str] = None
    is_mandatory: Optional[bool] = None    # None = no conformity route on file yet
    source_url: Optional[str] = None
    ask_query: str                        # ready-to-send chat query for "ask about this standard"

class CatalogLabOut(BaseModel):
    lab_id: str
    lab_name: str
    lab_type: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source_url: Optional[str] = None
