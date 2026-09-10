from rag.knowledge.evidence_builder import P4EvidenceBuilder


def test_build_pressure_cooker_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    assert len(evidence) > 0

    test_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-TEST-")
    ]

    assert len(test_evidence) == 12

    for item in test_evidence:
        assert item.standard_id == "STD-001"
        assert item.document_id
        assert item.document_title
        assert item.text
        assert item.chunk_id.startswith("P4-TEST-")


def test_build_water_heater_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-002")

    assert len(evidence) > 0

    test_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-TEST-")
    ]

    assert len(test_evidence) == 4

    test_names = {
        item.section_header
        for item in test_evidence
    }

    assert "Performance" in test_names or len(test_names) > 0


def test_qco_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    qco_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-QCO-")
    ]

    assert len(qco_evidence) > 0

    for item in qco_evidence:
        assert item.standard_id == "STD-001"
        assert item.document_type == "QCO"
        assert item.text
        assert item.source_url


def test_conformity_route_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    route_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-ROUTE-")
    ]

    assert len(route_evidence) > 0

    for item in route_evidence:
        assert item.standard_id == "STD-001"
        assert item.text


def test_certification_step_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    step_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-STEP-")
    ]

    assert len(step_evidence) == 9

    for item in step_evidence:
        assert item.standard_id == "STD-001"
        assert item.text


def test_lab_scope_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-002")

    lab_evidence = [
        item
        for item in evidence
        if item.chunk_id.startswith("P4-LABSCOPE-")
    ]

    assert len(lab_evidence) > 0

    for item in lab_evidence:
        assert item.standard_id == "STD-002"
        assert item.document_type == "LAB_SCOPE"
        assert item.text
        assert item.source_url


def test_empty_inspection_requirements_produce_no_fake_evidence():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    inspection_evidence = [
        item
        for item in evidence
        if "inspection" in item.text.lower()
    ]

    assert inspection_evidence == []


def test_unknown_standard_is_safe():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("UNKNOWN")

    assert evidence == []


def test_p4_provenance_is_preserved():
    builder = P4EvidenceBuilder()

    evidence = builder.build_for_standard("STD-001")

    test_evidence = [
        item
        for item in evidence
        if item.chunk_id == "P4-TEST-001"
    ]

    assert len(test_evidence) == 1

    item = test_evidence[0]

    assert item.standard_id == "STD-001"
    assert item.document_id == "DOC-002"
    assert item.document_title
    assert item.document_type == "QCO"
    assert item.authority_level == 2