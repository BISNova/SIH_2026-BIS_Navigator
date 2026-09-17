import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.list_query import detect_list_intent, build_list_answer


SAMPLE_CATALOG = [
    {"standard_id": "STD-001", "is_number": "IS 2347:2023", "title": "Pressure Cooker", "is_mandatory": True},
    {"standard_id": "STD-002", "is_number": "IS 2082:2018", "title": "Water Heater", "is_mandatory": True},
    {"standard_id": "STD-003", "is_number": "IS 302:2024", "title": "General Safety Part 1", "is_mandatory": None},
]


def test_detects_list_all_phrasing():
    assert detect_list_intent("list all standards").is_list_query is True


def test_detects_give_me_n_phrasing():
    assert detect_list_intent("give me 5 certifications on electronics").is_list_query is True


def test_detects_top_n_phrasing():
    assert detect_list_intent("top 3 mandatory standards").is_list_query is True


def test_detects_how_many_phrasing():
    assert detect_list_intent("how many standards do you have").is_list_query is True


def test_single_product_query_not_treated_as_list():
    assert detect_list_intent("I manufacture domestic pressure cookers").is_list_query is False


def test_mandatory_filter_detected_from_phrasing():
    intent = detect_list_intent("list all mandatory standards")
    assert intent.is_list_query is True
    assert intent.mandatory_only is True


def test_build_list_answer_filters_to_mandatory_only():
    intent = detect_list_intent("list all mandatory standards")
    result = build_list_answer(intent, SAMPLE_CATALOG)
    assert len(result["standards"]) == 2
    assert result["evidence_sufficient"] is True
    assert "IS 2347:2023" in result["answer"]
    assert "IS 302:2024" not in result["answer"]


def test_build_list_answer_returns_all_when_no_filter():
    intent = detect_list_intent("list all standards")
    result = build_list_answer(intent, SAMPLE_CATALOG)
    assert len(result["standards"]) == 3


def test_build_list_answer_handles_empty_result_gracefully():
    intent = detect_list_intent("list all mandatory standards")
    result = build_list_answer(intent, [])
    assert result["standards"] == []
    assert "couldn't find" in result["answer"].lower()
