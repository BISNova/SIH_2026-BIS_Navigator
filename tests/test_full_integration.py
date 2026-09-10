import sys
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ENGINE_RAG = PROJECT_ROOT / "evidence_engine" / "rag"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EVIDENCE_ENGINE_RAG))
sys.path.insert(0, str(PROJECT_ROOT / "integration"))

from mock_embedder import MockSentenceTransformer  # noqa: E402
from product_intelligence.src.pipeline import ProductIntelligencePipeline  # noqa: E402
from integration.adapter import adapt_to_p1_input  # noqa: E402
from integration.orchestrator import run_full_pipeline  # noqa: E402

sys.path.insert(0, str(EVIDENCE_ENGINE_RAG))
from schemas.p1_input import P1Input  # noqa: E402


def get_product_pipeline():
    return ProductIntelligencePipeline()


def get_evidence_pipeline():
    """SANDBOX-ONLY: constructs her real EvidencePipeline with the
    embedding model mocked (see mock_embedder.py for why). On a machine
    with real internet access, just do EvidencePipeline() directly."""
    with mock.patch("pipeline.evidence_pipeline.SentenceTransformer", MockSentenceTransformer):
        from pipeline.evidence_pipeline import EvidencePipeline
        return EvidencePipeline()


# ---------- Adapter-level tests (no RAG call needed) ----------

def test_adapter_output_is_valid_instance_of_her_real_schema():
    pipeline = get_product_pipeline()
    result = pipeline.process("domestic pressure cooker")
    p1_input = adapt_to_p1_input(result)
    assert isinstance(p1_input, P1Input)


def test_get_standard_ids_extracts_correctly():
    pipeline = get_product_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    p1_input = adapt_to_p1_input(result)
    ids = p1_input.get_standard_ids()
    assert set(ids) == {"STD-002", "STD-003", "STD-004"}


def test_unknown_mandatory_collapses_to_false_in_her_narrow_schema_but_not_in_full():
    """The real, flagged limitation: her `mandatory: bool` can't
    represent 'unknown', so None collapses to False there - but the
    tri-state truth is preserved in applicable_standards_full."""
    pipeline = get_product_pipeline()
    result = pipeline.process("we make electric geysers for homes")
    p1_input = adapt_to_p1_input(result)

    secondary_full = [s for s in p1_input.applicable_standards_full if s.relationship_type == "secondary"]
    assert all(s.is_mandatory is None for s in secondary_full)  # true tri-state preserved

    secondary_narrow = [s for s in p1_input.applicable_standards if s.relevance == "secondary"]
    assert all(s.mandatory is False for s in secondary_narrow)  # collapsed, as her schema forces


# ---------- Full pipeline tests (real RAG call, mock embeddings) ----------

def test_full_pipeline_matched_product_produces_grounded_answer():
    result = run_full_pipeline(
        "I manufacture domestic pressure cookers for household use",
        get_product_pipeline(),
        get_evidence_pipeline(),
    )
    assert result.answer
    assert result.clarification_needed is False
    assert len(result.evidence) > 0
    assert all(e.text for e in result.evidence)
    assert result.confidence_label in {"high", "medium", "low"}


def test_full_pipeline_not_found_skips_rag_entirely():
    """If Product Intelligence can't confidently match, the RAG engine
    must never be called - verified here by passing an evidence_pipeline
    that would raise if .run() were ever invoked."""
    class ExplodingEvidencePipeline:
        def run(self, *args, **kwargs):
            raise AssertionError("RAG should not be called for a not_found query")

    result = run_full_pipeline(
        "organic vegetables from my farm",
        get_product_pipeline(),
        ExplodingEvidencePipeline(),
    )
    assert result.evidence_sufficient is False
    assert result.evidence == []
    assert result.clarification_needed is False  # not_found is distinct from clarification


def test_full_pipeline_clarification_skips_rag_entirely():
    """Same guarantee for the clarification path. Our current real KB
    has no naturally ambiguous product pair, so this uses a product
    pipeline monkeypatched to force a clarification_needed result -
    the point is testing the orchestrator's short-circuit, not P2's
    matching logic (already covered in product_intelligence/tests/)."""
    from product_intelligence.src.schemas import ProductMatchResult

    class ForcedClarificationPipeline:
        def process(self, query):
            return ProductMatchResult(
                query=query,
                normalized_query=query,
                status="clarification_needed",
                needs_clarification=True,
                clarification_question="Which product do you mean?",
                confidence_score=0.2,
                confidence_label="low",
            )

    class ExplodingEvidencePipeline:
        def run(self, *args, **kwargs):
            raise AssertionError("RAG should not be called during clarification")

    result = run_full_pipeline(
        "ambiguous thing",
        ForcedClarificationPipeline(),
        ExplodingEvidencePipeline(),
    )
    assert result.clarification_needed is True
    assert result.clarification_question == "Which product do you mean?"
    assert result.evidence == []


def test_full_pipeline_gold_jewellery_end_to_end():
    result = run_full_pipeline(
        "gold jewellery hallmarking",
        get_product_pipeline(),
        get_evidence_pipeline(),
    )
    assert result.answer
    assert len(result.evidence) > 0
