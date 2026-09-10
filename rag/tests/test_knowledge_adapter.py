from rag.knowledge.adapter import P4KnowledgeAdapter


def test_adapter_loads_p4_data():
    adapter = P4KnowledgeAdapter()

    assert len(adapter.products) == 3
    assert len(adapter.standards) == 7
    assert len(adapter.tests) == 27
    assert len(adapter.labs) == 15


def test_get_product():
    adapter = P4KnowledgeAdapter()

    product = adapter.get_product("PROD-001")

    assert product is not None
    assert product["product_id"] == "PROD-001"


def test_product_standard_mapping():
    adapter = P4KnowledgeAdapter()

    standards = adapter.get_standards_for_product("PROD-002")

    standard_ids = {
        item["standard_id"]
        for item in standards
    }

    assert standard_ids == {
        "STD-002",
        "STD-003",
        "STD-004",
    }


def test_product_standard_relationships():
    adapter = P4KnowledgeAdapter()

    standards = adapter.get_standards_for_product("PROD-002")

    relationships = {
        item["standard_id"]: item["relationship_type"]
        for item in standards
    }

    assert relationships["STD-002"] == "primary"
    assert relationships["STD-003"] == "secondary"
    assert relationships["STD-004"] == "secondary"


def test_get_tests_for_standard():
    adapter = P4KnowledgeAdapter()

    tests = adapter.get_tests("STD-002")

    assert len(tests) == 4

    test_names = {
        test["test_name"]
        for test in tests
    }

    assert "Rated Capacity" in test_names
    assert "Heating Performance" in test_names
    assert "Standing Heat Loss" in test_names
    assert "Pressure Test" in test_names


def test_lab_scope_for_standard():
    adapter = P4KnowledgeAdapter()

    scope = adapter.get_lab_scope("STD-002")

    assert len(scope) > 0

    for record in scope:
        assert record["standard_id"] == "STD-002"
        assert "lab_id" in record
        assert "test_name" in record


def test_labs_for_test():
    adapter = P4KnowledgeAdapter()

    labs = adapter.get_labs_for_test(
        "STD-002",
        "Pressure Test",
    )

    assert len(labs) > 0

    for result in labs:
        assert result["lab"] is not None
        assert result["scope"]["test_name"] == "Pressure Test"


def test_empty_inspection_requirements():
    adapter = P4KnowledgeAdapter()

    requirements = adapter.get_inspection_requirements("STD-001")

    assert requirements == []


def test_documents_for_standard():
    adapter = P4KnowledgeAdapter()

    documents = adapter.get_documents("STD-001")

    assert len(documents) > 0

    for document in documents:
        assert document["standard_id"] == "STD-001"


def test_unknown_product_is_safe():
    adapter = P4KnowledgeAdapter()

    assert adapter.get_product("UNKNOWN") is None
    assert adapter.get_product_attributes("UNKNOWN") == []
    assert adapter.get_standards_for_product("UNKNOWN") == []


def test_complete_product_knowledge():
    adapter = P4KnowledgeAdapter()

    knowledge = adapter.get_knowledge_for_product("PROD-001")

    assert knowledge["product"]["product_id"] == "PROD-001"
    assert len(knowledge["attributes"]) > 0
    assert len(knowledge["standards"]) > 0
    assert len(knowledge["documents"]) > 0