import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.language import (
    detect_language,
    translate_to_english,
    normalize_query_to_english,
)


# ---------- Script detection (real, offline, no network needed) ----------

def test_hindi_devanagari_detected_reliably():
    result = detect_language("मुझे प्रेशर कुकर के लिए मानक चाहिए")
    assert result.language == "hi"
    assert result.is_non_english is True
    assert result.method == "script"


def test_tamil_detected_reliably():
    result = detect_language("எனக்கு அழுத்தம் குக்கர் தரம் தேவை")
    assert result.language == "ta"
    assert result.is_non_english is True


def test_short_english_queries_not_misdetected_as_non_english():
    """The real bug found while building this: langdetect alone
    misidentifies these exact short English queries as French. Script
    detection + the short-text guard must prevent that regression."""
    queries = [
        "I manufacture domestic pressure cookers",
        "domestic pressure cooker",
        "gold jewellery hallmarking",
        "we make electric geysers for homes",
        "what tests are required",
    ]
    for q in queries:
        result = detect_language(q)
        assert result.language == "en", f"{q!r} was misdetected as {result.language!r}"
        assert result.is_non_english is False


def test_empty_query_defaults_to_english():
    result = detect_language("")
    assert result.language == "en"
    assert result.is_non_english is False


# ---------- Translation (mocked - see language.py docstring on why) ----------

def test_translate_to_english_skips_when_already_english():
    result = translate_to_english("domestic pressure cooker", "en")
    assert result == "domestic pressure cooker"


def test_translate_to_english_calls_free_translator_for_non_english():
    with mock.patch("deep_translator.GoogleTranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = "pressure cooker standard"
        result = translate_to_english("प्रेशर कुकर मानक", "hi")
        assert result == "pressure cooker standard"
        MockTranslator.assert_called_once_with(source="hi", target="en")


def test_translate_to_english_falls_back_to_original_on_failure():
    """A failed translation (network error, rate limit, etc.) must never
    crash the pipeline - it should degrade to the original text."""
    with mock.patch("deep_translator.GoogleTranslator", side_effect=Exception("network down")):
        result = translate_to_english("प्रेशर कुकर मानक", "hi")
        assert result == "प्रेशर कुकर मानक"  # unchanged, not crashed


# ---------- Full normalize_query_to_english wiring ----------

def test_normalize_english_query_passes_through_unchanged():
    text, lang = normalize_query_to_english("domestic pressure cooker")
    assert text == "domestic pressure cooker"
    assert lang == "en"


def test_normalize_hindi_query_detects_and_attempts_translation():
    with mock.patch("deep_translator.GoogleTranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = "pressure cooker standard"
        text, lang = normalize_query_to_english("प्रेशर कुकर मानक")
        assert text == "pressure cooker standard"
        assert lang == "hi"
