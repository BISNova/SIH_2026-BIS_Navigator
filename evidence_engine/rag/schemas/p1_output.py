
from typing import List, Optional
from pydantic import BaseModel, Field

from schemas.evidence import EvidenceRecord


class P1Output(BaseModel):
    answer: str

    evidence: List[EvidenceRecord] = Field(
        default_factory=list
    )

    sources: List[str] = Field(
        default_factory=list
    )

    confidence_score: float = 0.0
    confidence_label: str = "low"

    evidence_sufficient: bool = False

    clarification_needed: bool = False
    clarification_question: Optional[str] = None
