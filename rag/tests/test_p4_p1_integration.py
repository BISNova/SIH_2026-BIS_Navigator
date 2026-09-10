from rag.knowledge.p1_bridge import P4P1Bridge
from rag.schemas.p1_input import P1Input


def test_p4_output_is_valid_p1_input():
    bridge = P4P1Bridge()

    p1_input = bridge.build_p1_input(
        query="What tests are required for a domestic pressure cooker?",
        product_id="PROD-001",
        normalized_query="tests required for domestic pressure cooker",
        confidence_score=0.91,
        confidence_label="high",
    )

    assert isinstance(p1_input, P1Input)

    assert p1_input.query == (
        "What tests are required for a domestic pressure cooker?"
    )

    assert p1_input.matched_product is not None
    assert p1_input.matched_product.product_id == "PROD-001"
    assert p1_input.matched_product.canonical_name == (
        "Domestic Pressure Cooker"
    )

    assert len(p1_input.applicable_standards) == 1
    assert p1_input.applicable_standards[0].standard_id == "STD-001"


def test_p4_water_heater_produces_valid_p1_input():
    bridge = P4P1Bridge()

    p1_input = bridge.build_p1_input(
        query="What tests are required for a storage electric water heater?",
        product_id="PROD-002",
        normalized_query="tests required for storage electric water heater",
        confidence_score=0.90,
        confidence_label="high",
    )

    assert isinstance(p1_input, P1Input)

    assert p1_input.matched_product is not None
    assert p1_input.matched_product.product_id == "PROD-002"

    standard_ids = {
        standard.standard_id
        for standard in p1_input.applicable_standards
    }

    assert standard_ids == {
        "STD-002",
        "STD-003",
        "STD-004",
    }


def test_p4_clarification_produces_valid_p1_input():
    bridge = P4P1Bridge()

    p1_input = bridge.build_p1_input(
        query="Tell me about this product",
        product_id="PROD-001",
        status="clarification",
        needs_clarification=True,
        clarification_question="Which product are you referring to?",
    )

    assert isinstance(p1_input, P1Input)
    assert p1_input.needs_clarification is True
    assert p1_input.clarification_question == (
        "Which product are you referring to?"
    )