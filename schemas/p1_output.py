from typing import List, Optional
from pydantic import BaseModel

from schemas.evidence import EvidenceRecord


class P1Output(BaseModel):
    answer: str

    evidence: List[EvidenceRecord] = []
    sources: List[str] = []

    confidence_score: float = 0.0
    confidence_label: str = "low"

    evidence_sufficient: bool = False

    clarification_needed: bool = False
    clarification_question: Optional[str] = None