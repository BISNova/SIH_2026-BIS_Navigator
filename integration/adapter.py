"""
The bridge: Person 2's ProductMatchResult -> P1's exact P1Input JSON
shape (via p1_contract.py's mirrored models).

Field-by-field mapping notes:

- matched_product: our object -> her object. Direct, no more flattening
  to a string - her schema was widened to accept this since the last
  integration round, resolving what used to be an open question.

- applicable_standards: populated in BOTH her "rich" fields (is_number,
  title, relationship_type, status, source_url) AND her older
  "compatibility" fields (standard_title, relevance, mandatory) so
  either code path on her side works regardless of which fields any
  given piece of her code actually reads.

- curated_confidence: her field is a STRING, ours is a raw float
  (0.0-1.0) from the real KB's curated mapping confidence. Bucketed
  here rather than sent as a stringified float, since "high"/"medium"/
  "low" is what her field name implies and is more robust to exact
  threshold changes on either side.

- mandatory: her field is a plain, non-optional bool. Our real data has
  a genuine third state (is_mandatory=None means "no conformity route
  on file yet", not "confirmed not mandatory") - collapsed to False
  here since her schema can't represent the distinction. Flagged in
  INTEGRATION_NOTES.md as a real, still-open question for her.

- language: defaults to "en". Not currently wired to a frontend
  language toggle (none exists yet) - passed through as a parameter so
  it's a one-line change to hook up later.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from product_intelligence.src.schemas import ProductMatchResult  # noqa: E402

from .p1_contract import (
    P1InputPayload,
    MatchedProductPayload,
    ApplicableStandardPayload,
)


def _bucket_confidence(score) -> str | None:
    if score is None:
        return None
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def adapt_to_p1_input(result: ProductMatchResult, language: str = "en") -> P1InputPayload:
    matched_product = None
    if result.matched_product:
        attrs = result.matched_product.attributes
        matched_product = MatchedProductPayload(
            product_id=result.matched_product.product_id,
            canonical_name=result.matched_product.canonical_name,
            attributes={
                "category": result.matched_product.category,
                "subcategory": attrs.subcategory if attrs else None,
                "material": attrs.material if attrs else None,
                "typical_use": attrs.typical_use if attrs else None,
            } if attrs else {"category": result.matched_product.category},
        )

    applicable_standards = [
        ApplicableStandardPayload(
            standard_id=s.standard_id,
            is_number=s.is_number,
            title=s.title,
            relationship_type=s.relationship_type,
            status=s.status,
            curated_confidence=_bucket_confidence(s.confidence),
            source_url=s.source_url,
            # compatibility fields
            standard_title=s.title,
            relevance=s.relationship_type,
            mandatory=bool(s.is_mandatory) if s.is_mandatory is not None else False,
        )
        for s in result.applicable_standards
    ]

    return P1InputPayload(
        query=result.query,
        normalized_query=result.normalized_query,
        status=result.status,
        matched_product=matched_product,
        applicable_standards=applicable_standards,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        needs_clarification=result.needs_clarification,
        clarification_question=result.clarification_question,
        language=language,
    )
