"""
v3 of the contract - updated to match Person 4's REAL delivered KB data
(not the placeholder schema assumptions from v2).

Two real-data corrections from v2, worth reading before touching anything:

1. relationship_type is "primary" / "secondary" in the real data, NOT
   "mandatory" / "related" as the placeholder assumed. This describes
   how CENTRAL a standard is to the product, not whether certification
   is legally required.

2. "Legally mandatory" is a genuinely separate concept, living on
   conformity_routes (joined by standard_id), not on the product-standard
   mapping at all. A standard can be "primary" to a product without us
   yet knowing if it's mandatory (if no conformity_routes entry exists
   for it) - that's why is_mandatory is Optional[bool], and None means
   "we don't have route data for this yet", not "not mandatory".
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ProductAttributes(BaseModel):
    """Curated attributes of the matched product itself (from Person 4's
    products table) - NOT extracted from the user's specific query text."""
    subcategory: Optional[str] = None
    material: Optional[str] = None
    typical_use: Optional[str] = None


class ProductCandidate(BaseModel):
    """One possible product identification, with its raw similarity score."""
    product_id: str
    canonical_name: str
    category: str
    score: float = Field(..., ge=0.0, le=1.0)
    attributes: Optional[ProductAttributes] = None


class ApplicableStandard(BaseModel):
    """One standard that applies to the identified product."""
    standard_id: str
    is_number: str          # display form, e.g. "IS 2347:2023"
    title: str
    status: str              # "current" | "withdrawn"
    relationship_type: str   # "primary" | "secondary" - centrality, NOT legal mandate
    is_mandatory: Optional[bool] = None  # from conformity_routes; None = unknown, not "no"
    scope_condition: Optional[str] = None
    clarification_required: bool = False
    source_document_id: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None  # Person 4's curated mapping confidence (0-1), NOT a match score
    last_verified: Optional[str] = None  # "data as of" date - see pipeline.py's _last_verified()


class ClarificationOption(BaseModel):
    label: str
    product_id: str


class ProductMatchResult(BaseModel):
    """
    The single object Person 2's pipeline returns for every query.

    status meanings:
      - "matched"              -> matched_product + applicable_standards are
                                   populated, safe to pass to Person 1's RAG
      - "clarification_needed" -> DO NOT call Person 1 yet. Show the
                                   clarification_question/options to the user
                                   and re-run process() with their answer
                                   appended to the query.
      - "not_found"            -> top score didn't clear the absolute floor.
                                   Tell the user honestly instead of guessing.
    """
    query: str
    normalized_query: str
    detected_language: str = "en"  # ISO 639-1 code; "en" if no translation was needed

    status: str  # "matched" | "clarification_needed" | "not_found"

    product_candidates: List[ProductCandidate] = []
    matched_product: Optional[ProductCandidate] = None
    applicable_standards: List[ApplicableStandard] = []

    confidence_score: float = 0.0
    confidence_label: str = "none"  # "high" | "medium" | "low" | "none"

    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[ClarificationOption] = []
