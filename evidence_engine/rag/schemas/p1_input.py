from typing import List, Optional
from pydantic import BaseModel, Field


class ApplicableStandard(BaseModel):
    standard_id: str
    standard_title: str
    relevance: Optional[str] = None
    mandatory: bool = False


class P1Input(BaseModel):
    query: str
    normalized_query: Optional[str] = None

    status: str

    matched_product: Optional[str] = None

    applicable_standards: List[ApplicableStandard] = Field(
        default_factory=list
    )

    confidence_score: float = 0.0
    confidence_label: str = "low"

    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    def get_standard_ids(self) -> List[str]:
        return [
            standard.standard_id
            for standard in self.applicable_standards
        ]
