"""
The actual bridge: Person 2's ProductMatchResult -> Person 1's
P1Input(Extended). Field mapping follows the pattern in her own
evidence_engine/rag/tests/test_contracts.py exactly.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from product_intelligence.src.schemas import ProductMatchResult  # noqa: E402

from .p1_input_extended import (  # noqa: E402
    P1InputExtended,
    ApplicableStandard,
    ProductDetails,
    ProductAttributesOut,
    FullApplicableStandard,
    ClarificationOptionOut,
    ProductCandidateOut,
)


def adapt_to_p1_input(result: ProductMatchResult) -> P1InputExtended:
    matched_product_details = None
    if result.matched_product:
        attrs = result.matched_product.attributes
        matched_product_details = ProductDetails(
            product_id=result.matched_product.product_id,
            canonical_name=result.matched_product.canonical_name,
            category=result.matched_product.category,
            attributes=ProductAttributesOut(
                subcategory=attrs.subcategory if attrs else None,
                material=attrs.material if attrs else None,
                typical_use=attrs.typical_use if attrs else None,
            ) if attrs else None,
        )

    # Her original, narrower shape.
    # NOTE on `mandatory`: her schema forces this to a plain bool, but our
    # real data has a genuine third state - "we don't have a conformity
    # route on file for this standard yet" (is_mandatory=None). Collapsing
    # None -> False here means her `mandatory=False` can mean EITHER
    # "confirmed not mandatory" OR "unknown" - those are very different
    # things for a compliance assistant to conflate. This is flagged in
    # INTEGRATION_NOTES.md as a real question for her, not silently
    # patched - the full tri-state value is preserved on
    # applicable_standards_full below regardless.
    her_shaped_standards = [
        ApplicableStandard(
            standard_id=s.standard_id,
            standard_title=s.title,
            relevance=s.relationship_type,  # "primary" | "secondary"
            mandatory=bool(s.is_mandatory) if s.is_mandatory is not None else False,
        )
        for s in result.applicable_standards
    ]

    full_standards = [
        FullApplicableStandard(
            standard_id=s.standard_id,
            is_number=s.is_number,
            title=s.title,
            status=s.status,
            relationship_type=s.relationship_type,
            is_mandatory=s.is_mandatory,
            scope_condition=s.scope_condition,
            source_document_id=s.source_document_id,
            source_url=s.source_url,
            confidence=s.confidence,
        )
        for s in result.applicable_standards
    ]

    clarification_options = [
        ClarificationOptionOut(label=opt.label, product_id=opt.product_id)
        for opt in result.clarification_options
    ]

    product_candidates = [
        ProductCandidateOut(
            product_id=c.product_id,
            canonical_name=c.canonical_name,
            category=c.category,
            score=c.score,
        )
        for c in result.product_candidates
    ]

    return P1InputExtended(
        query=result.query,
        normalized_query=result.normalized_query,
        status=result.status,
        matched_product=result.matched_product.canonical_name if result.matched_product else None,
        applicable_standards=her_shaped_standards,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        needs_clarification=result.needs_clarification,
        clarification_question=result.clarification_question,
        matched_product_details=matched_product_details,
        applicable_standards_full=full_standards,
        clarification_options=clarification_options,
        product_candidates=product_candidates,
    )
