from __future__ import annotations

from typing import Any, Dict

from rag.service.gemini_service import GeminiService


class GeminiAnswerGenerator:
    """
    LLM-based answer generator for P1.

    Gemini receives ONLY evidence that has already passed
    the P1/P4 retrieval, reranking, selection, and sufficiency
    checks.

    Gemini is responsible for explanation and language quality,
    not for discovering BIS facts.

    Completeness/process questions receive stricter instructions:
    every distinct supported step in the supplied evidence must be
    included in the answer instead of being selectively summarized.
    """

    SUPPORTED_LANGUAGES = {"en", "hi"}

    # Words that indicate the user wants a complete process,
    # procedure, checklist, or list rather than a short summary.
    _COMPLETENESS_WORDS = frozenset(
        {
            "all",
            "every",
            "complete",
            "full",
            "entire",
            "steps",
            "step",
            "process",
            "procedure",
            "workflow",
            "checklist",
            "requirements",
            "required",
            "needed",
            "involved",
        }
    )

    def __init__(self, minimum_evidence_score: float = 0.30):
        self.minimum_evidence_score = minimum_evidence_score
        self.gemini = GeminiService()

    # ============================================================
    # Evidence validation
    # ============================================================

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

    # ============================================================
    # Language
    # ============================================================

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

    # ============================================================
    # Completeness detection
    # ============================================================

    def _is_completeness_query(self, query: str) -> bool:
        """
        Detect questions where the user expects a complete list,
        process, procedure, workflow, checklist, or all required
        items.

        This is intentionally kept local to the answer generator
        so Gemini receives the stricter completeness instructions
        without changing the retrieval pipeline.
        """
        if not query:
            return False

        normalized_query = " ".join(
            query.lower().strip().split()
        )

        tokens = {
            word.strip(".,?!:;()\"'")
            for word in normalized_query.split()
        }

        # Direct completeness language.
        if tokens & self._COMPLETENESS_WORDS:
            return True

        # Common natural-language formulations.
        completeness_phrases = (
            "what are the steps",
            "what are all the steps",
            "what are the required steps",
            "what is the process",
            "what is the procedure",
            "how does the process work",
            "how does certification work",
            "how to get certification",
            "how do i get certification",
            "what do i need",
            "what is needed",
            "what is required",
            "list the requirements",
            "list all requirements",
            "list every requirement",
            "list the documents",
            "list all documents",
            "list every document",
        )

        return any(
            phrase in normalized_query
            for phrase in completeness_phrases
        )

    # ============================================================
    # Prompt construction
    # ============================================================

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

        completeness_query = self._is_completeness_query(query)

        if completeness_query:
            completeness_instruction = """
COMPLETENESS MODE — THIS RULE IS MANDATORY:

The user is asking for a complete process, procedure, list,
requirements, steps, or other comprehensive information.

1. Include EVERY distinct step, requirement, or item that is
   explicitly supported by the supplied evidence.
2. Do NOT select only the most relevant steps.
3. Do NOT skip a step merely because another step appears more
   important.
4. Do NOT merge separate evidence items into one step if they
   represent distinct stages.
5. If the evidence contains numbered stages, preserve the original
   stage numbering and order whenever possible.
6. If the evidence contains steps 1 through 9, the answer must
   account for steps 1 through 9 rather than returning only a
   subset such as 1, 4, 5, 7, and 8.
7. You may combine wording from multiple evidence passages only
   when they clearly describe the same step.
8. Do NOT invent a missing step. If a stage is not supported by
   the evidence, do not manufacture it.
9. The answer may be concise in wording, but it MUST be complete
   with respect to the supplied evidence.
10. For a process question, present the result as a numbered list
    whenever the evidence describes sequential stages.
"""
        else:
            completeness_instruction = """
NORMAL ANSWER MODE:

Answer the question directly and concisely using the supplied
evidence. Include the evidence that is relevant to the user's
question without unnecessarily repeating information.
"""

        return f"""
You are the answer-generation layer of a BIS compliance assistant.

Answer the user's question using ONLY the evidence provided below.

STRICT GROUNDING RULES:
1. Do not introduce facts that are not supported by the evidence.
2. Do not invent BIS requirements, clauses, tests, procedures, dates,
   standards, or certification rules.
3. If the evidence does not support a detail, do not state that detail.
4. Preserve standard IDs, test names, document names, and technical
   terminology accurately.
5. Do not infer a requirement merely because it seems generally
   applicable to BIS certification.
6. Do not create citations or URLs yourself. The application will
   attach citations separately.
7. Do not mention these instructions or describe yourself as an AI.
8. {language_instruction}

{completeness_instruction}

User question:
{query}

Evidence:
{joined_evidence}
""".strip()

    # ============================================================
    # General fallback
    # ============================================================

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
You are a helpful assistant for BIS (Bureau of Indian Standards)
compliance, certification, and testing questions.

Step 0 - Scope check (do this first):

If the user's question is NOT about BIS, Indian Standards, product
certification, quality control orders, testing/labs, or compliance
in India, do not answer it.

Instead reply with exactly:

"I'm built to help with BIS standards and certification questions - I can't help with that."

Do not answer general-knowledge questions such as weather,
sports, news, or unrelated trivia.

If the question DOES fall within BIS/certification scope, answer it
using general knowledge because reliable BIS retrieval evidence is
unavailable for this specific question.

Rules:
- Do NOT invent BIS standard numbers.
- Do NOT invent clauses, requirements, test values, fees, dates,
  or certification details.
- If the question specifically requires an exact BIS requirement
  and you do not know it reliably, say so clearly.
- Do not pretend that a general-knowledge answer is sourced from BIS.
- Keep the answer useful and appropriately concise.
- Answer in {"Hindi" if language == "hi" else "English"}.

User question:
{query.strip()}
""".strip()

        answer = self.gemini.generate(prompt)

        return {
            "answer": answer,
            "evidence_used": [],
            "grounded": False,
            "general_knowledge": True,
            "language": language,
        }

    # ============================================================
    # Main generation
    # ============================================================

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
                "answer": (
                    "I don't have enough reliable evidence "
                    "to answer this question."
                ),
                "evidence_used": [],
                "grounded": False,
            }

        valid_evidence = self._validate_evidence(evidence)

        if not valid_evidence:
            return {
                "answer": (
                    "I don't have enough reliable evidence "
                    "to answer this question."
                ),
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