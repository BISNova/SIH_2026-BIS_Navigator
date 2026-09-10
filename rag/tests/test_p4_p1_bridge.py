from rag.knowledge.p1_bridge import P4P1Bridge


def test_build_matched_product():
    bridge = P4P1Bridge()

    product = bridge.build_matched_product("PROD-001")

    assert product is not None
    assert product.product_id == "PROD-001"
    assert product.canonical_name == "Domestic Pressure Cooker"
    assert isinstance(product.attributes, dict)


def test_build_applicable_standards_for_pressure_cooker():
    bridge = P4P1Bridge()

    standards = bridge.build_applicable_standards("PROD-001")

    assert len(standards) > 0
    assert standards[0].standard_id == "STD-001"
    assert standards[0].is_number == "2347"


def test_build_applicable_standards_for_water_heater():
    bridge = P4P1Bridge()

    standards = bridge.build_applicable_standards("PROD-002")

    standard_ids = {standard.standard_id for standard in standards}

    assert standard_ids == {
        "STD-002",
        "STD-003",
        "STD-004",
    }


def test_primary_secondary_relationships():
    bridge = P4P1Bridge()

    standards = bridge.build_applicable_standards("PROD-002")

    relationships = {
        standard.standard_id: standard.relationship_type
        for standard in standards
    }

    assert relationships["STD-002"] == "primary"
    assert relationships["STD-003"] == "secondary"
    assert relationships["STD-004"] == "secondary"


def test_build_p1_input():
    bridge = P4P1Bridge()

    p1_input = bridge.build_p1_input(
        query="What tests are required for a domestic pressure cooker?",
        product_id="PROD-001",
        normalized_query="tests required for domestic pressure cooker",
        confidence_score=0.91,
        confidence_label="high",
    )

    assert p1_input.query.startswith("What tests")
    assert p1_input.matched_product is not None
    assert p1_input.matched_product.product_id == "PROD-001"

    assert len(p1_input.applicable_standards) == 1
    assert p1_input.applicable_standards[0].standard_id == "STD-001"

    assert p1_input.confidence_score == 0.91
    assert p1_input.confidence_label == "high"


def test_unknown_product():
    bridge = P4P1Bridge()

    product = bridge.build_matched_product("UNKNOWN")

    assert product is None
    assert bridge.build_applicable_standards("UNKNOWN") == []


def test_bridge_handles_clarification():
    bridge = P4P1Bridge()

    p1_input = bridge.build_p1_input(
        query="Tell me about this product",
        product_id="PROD-001",
        status="clarification",
        needs_clarification=True,
        clarification_question="Which product are you referring to?",
    )

    assert p1_input.needs_clarification is True
    assert (
        p1_input.clarification_question
        == "Which product are you referring to?"
    )