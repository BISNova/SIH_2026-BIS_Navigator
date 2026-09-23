"""
Detects non-English queries and translates them to English before they
reach product matching - so the user can type in their own language,
but Product Intelligence and P1 always see English.

Deliberately NOT using Gemini/OpenAI for this (per explicit requirement
- no per-query API cost for something this mechanical). Two free,
no-API-key tools instead:

  1. Unicode script detection (this file, no dependency) - the primary,
     reliable signal. If the text contains Devanagari (Hindi/Marathi),
     Bengali, Tamil, Telugu, etc. characters, we know for certain it's
     not English. This is 100% deterministic, not a guess.

  2. `langdetect` (pip, offline, no network) - used ONLY as a secondary
     check for longer Latin-script text, and deliberately NOT trusted
     for short text. This is documented here because it's a real,
     tested finding, not a guess:

        langdetect.detect("I manufacture domestic pressure cookers")
        -> "fr"  (WRONG - this is English)
        langdetect.detect("domestic pressure cooker")
        -> "fr"  (WRONG again)

     Short strings are exactly what real chat queries look like, so
     trusting langdetect on them would mistranslate perfectly good
     English queries. Given this product's actual user base (Indian
     manufacturers/consumers), the realistic non-English case is
     overwhelmingly an Indic script, which script detection already
     catches with certainty - so langdetect is only consulted for
     longer (8+ word) pure-Latin-script text, as a low-stakes secondary
     signal, and English is always the safe default otherwise.

Translation: `deep-translator`'s GoogleTranslator - free, no API key,
no billing (unofficial wrapper around Google's public translate
endpoint, not the paid Cloud Translation API). This means it depends on
a public endpoint outside our control, so every call is wrapped in a
try/except that falls back to the original text - a failed translation
should never crash the pipeline or block a query.

NOTE ON TESTING: this sandbox's network cannot reach the translation
endpoint (same restriction as this project's other external services -
see INTEGRATION_NOTES.md). Script detection and the routing logic are
fully tested here (pure/offline). The actual translate() network call
is tested with the real library mocked - it will work with any normal
internet connection, but that exact call could not be verified live
from this environment.
"""

from dataclasses import dataclass
from typing import Optional
import logging

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

MIN_WORDS_FOR_LANGDETECT = 8  # only trust langdetect on longer Latin text


@dataclass
class LanguageDetectionResult:
    language: str            # ISO 639-1 code, "en" if undetermined/English
    is_non_english: bool
    method: str               # "script" | "langdetect" | "default"


def _script_of(text: str) -> Optional[str]:
    """Returns the language code for the first matching script found, or
    None if the text is (as far as we can tell) plain Latin script."""
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

    script_lang = _script_of(text)
    if script_lang:
        return LanguageDetectionResult(script_lang, True, "script")

    word_count = len(text.split())
    if word_count >= MIN_WORDS_FOR_LANGDETECT:
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0  # deterministic results
            detected = detect(text)
            if detected != "en":
                return LanguageDetectionResult(detected, True, "langdetect")
        except Exception:
            # langdetect itself failing is not a reason to block the query -
            # fall through to the English default.
            pass

    return LanguageDetectionResult("en", False, "default")


# def translate_to_english(text: str, source_language: str) -> str:
#     """
#     Best-effort translation to English. On ANY failure (network error,
#     rate limit, unsupported language code, the free endpoint being
#     unreachable), returns the ORIGINAL text unchanged rather than
#     raising - a translation failure should degrade gracefully, not
#     break the query.
#     """
#     if source_language == "en":
#         return text

#     try:
#         from deep_translator import GoogleTranslator
#         translated = GoogleTranslator(source=source_language, target="en").translate(text)
#         return translated if translated else text
#     except Exception:
#         return text


logger = logging.getLogger(__name__)


def _translate_to_english_all(text: str, source_language: str) -> list[str]:
    """
    Try every configured free translator and return every DISTINCT
    successful translation, instead of stopping at the first success.

    Why: GoogleTranslator and MyMemoryTranslator are independent
    services and often phrase the same source sentence differently -
    one may render a domain term in a way that matches the KB's
    wording, the other may not. Keeping only "whichever ran first"
    means retrieval quality depends on an arbitrary ordering. Callers
    that want retrieval resilience should search with ALL of these
    (see EvidencePipeline.run()'s query_variants) rather than trust
    a single one.
    """
    if source_language == "en":
        return [text]

    from deep_translator import GoogleTranslator, MyMemoryTranslator

    variants: list[str] = []
    seen: set[str] = set()

    for translator_cls, kwargs in [
        (GoogleTranslator, {"source": source_language, "target": "en"}),
        (MyMemoryTranslator, {"source": source_language, "target": "en"}),
    ]:
        try:
            translated = translator_cls(**kwargs).translate(text)

            if translated and translated.strip():
                key = translated.strip().lower()

                if key not in seen:
                    seen.add(key)
                    variants.append(translated.strip())

            else:
                logger.warning(
                    "%s returned empty translation for lang=%s query=%r",
                    translator_cls.__name__, source_language, text,
                )
        except Exception as exc:
            logger.warning(
                "%s failed for lang=%s query=%r: %s",
                translator_cls.__name__, source_language, text, exc,
            )

    if not variants:
        logger.error(
            "All translators failed for lang=%s query=%r - falling back to original text",
            source_language, text,
        )

    return variants


def translate_to_english(text: str, source_language: str) -> str:
    """
    Best-effort SINGLE translation to English - kept for existing
    callers. Returns the first successful translator's output, or the
    original text unchanged if every translator failed.
    """
    variants = _translate_to_english_all(text, source_language)
    return variants[0] if variants else text


def normalize_query_to_english(text: str) -> tuple[str, str]:
    """
    The original single-result entry point: detect the language, and
    return (english_text, detected_language_code). If detection or
    translation fails or isn't needed, english_text == text.
    """
    result = detect_language(text)
    if not result.is_non_english:
        return text, "en"

    translated = translate_to_english(text, result.language)
    return translated, result.language


def normalize_query_to_english_variants(text: str) -> tuple[list[str], str]:
    """
    Like normalize_query_to_english, but returns EVERY distinct
    successful translation instead of just one. Use this wherever the
    result feeds something that can search/rank against multiple
    phrasings and keep the best (product matching, evidence
    retrieval) - it costs nothing extra (both translators already run
    today, one of them was just being discarded), and it means one
    translator's odd phrasing of a domain term no longer determines
    the whole result on its own.

    Always returns at least one element (falls back to [text] if every
    translator failed, same fallback behavior as translate_to_english).
    """
    result = detect_language(text)
    if not result.is_non_english:
        return [text], "en"

    variants = _translate_to_english_all(text, result.language)

    if not variants:
        variants = [text]

    return variants, result.language
