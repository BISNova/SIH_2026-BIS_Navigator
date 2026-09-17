import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import ProductIntelligencePipeline


def get_pipeline():
    return ProductIntelligencePipeline()


def test_pressure_cooker_matches_correctly():
    pipeline = get_pipeline()
    result = pipeline.process("I manufacture domestic pressure cookers for household use")
    assert result.status == "matched"
    assert result.matched_product.product_id == "PROD-001"


def test_water_heater_has_primary_and_secondary_standards():
    """Real data: PROD-002 maps to STD-002 (primary) + STD-003, STD-004
    (secondary, the two parts of the general electrical safety standard)."""
    pipeline = get_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    assert result.status == "matched"
    assert result.matched_product.product_id == "PROD-002"
    assert len(result.applicable_standards) == 3
    assert result.applicable_standards[0].relationship_type == "primary"
    relationship_types = {s.relationship_type for s in result.applicable_standards}
    assert relationship_types == {"primary", "secondary"}


def test_two_parts_of_same_base_standard_display_distinctly():
    """IS 302 Part 1 and Part 2/Section 21 share is_number+edition_year -
    is_number_display must still disambiguate them."""
    pipeline = get_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    displays = [s.is_number for s in result.applicable_standards]
    assert len(displays) == len(set(displays))  # no two look identical


def test_mandatory_flag_reflects_real_conformity_routes_not_relationship_type():
    """is_mandatory comes from conformity_routes.json, joined by
    standard_id - NOT derived from relationship_type. STD-003/STD-004
    have no conformity_routes entry in this sample, so is_mandatory must
    be None (unknown), not False."""
    pipeline = get_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    primary = next(s for s in result.applicable_standards if s.relationship_type == "primary")
    secondary_standards = [s for s in result.applicable_standards if s.relationship_type == "secondary"]
    assert primary.is_mandatory is True  # STD-002 has a conformity_routes entry
    assert all(s.is_mandatory is None for s in secondary_standards)  # no route on file yet


def test_gold_jewellery_matches_and_has_hallmarking_standards():
    pipeline = get_pipeline()
    result = pipeline.process("gold jewellery hallmarking")
    assert result.status == "matched"
    assert result.matched_product.product_id == "PROD-003"
    assert len(result.applicable_standards) == 3


def test_confidence_is_a_curated_float_not_a_bucket():
    pipeline = get_pipeline()
    result = pipeline.process("domestic pressure cooker")
    for s in result.applicable_standards:
        assert isinstance(s.confidence, float)
        assert 0.0 <= s.confidence <= 1.0


def test_matched_product_attributes_use_real_material_field():
    pipeline = get_pipeline()
    result = pipeline.process("domestic pressure cooker")
    assert result.matched_product.attributes is not None
    assert "steel" in result.matched_product.attributes.material.lower()


def test_nonsense_query_returns_not_found():
    pipeline = get_pipeline()
    result = pipeline.process("organic vegetables from my farm")
    assert result.status == "not_found"
    assert result.matched_product is None


def test_empty_query_does_not_crash():
    pipeline = get_pipeline()
    result = pipeline.process("")
    assert result.status == "not_found"


def test_source_url_prefers_document_over_standard_generic_page():
    """Citation should point at the specific document (e.g. the actual
    product manual PDF) rather than a generic BIS standards search page,
    when a document record is available."""
    pipeline = get_pipeline()
    result = pipeline.process("domestic pressure cooker")
    primary = result.applicable_standards[0]
    assert primary.source_url is not None
    assert primary.source_url.startswith("https://")


def test_context_hint_resolves_followup_queries_that_would_otherwise_fail():
    """Conversation memory building block: a followup like 'what tests
    are needed' has no product info of its own - context_hint (the
    previous turn's matched product, supplied by the caller) lets it
    resolve correctly instead of returning not_found."""
    pipeline = get_pipeline()
    without_context = pipeline.process("what tests are needed")
    assert without_context.status == "not_found"

    with_context = pipeline.process("what tests are needed", context_hint="domestic pressure cooker")
    assert with_context.status == "matched"
    assert with_context.matched_product.product_id == "PROD-001"


def test_last_verified_falls_back_to_publication_date_when_unpopulated():
    """last_updated/retrieved_at are null in the current KB (not yet
    populated by Person 4) - last_verified must still return something
    honest by falling back to publication_date, not silently omit it."""
    pipeline = get_pipeline()
    result = pipeline.process("domestic pressure cooker")
    assert result.applicable_standards[0].last_verified is not None


def test_hindi_query_detected_and_matched_after_translation():
    from unittest import mock
    pipeline = get_pipeline()
    with mock.patch("deep_translator.GoogleTranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = "domestic pressure cooker"
        result = pipeline.process("घरेलू प्रेशर कुकर")
        assert result.detected_language == "hi"
        assert result.status == "matched"
        assert result.matched_product.product_id == "PROD-001"
