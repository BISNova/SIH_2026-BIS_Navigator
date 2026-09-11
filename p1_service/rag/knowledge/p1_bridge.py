from typing import Any, Dict, Optional

from rag.schemas.p1_input import (
    ApplicableStandard,
    MatchedProduct,
    P1Input,
)

from rag.knowledge.adapter import P4KnowledgeAdapter


class P4P1Bridge:
    """
    Converts structured P4 knowledge into P1-compatible objects.

    P4 remains responsible for structured BIS knowledge.
    P1 remains responsible for evidence retrieval and answer generation.
    """

    def __init__(
        self,
        adapter: Optional[P4KnowledgeAdapter] = None,
    ):
        self.adapter = adapter or P4KnowledgeAdapter()

    def build_matched_product(
        self,
        product_id: str,
    ) -> Optional[MatchedProduct]:
        product = self.adapter.get_product(product_id)

        if product is None:
            return None

        attributes = self._build_attributes(product_id)

        return MatchedProduct(
            product_id=product_id,
            canonical_name=(
                product.get("product_name")
                or product.get("canonical_name")
                or product_id
            ),
            attributes=attributes,
        )

    def build_applicable_standards(
        self,
        product_id: str,
    ) -> list[ApplicableStandard]:
        relationships = (
            self.adapter.get_standards_for_product(product_id)
        )

        standards = []

        for relationship in relationships:
            if relationship.get("active") is False:
                continue

            standard = relationship.get("standard") or {}

            standard_id = relationship.get("standard_id")

            if not standard_id:
                continue

            confidence = relationship.get(
                "curated_confidence"
            )

            standards.append(
                ApplicableStandard(
                    standard_id=standard_id,
                    is_number=standard.get("is_number"),
                    title=standard.get("title"),
                    relationship_type=relationship.get(
                        "relationship_type"
                    ),
                    status=standard.get("status"),
                    curated_confidence=(
                        str(confidence)
                        if confidence is not None
                        else None
                    ),
                    source_url=standard.get("source_url"),

                    # Existing compatibility fields
                    standard_title=standard.get("title"),
                    relevance=None,

                    mandatory=self._is_mandatory(
                        product_id,
                        standard_id,
                    ),
                )
            )

        return standards

    def build_p1_input(
        self,
        query: str,
        product_id: Optional[str] = None,
        normalized_query: Optional[str] = None,
        status: str = "matched",
        confidence_score: float = 0.0,
        confidence_label: str = "low",
        needs_clarification: bool = False,
        clarification_question: Optional[str] = None,
    ) -> P1Input:

        matched_product = None
        applicable_standards = []

        if product_id:
            matched_product = self.build_matched_product(
                product_id
            )

            applicable_standards = (
                self.build_applicable_standards(product_id)
            )

        return P1Input(
            query=query,
            normalized_query=normalized_query,
            status=status,
            matched_product=matched_product,
            applicable_standards=applicable_standards,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
        )

    def _build_attributes(
        self,
        product_id: str,
    ) -> Dict[str, Any]:

        records = self.adapter.get_product_attributes(
            product_id
        )

        attributes: Dict[str, Any] = {}

        for record in records:
            name = (
                record.get("attribute_name")
                or record.get("name")
                or record.get("attribute")
            )

            if not name:
                continue

            value = record.get("value")

            if value is None:
                value = record.get("allowed_values")

            attributes[name] = value

        return attributes

    def _is_mandatory(
        self,
        product_id: str,
        standard_id: str,
    ) -> bool:

        routes = self.adapter.get_conformity_routes(
            standard_id
        )

        for route in routes:
            if route.get("mandatory") is True:
                return True

        # Also check product-standard mapping.
        relationships = (
            self.adapter.get_standards_for_product(product_id)
        )

        for relationship in relationships:
            if (
                relationship.get("standard_id") == standard_id
                and relationship.get("mandatory") is True
            ):
                return True

        return False