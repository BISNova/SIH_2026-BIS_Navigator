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
    relationship_type: str             # "primary" | "secondary"
    is_mandatory: Optional[bool] = None  # None = no conformity route on file yet, NOT "not mandatory"
    source_url: Optional[str] = None
    confidence: Optional[float] = None


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


class HealthResponse(BaseModel):
    status: str
    products_loaded: int
    standards_loaded: int
    p1_service_reachable: bool
