from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[UUID] = None


class StandardOut(BaseModel):
    standard_id: str
    is_number: str
    title: str
    status: str
    relationship_type: Optional[str] = None
    is_mandatory: Optional[bool] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None
    last_verified: Optional[str] = None


class ClarificationOptionOut(BaseModel):
    label: str
    query: str


class EvidenceOut(BaseModel):
    chunk_id: str
    standard_id: str
    text: str
    section_header: Optional[str] = None
    source_url: Optional[str] = None


class ChatResponse(BaseModel):
    status: str
    answer: str

    matched_product_name: Optional[str] = None

    standards: List[StandardOut] = Field(default_factory=list)

    confidence_score: float = 0.0
    confidence_label: str = "low"

    evidence_sufficient: bool = False

    evidence: List[EvidenceOut] = Field(default_factory=list)

    sources: List[str] = Field(default_factory=list)

    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    clarification_options: List[ClarificationOptionOut] = Field(
        default_factory=list
    )

    detected_language: str = "en"

    from_cache: bool = False

    disclaimer: str = (
        "Informational guidance only - not a substitute for official BIS "
        "certification advice. Always confirm with BIS or a licensed "
        "consultant before making compliance decisions."
    )


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: str
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
    standard_id: str
    is_number: str
    title: str
    status: str
    scope_summary: Optional[str] = None
    product_category: Optional[str] = None
    is_mandatory: Optional[bool] = None
    source_url: Optional[str] = None
    ask_query: str


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

class ChecklistCertificationStepOut(BaseModel):
    step_no: int
    title: str
    description: str
    source_document_id: Optional[str] = None


class ChecklistTestOut(BaseModel):
    test_id: str
    standard_id: str
    test_name: str
    test_category: Optional[str] = None
    test_method: Optional[str] = None
    clause_reference: Optional[str] = None
    requirement: Optional[str] = None
    unit: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    sample_requirement: Optional[str] = None
    frequency: Optional[str] = None
    facility_requirement: Optional[str] = None
    source_document_id: Optional[str] = None


class ChecklistResponse(BaseModel):
    product: dict
    standards: list[dict]
    schemes: list[dict] = Field(default_factory=list)
    conformity_routes: list[dict] = Field(default_factory=list)
    certification_steps: list[ChecklistCertificationStepOut]
    tests: list[ChecklistTestOut]
    inspection_requirements: list[dict]


class ChecklistProgressRequest(BaseModel):
    product_id: str
    completed_step_ids: list[str] = Field(default_factory=list)


class ChecklistProgressResponse(BaseModel):
    id: UUID
    user_id: UUID
    product_id: str
    completed_step_ids: list[str]
    updated_at: datetime