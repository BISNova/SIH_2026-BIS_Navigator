from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MatchedProduct(BaseModel):
    product_id: str
    canonical_name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ApplicableStandard(BaseModel):
    standard_id: str
    is_number: Optional[str] = None
    title: Optional[str] = None
    relationship_type: Optional[str] = None
    status: Optional[str] = None
    curated_confidence: Optional[str] = None
    source_url: Optional[str] = None

    # Kept for compatibility with existing P1 code/tests
    standard_title: Optional[str] = None
    relevance: Optional[str] = None
    mandatory: bool = False


class P1Input(BaseModel):
    query: str
    normalized_query: Optional[str] = None

    # Every distinct English translation P2's translators produced for
    # this query (language.normalize_query_to_english_variants on the
    # P2 side). normalized_query is always variants[0] when non-empty.
    # Empty for English queries (nothing to vary) - see
    # EvidencePipeline.run()'s query_variants for how P1 uses this.
    normalized_query_variants: List[str] = Field(default_factory=list)

    status: str

    matched_product: Optional[MatchedProduct] = None

    applicable_standards: List[ApplicableStandard] = Field(
        default_factory=list
    )

    confidence_score: float = 0.0
    confidence_label: str = "low"

    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    # Response language requested by the caller.
    # Defaults to English for backward compatibility.
    language: str = "en"

    def get_standard_ids(self) -> List[str]:
        return [
            standard.standard_id
            for standard in self.applicable_standards
        ]