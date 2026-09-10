"""
This is the module that makes "asks instead of guesses" real.

Two separate checks are used together, not one:

1. ABSOLUTE FLOOR - is the best score even plausible as a real match?
   A relative gap alone is not enough: if a query matches NOTHING well,
   the top-1 and top-2 scores can still be far apart from each other
   (e.g. 0.10 vs 0.02) while both being wrong. The absolute floor catches
   "this product genuinely isn't in our curated categories" and returns
   not_found instead of forcing a clarification among wrong options.

2. RELATIVE GAP - given the top score clears the floor, is it clearly
   ahead of the second-best, or are two categories genuinely competing?
   A small gap here is the actual "ambiguous product description" case
   (e.g. "bottle" -> plastic vs glass) and should trigger clarification.
"""

from dataclasses import dataclass
from typing import Optional
from .config import (
    ABSOLUTE_CONFIDENCE_FLOOR,
    HIGH_CONFIDENCE_THRESHOLD,
    AMBIGUITY_GAP_THRESHOLD,
)


@dataclass
class ConfidenceDecision:
    status: str  # "matched" | "clarification_needed" | "not_found"
    confidence_label: str  # "high" | "medium" | "low" | "none"
    needs_clarification: bool


def decide(top1_score: float, top2_score: Optional[float]) -> ConfidenceDecision:
    top2_score = top2_score or 0.0

    # Check 1: absolute floor
    if top1_score < ABSOLUTE_CONFIDENCE_FLOOR:
        return ConfidenceDecision(
            status="not_found",
            confidence_label="none",
            needs_clarification=False,
        )

    # Check 2: relative gap
    gap = top1_score - top2_score
    if gap < AMBIGUITY_GAP_THRESHOLD:
        return ConfidenceDecision(
            status="clarification_needed",
            confidence_label="low",
            needs_clarification=True,
        )

    # Confident single match - just decide the display label
    label = "high" if top1_score >= HIGH_CONFIDENCE_THRESHOLD else "medium"
    return ConfidenceDecision(
        status="matched",
        confidence_label=label,
        needs_clarification=False,
    )
