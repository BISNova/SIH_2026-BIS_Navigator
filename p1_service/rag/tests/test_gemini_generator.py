from unittest.mock import Mock, patch

from rag.answer.gemini_generator import GeminiAnswerGenerator


def test_gemini_generator_returns_grounded_answer():
    mock_service = Mock()
    mock_service.generate.return_value = (
        "The pressure cooker requires a proof pressure test."
    )

    evidence = [
        {
            "chunk_id": "TEST-001",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "The pressure cooker shall undergo a proof pressure test.",
            "rerank_score": 0.80,
        }
    ]

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="What test is required?",
            evidence=evidence,
            evidence_sufficient=True,
        )

    assert result["grounded"] is True
    assert "proof pressure test" in result["answer"].lower()
    assert len(result["evidence_used"]) == 1
    assert result["language"] == "en"

    mock_service.generate.assert_called_once()


def test_gemini_generator_rejects_insufficient_evidence():
    mock_service = Mock()

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="What test is required?",
            evidence=[],
            evidence_sufficient=False,
        )

    assert result["grounded"] is False
    assert result["evidence_used"] == []
    assert "enough reliable evidence" in result["answer"].lower()

    mock_service.generate.assert_not_called()


def test_gemini_generator_filters_low_score_evidence():
    mock_service = Mock()
    mock_service.generate.return_value = "Supported answer."

    evidence = [
        {
            "chunk_id": "TEST-001",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "Valid evidence.",
            "rerank_score": 0.80,
        },
        {
            "chunk_id": "TEST-002",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "Weak evidence.",
            "rerank_score": 0.10,
        },
    ]

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="What test is required?",
            evidence=evidence,
            evidence_sufficient=True,
        )

    assert result["grounded"] is True
    assert len(result["evidence_used"]) == 1
    assert result["evidence_used"][0]["chunk_id"] == "TEST-001"

    mock_service.generate.assert_called_once()


def test_gemini_generator_supports_english_language():
    mock_service = Mock()
    mock_service.generate.return_value = (
        "The pressure cooker requires a proof pressure test."
    )

    evidence = [
        {
            "chunk_id": "TEST-001",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "The pressure cooker shall undergo a proof pressure test.",
            "rerank_score": 0.80,
        }
    ]

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="What test is required?",
            evidence=evidence,
            evidence_sufficient=True,
            language="en",
        )

    assert result["grounded"] is True
    assert result["language"] == "en"

    # Verify Gemini was actually given the English instruction.
    prompt = mock_service.generate.call_args[0][0]

    assert "Answer in English." in prompt

    mock_service.generate.assert_called_once()


def test_gemini_generator_supports_hindi_language():
    mock_service = Mock()
    mock_service.generate.return_value = (
        "प्रेशर कुकर के लिए प्रूफ प्रेशर टेस्ट आवश्यक है।"
    )

    evidence = [
        {
            "chunk_id": "TEST-001",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "The pressure cooker shall undergo a proof pressure test.",
            "rerank_score": 0.80,
        }
    ]

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="प्रेशर कुकर के लिए कौन सा टेस्ट आवश्यक है?",
            evidence=evidence,
            evidence_sufficient=True,
            language="hi",
        )

    assert result["grounded"] is True
    assert result["language"] == "hi"
    assert "प्रूफ प्रेशर टेस्ट" in result["answer"]

    # Verify Gemini was actually given the Hindi instruction.
    prompt = mock_service.generate.call_args[0][0]

    assert "Answer in Hindi" in prompt
    assert "Devanagari" in prompt
    assert "STD-001" in prompt

    mock_service.generate.assert_called_once()


def test_gemini_generator_falls_back_to_english_for_unsupported_language():
    mock_service = Mock()
    mock_service.generate.return_value = "Supported answer."

    evidence = [
        {
            "chunk_id": "TEST-001",
            "standard_id": "STD-001",
            "document_id": "DOC-001",
            "document_title": "Pressure Cooker Manual",
            "text": "The pressure cooker shall undergo a proof pressure test.",
            "rerank_score": 0.80,
        }
    ]

    with patch(
        "rag.answer.gemini_generator.GeminiService",
        return_value=mock_service,
    ):
        generator = GeminiAnswerGenerator()

        result = generator.generate(
            query="What test is required?",
            evidence=evidence,
            evidence_sufficient=True,
            language="fr",
        )

    assert result["grounded"] is True
    assert result["language"] == "en"

    prompt = mock_service.generate.call_args[0][0]

    assert "Answer in English." in prompt
    assert "Answer in Hindi" not in prompt

    mock_service.generate.assert_called_once()