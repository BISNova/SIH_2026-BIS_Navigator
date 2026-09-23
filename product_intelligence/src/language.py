"""
Detects non-English queries and translates them to English before they
reach product matching - so the user can type in their own language,
but Product Intelligence and P1 always see English.

Language detection:
  1. Unicode script detection for Indic scripts.
  2. Deterministic Romanized-Hindi (Hinglish) marker detection.
  3. langdetect only for longer Latin-script text.

Translation:
  - Common Hinglish patterns are normalized locally and deterministically.
  - Other non-English languages use deep-translator as a best-effort
    external translation service.
  - Translation failures never crash the pipeline.
"""

from dataclasses import dataclass
from typing import Optional
import logging
import re


# Unicode block ranges for scripts an Indian-standards tool realistically
# sees. Extend this dict if a new script shows up in real usage.
SCRIPT_RANGES = {
    "hi": [(0x0900, 0x097F)],   # Devanagari (Hindi, Marathi, Sanskrit)
    "bn": [(0x0980, 0x09FF)],   # Bengali
    "ta": [(0x0B80, 0x0BFF)],   # Tamil
    "te": [(0x0C00, 0x0C7F)],   # Telugu
    "kn": [(0x0C80, 0x0CFF)],   # Kannada
    "ml": [(0x0D00, 0x0D7F)],   # Malayalam
    "gu": [(0x0A80, 0x0AFF)],   # Gujarati
    "pa": [(0x0A00, 0x0A7F)],   # Gurmukhi (Punjabi)
    "or": [(0x0B00, 0x0B7F)],   # Odia
}

MIN_WORDS_FOR_LANGDETECT = 8


# Romanized Hindi ("Hinglish") is written in plain Latin script, so
# Unicode script detection cannot catch it.
HINGLISH_MARKER_WORDS = frozenset({
    "ka",
    "ki",
    "ke",
    "hai",
    "kaunsa",
    "konsa",
    "kya",
    "chahiye",
    "liye",
    "wala",
    "wale",
    "wali",
    "kaise",
    "kahan",
    "kitna",
    "kitne",
    "bataye",
    "batao",
})

MIN_HINGLISH_MARKERS = 1

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionResult:
    language: str
    is_non_english: bool
    method: str


def _script_of(text: str) -> Optional[str]:
    """Return the language code for the first matching Unicode script."""
    for ch in text:
        code_point = ord(ch)

        for lang, ranges in SCRIPT_RANGES.items():
            for start, end in ranges:
                if start <= code_point <= end:
                    return lang

    return None


def detect_language(text: str) -> LanguageDetectionResult:
    if not text or not text.strip():
        return LanguageDetectionResult("en", False, "default")

    # 1. Deterministic Unicode-script detection.
    script_lang = _script_of(text)

    if script_lang:
        return LanguageDetectionResult(
            script_lang,
            True,
            "script",
        )

    # 2. Deterministic Hinglish detection.
    normalized_words = {
        word.strip(".,?!:;()\"'").lower()
        for word in text.split()
    }

    hinglish_hits = normalized_words & HINGLISH_MARKER_WORDS

    if len(hinglish_hits) >= MIN_HINGLISH_MARKERS:
        return LanguageDetectionResult(
            "hi",
            True,
            "hinglish_markers",
        )

    # 3. Use langdetect only for longer Latin-script text.
    word_count = len(text.split())

    if word_count >= MIN_WORDS_FOR_LANGDETECT:
        try:
            from langdetect import detect, DetectorFactory

            DetectorFactory.seed = 0
            detected = detect(text)

            if detected != "en":
                return LanguageDetectionResult(
                    detected,
                    True,
                    "langdetect",
                )

        except Exception:
            # Detection failure must never block the query.
            pass

    return LanguageDetectionResult(
        "en",
        False,
        "default",
    )


def _translate_hinglish_locally(text: str) -> str:
    """
    Handle common Romanized-Hindi patterns without an external
    translation service.

    This is intentionally conservative. We only rewrite phrases that
    are common in BIS/product questions and preserve product names,
    standard numbers and technical English terms unchanged.
    """

    original = text.strip()

    # ---------------------------------------------------------------
    # High-value BIS/product question patterns.
    # ---------------------------------------------------------------

    # Example:
    # "Pressure cooker ke liye BIS ka kaunsa standard hai?"
    #
    # -> "Which BIS standard applies to pressure cooker?"
    match = re.fullmatch(
        r"(.+?)\s+ke\s+liye\s+BIS\s+ka\s+(?:kaunsa|konsa)\s+standard\s+hai[?.!]*",
        original,
        flags=re.IGNORECASE,
    )

    if match:
        product = match.group(1).strip()

        return (
            f"Which BIS standard applies to {product}?"
        )

    # Example:
    # "Pressure cooker ke liye kaunsa standard hai?"
    match = re.fullmatch(
        r"(.+?)\s+ke\s+liye\s+(?:kaunsa|konsa)\s+standard\s+hai[?.!]*",
        original,
        flags=re.IGNORECASE,
    )

    if match:
        product = match.group(1).strip()

        return (
            f"Which standard applies to {product}?"
        )

    # Example:
    # "Pressure cooker ke liye BIS ka standard kya hai?"
    match = re.fullmatch(
        r"(.+?)\s+ke\s+liye\s+BIS\s+ka\s+standard\s+kya\s+hai[?.!]*",
        original,
        flags=re.IGNORECASE,
    )

    if match:
        product = match.group(1).strip()

        return (
            f"What BIS standard applies to {product}?"
        )

    # ---------------------------------------------------------------
    # General conservative word/phrase normalization.
    # Used only if a more specific pattern above did not match.
    # ---------------------------------------------------------------

    normalized = original

    phrase_replacements = [
        (r"\bke\s+liye\b", "for"),
        (r"\bkaunsa\b", "which"),
        (r"\bkonsa\b", "which"),
        (r"\bkaise\b", "how"),
        (r"\bkahan\b", "where"),
        (r"\bkitna\b", "how much"),
        (r"\bkitne\b", "how many"),
        (r"\bchahiye\b", "need"),
        (r"\bbataye\b", "tell me"),
        (r"\bbatao\b", "tell me"),
        (r"\bkya\b", "what"),
        (r"\bka\b", "of"),
        (r"\bki\b", "of"),
        (r"\bke\b", "of"),
        (r"\bhai\b", "is"),
        (r"\bwala\b", "type"),
        (r"\bwale\b", "types"),
        (r"\bwali\b", "type"),
    ]

    for pattern, replacement in phrase_replacements:
        normalized = re.sub(
            pattern,
            replacement,
            normalized,
            flags=re.IGNORECASE,
        )

    return normalized


def translate_to_english(
    text: str,
    source_language: str,
) -> str:
    """
    Best-effort translation to English.

    Hinglish is handled locally first so common Romanized-Hindi queries
    do not depend on an external translation API.

    Other languages use GoogleTranslator followed by MyMemoryTranslator.
    Any failure falls back to the original text rather than crashing.
    """

    if source_language == "en":
        return text

    # ---------------------------------------------------------------
    # Romanized Hindi / Hinglish
    # ---------------------------------------------------------------
    if source_language == "hi":
        # First try deterministic local normalization.
        local_translation = _translate_hinglish_locally(text)

        if local_translation != text:
            logger.info(
                "Used local Hinglish normalization: %r -> %r",
                text,
                local_translation,
            )
            return local_translation

        # If this is actual Hindi in Devanagari, use the external
        # translator below. Local Hinglish rules are intentionally
        # conservative.
        if _script_of(text) == "hi":
            pass
        else:
            # For an unrecognized Romanized-Hindi sentence, make a
            # conservative word-level normalization rather than relying
            # on a rate-limited public endpoint.
            return _translate_hinglish_locally(text)

    # ---------------------------------------------------------------
    # Other non-English languages
    # ---------------------------------------------------------------
    try:
        from deep_translator import (
            GoogleTranslator,
            MyMemoryTranslator,
        )
    except ImportError:
        logger.error(
            "deep-translator is not installed; returning original text."
        )
        return text

    translators = [
        (
            GoogleTranslator,
            {
                "source": source_language,
                "target": "en",
            },
        ),
        (
            MyMemoryTranslator,
            {
                "source": source_language,
                "target": "en",
            },
        ),
    ]

    for translator_cls, kwargs in translators:
        try:
            translated = translator_cls(**kwargs).translate(text)

            if translated and translated.strip():
                return translated

            logger.warning(
                "%s returned empty translation for lang=%s query=%r",
                translator_cls.__name__,
                source_language,
                text,
            )

        except Exception as exc:
            logger.warning(
                "%s failed for lang=%s query=%r: %s",
                translator_cls.__name__,
                source_language,
                text,
                exc,
            )

    logger.error(
        "All translators failed for lang=%s query=%r - "
        "falling back to original text",
        source_language,
        text,
    )

    return text


def normalize_query_to_english(
    text: str,
) -> tuple[str, str]:
    """
    Detect the language and return:

        (english_text, detected_language_code)

    If the query is already English, it is returned unchanged.
    Translation failures never raise an exception.
    """

    result = detect_language(text)

    if not result.is_non_english:
        return text, "en"

    translated = translate_to_english(
        text,
        result.language,
    )

    return translated, result.language