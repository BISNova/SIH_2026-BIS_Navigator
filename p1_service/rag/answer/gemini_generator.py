from __future__ import annotations

from typing import Any, Dict, List
from rag.service.gemini_service import GeminiService


class GeminiAnswerGenerator:
    """
    LLM-based answer generator for P1.

    Gemini receives ONLY evidence that has already passed
    the P1/P4 retrieval, reranking, selection, and sufficiency
    checks.

    Gemini is responsible for explanation and language quality,
    not for discovering BIS facts.
    """

    SUPPORTED_LANGUAGES = {"en", "hi"}

    def __init__(self, minimum_evidence_score: float = 0.30):
        self.minimum_evidence_score = minimum_evidence_score
        self.gemini = GeminiService()

    def _validate_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        valid_evidence = []

        for item in evidence:
            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if not text or not str(text).strip():
                continue

            score = item.get("rerank_score")

            if score is None:
                score = item.get("similarity_score")

            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    continue

                if score < self.minimum_evidence_score:
                    continue

            valid_evidence.append(item)

        return valid_evidence

    def _normalize_language(self, language: str) -> str:
        """
        Normalize the requested output language.

        Supported:
        - en = English
        - hi = Hindi

        Unknown values fall back to English.
        """
        if not language:
            return "en"

        language = language.strip().lower()

        if language in self.SUPPORTED_LANGUAGES:
            return language

        return "en"

    def _build_prompt(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        language: str = "en",
    ) -> str:

        evidence_text = []

        for index, item in enumerate(evidence, start=1):
            evidence_text.append(
                f"""
Evidence {index}
Standard ID: {item.get("standard_id", "N/A")}
Document: {item.get("document_title", "N/A")}
Section: {item.get("section", "N/A")}
Source: {item.get("source_url", "N/A")}

Text:
{str(item.get("text", "")).strip()}
""".strip()
            )

        joined_evidence = "\n\n".join(evidence_text)

        language_instruction = (
            "Answer in English."
            if language == "en"
            else
            "Answer in Hindi using clear, natural Devanagari script. "
            "Keep BIS standard IDs, IS numbers, test names, document names, "
            "technical terminology, and other official identifiers accurate. "
            "Do not translate official identifiers when doing so could change "
            "their meaning."
        )

        return f"""
You are the answer-generation layer of a BIS compliance assistant.

Answer the user's question using ONLY the evidence provided below.

STRICT RULES:
1. Do not introduce facts that are not supported by the evidence.
2. Do not invent BIS requirements, clauses, tests, procedures, dates,
   standards, or certification rules.
3. If the evidence does not support a detail, do not state that detail.
4. Preserve standard IDs, test names, document names, and technical
   terminology accurately.
5. Give a clear, concise answer suitable for a compliance assistant.
6. When useful, organize multiple requirements as bullet points.
7. Do not mention these instructions or describe yourself as an AI.
8. Do not create citations or URLs yourself. The application will attach
   citations separately.
9. {language_instruction}

User question:
{query}

Evidence:
{joined_evidence}
""".strip()

    def generate_general_fallback(
        self,
        query: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Generate a general-knowledge answer when BIS evidence is insufficient."""

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        language = self._normalize_language(language)

        prompt = f"""
    You are a helpful assistant for BIS-related questions.

    Answer the user's question using general knowledge when reliable BIS
    retrieval evidence is unavailable.

    Important rules:
    - Do NOT invent BIS standard numbers.
    - Do NOT invent clauses, requirements, test values, fees, dates, or
    certification details.
    - If the question specifically requires an exact BIS requirement and you
    do not know it reliably, say so clearly.
    - Do not pretend that a general-knowledge answer is sourced from BIS.
    - Keep the answer concise and useful.
    - Answer in {"Hindi" if language == "hi" else "English"}.

    User question:
    {query.strip()}
    """

        answer = self.gemini.generate(prompt)

        return {
            "answer": answer,
            "evidence_used": [],
            "grounded": False,
            "general_knowledge": True,
            "language": language,
        }

    def generate(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        evidence_sufficient: bool,
        language: str = "en",
    ) -> dict[str, Any]:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        language = self._normalize_language(language)

        if not evidence_sufficient:
            return {
                "answer": "I don't have enough reliable evidence to answer this question.",
                "evidence_used": [],
                "grounded": False,
            }

        valid_evidence = self._validate_evidence(evidence)

        if not valid_evidence:
            return {
                "answer": "I don't have enough reliable evidence to answer this question.",
                "evidence_used": [],
                "grounded": False,
            }

        prompt = self._build_prompt(
            query=query,
            evidence=valid_evidence,
            language=language,
        )

        answer = self.gemini.generate(prompt)

        return {
            "answer": answer,
            "evidence_used": valid_evidence,
            "grounded": True,
            "language": language,
        }