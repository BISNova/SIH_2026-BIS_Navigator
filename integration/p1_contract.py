"""
Mirrors P1's actual rag/schemas/p1_input.py and p1_output.py exactly,
field-for-field - but defined independently here rather than imported
from her package. This is deliberate: P1 is now a separately deployed
HTTP service (see p1_client.py), not something we import Python code
from. The contract is the JSON shape, not shared class objects.

If she changes her schema, this file needs a matching update - that's
the cost of true service separation, and it's the same tradeoff the
"P2 API" / "P1 API" boxes in the architecture diagram implied.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MatchedProductPayload(BaseModel):
    product_id: str
    canonical_name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ApplicableStandardPayload(BaseModel):
    standard_id: str
    is_number: Optional[str] = None
    title: Optional[str] = None
    relationship_type: Optional[str] = None
    status: Optional[str] = None
    curated_confidence: Optional[str] = None
    source_url: Optional[str] = None

    # Compatibility fields her schema keeps for older P1 code/tests
    standard_title: Optional[str] = None
    relevance: Optional[str] = None
    mandatory: bool = False


class P1InputPayload(BaseModel):
    query: str
    normalized_query: Optional[str] = None
    status: str
    matched_product: Optional[MatchedProductPayload] = None
    applicable_standards: List[ApplicableStandardPayload] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_label: str = "low"
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    language: str = "en"


class EvidenceRecordPayload(BaseModel):
    chunk_id: str
    standard_id: str
    document_id: str
    document_title: str
    document_type: Optional[str] = None
    section: Optional[str] = None
    section_header: Optional[str] = None
    page_number: Optional[int] = None
    text: str
    source_url: Optional[str] = None
    version: Optional[str] = None
    authority_level: Optional[int] = None


class P1OutputPayload(BaseModel):
    answer: str
    evidence: List[EvidenceRecordPayload] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_label: str = "low"
    evidence_sufficient: bool = False
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
