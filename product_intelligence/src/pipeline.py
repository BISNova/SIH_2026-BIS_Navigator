"""
ProductIntelligencePipeline is the ONE object Person 5/Person 1 needs to
import.

    from product_intelligence.src.pipeline import ProductIntelligencePipeline
    pipeline = ProductIntelligencePipeline()
    result = pipeline.process("stainless steel pressure cooker for household use")

`result` is a schemas.ProductMatchResult. Two-stage process, per Person
4's real KB: identify the product first (matcher.py + confidence.py),
then join to product_standard_mapping for every standard actually
mapped to it, further enriched with conformity_routes for the real
"is this legally mandatory" signal.
"""

from typing import List, Optional

from .data_loader import (
    load_products,
    load_standards,
    load_mapping,
    load_documents,
    load_conformity_routes,
    load_clarification_bank,
)
from .matcher import ProductMatcher
from .normalize import normalize
from .confidence import decide
from .clarification import get_clarification
from .language import normalize_query_to_english
from .schemas import (
    ProductMatchResult,
    ProductCandidate,
    ApplicableStandard,
    ProductAttributes,
)
from .config import TOP_K_CANDIDATES


class ProductIntelligencePipeline:
    def __init__(self):
        self.products_df = load_products()
        self.standards_df = load_standards()
        self.mapping_df = load_mapping()
        self.documents_df = load_documents()
        self.conformity_routes_df = load_conformity_routes()
        self.clarification_bank = load_clarification_bank()
        self.matcher = ProductMatcher(self.products_df)

    def reload_data(self):
        """Call after Person 4 updates any KB file, no restart needed."""
        self.products_df = load_products()
        self.standards_df = load_standards()
        self.mapping_df = load_mapping()
        self.documents_df = load_documents()
        self.conformity_routes_df = load_conformity_routes()
        self.clarification_bank = load_clarification_bank()
        self.matcher.reload(self.products_df)

    def _row_to_candidate(self, row_index: int, score: float) -> ProductCandidate:
        row = self.products_df.iloc[row_index]
        return ProductCandidate(
            product_id=row["product_id"],
            canonical_name=row["canonical_name"],
            category=row["category"],
            score=round(float(score), 4),
            attributes=ProductAttributes(
                subcategory=row.get("subcategory") or None,
                material=row.get("material_display") or None,
                typical_use=row.get("typical_use_display") or None,
            ),
        )

    def _is_mandatory(self, standard_id: str) -> Optional[bool]:
        """None means 'no conformity route on file yet', not 'not mandatory'."""
        routes = self.conformity_routes_df
        if routes.empty or "standard_id" not in routes.columns:
            return None
        match = routes[routes["standard_id"] == standard_id]
        if match.empty:
            return None
        return bool(match.iloc[0]["mandatory"])

    def _last_verified(self, document_row) -> Optional[str]:
        """
        'Data as of' date for a standard's evidence, per the judges'
        feedback that the schema already has last_updated/retrieved_at/
        content_hash fields sitting unused. Falls back through the most
        specific-to-least-specific date field available, since the
        current KB has last_updated/retrieved_at as null for every
        document (not yet populated by Person 4) - this fallback chain
        means the UI still shows something honest today, and will
        automatically start showing the more precise date the moment
        those fields get real values, with no code change needed.
        """
        if document_row is None or document_row.empty:
            return None
        for field in ("last_updated", "retrieved_at", "publication_date"):
            value = document_row.get(field)
            if value is not None and str(value) != "nan" and str(value).strip():
                return str(value)
        return None

    def _lookup_standards(self, product_id: str) -> List[ApplicableStandard]:
        rows = self.mapping_df[self.mapping_df["product_id"] == product_id]

        results = []
        for _, map_row in rows.iterrows():
            std_row = self.standards_df[
                self.standards_df["standard_id"] == map_row["standard_id"]
            ]
            if std_row.empty:
                continue  # mapping points to a standard_id not yet in standards.json
            std_row = std_row.iloc[0]

            doc_matches = self.documents_df[
                self.documents_df["document_id"] == map_row["source_document_id"]
            ]
            doc_row = doc_matches.iloc[0] if not doc_matches.empty else None
            source_url = doc_row["source_url"] if doc_row is not None else std_row.get("source_url")

            results.append(ApplicableStandard(
                standard_id=std_row["standard_id"],
                is_number=std_row["is_number_display"],
                title=std_row["title"],
                status=std_row["status"],
                relationship_type=map_row["relationship_type"],
                is_mandatory=self._is_mandatory(std_row["standard_id"]),
                scope_condition=map_row.get("scope_condition"),
                clarification_required=bool(map_row["clarification_required"]),
                source_document_id=map_row["source_document_id"],
                source_url=source_url,
                confidence=map_row.get("confidence"),
                last_verified=self._last_verified(doc_row),
            ))

        # primary standards first - that's what the user needs to see first
        results.sort(key=lambda s: 0 if s.relationship_type == "primary" else 1)
        return results

    def process(self, query: str, context_hint: Optional[str] = None) -> ProductMatchResult:
        """
        context_hint: optional text from a prior turn in the same
        conversation (e.g. the last matched product's name), used ONLY
        as a fallback if the query alone doesn't confidently match
        anything. This is what lets "what tests does it need" resolve
        correctly right after "I make pressure cookers" - see
        backend/session_store.py for where context_hint comes from.
        """
        english_query, detected_language = normalize_query_to_english(query)

        result = self._process_english(english_query, original_query=query)
        result.detected_language = detected_language

        if result.status == "not_found" and context_hint:
            augmented = f"{english_query} {context_hint}".strip()
            augmented_result = self._process_english(augmented, original_query=query)
            if augmented_result.status != "not_found":
                augmented_result.detected_language = detected_language
                return augmented_result

        return result

    def _process_english(self, query: str, original_query: str) -> ProductMatchResult:
        ranked = self.matcher.rank(query)  # [(row_index, score), ...] all rows

        top_candidates: List[ProductCandidate] = [
            self._row_to_candidate(idx, score)
            for idx, score in ranked[:TOP_K_CANDIDATES]
        ]

        top1_score = ranked[0][1]
        top2_score = ranked[1][1] if len(ranked) > 1 else 0.0

        decision = decide(top1_score, top2_score)

        result = ProductMatchResult(
            query=original_query,
            normalized_query=normalize(query),
            status=decision.status,
            product_candidates=top_candidates,
            confidence_score=round(float(top1_score), 4),
            confidence_label=decision.confidence_label,
            needs_clarification=decision.needs_clarification,
        )

        if decision.status == "matched":
            result.matched_product = top_candidates[0]
            result.applicable_standards = self._lookup_standards(top_candidates[0].product_id)

        elif decision.status == "clarification_needed":
            id1 = top_candidates[0].product_id
            id2 = top_candidates[1].product_id
            question, options = get_clarification((id1, id2), self.clarification_bank)
            result.clarification_question = question
            result.clarification_options = options

        # status == "not_found" -> everything stays at defaults (no recommendation)

        return result
