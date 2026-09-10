"""
P1InputExtended = her exact P1Input (unchanged, still has the two open
questions from before: matched_product is a plain string, and there's
still no clarification_options field) + our richer real-KB fields,
added additively.

Nothing here changes if/when she updates her own schema - this wrapper
either gets thinner (fields move into her real file) or stays as
permanent documentation of what's available beyond her minimum contract.
"""

import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

_EVIDENCE_ENGINE_RAG = Path(__file__).resolve().parent.parent / "evidence_engine" / "rag"
if str(_EVIDENCE_ENGINE_RAG) not in sys.path:
    sys.path.insert(0, str(_EVIDENCE_ENGINE_RAG))

from schemas.p1_input import P1Input, ApplicableStandard  # noqa: E402


class ProductAttributesOut(BaseModel):
    subcategory: Optional[str] = None
    material: Optional[str] = None
    typical_use: Optional[str] = None


class ProductDetails(BaseModel):
    product_id: str
    canonical_name: str
    category: str
    attributes: Optional[ProductAttributesOut] = None


class FullApplicableStandard(BaseModel):
    """Everything her ApplicableStandard has, plus what it can't
    represent: is_mandatory is tri-state here (True/False/None=unknown),
    where her `mandatory: bool` is forced to collapse None -> False (see
    adapter.py's note on this - a real, flagged limitation of her
    current schema, not something silently patched over)."""
    standard_id: str
    is_number: str
    title: str
    status: str
    relationship_type: str  # "primary" | "secondary"
    is_mandatory: Optional[bool] = None
    scope_condition: Optional[str] = None
    source_document_id: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None


class ClarificationOptionOut(BaseModel):
    label: str
    product_id: str


class ProductCandidateOut(BaseModel):
    product_id: str
    canonical_name: str
    category: str
    score: float


class P1InputExtended(P1Input):
    matched_product_details: Optional[ProductDetails] = None
    applicable_standards_full: List[FullApplicableStandard] = []
    clarification_options: List[ClarificationOptionOut] = []
    product_candidates: List[ProductCandidateOut] = []
