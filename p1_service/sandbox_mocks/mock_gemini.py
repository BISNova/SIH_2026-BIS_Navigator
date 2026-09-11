"""
SANDBOX-ONLY MOCK. This exists purely because this development sandbox
has no Gemini API key configured (and shouldn't - keys should never be
baked into a shared/sandboxed environment). On any machine with a real
GEMINI_API_KEY in .env, none of this file is needed - P1's real
GeminiService works as-is.

Returns a clearly-labeled canned string built directly from the
evidence passed in, so it's obvious in any test output that this is not
a real LLM-generated answer.
"""


class MockGeminiService:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, prompt: str) -> str:
        return (
            "[MOCK GEMINI RESPONSE - sandbox has no real API key] "
            "This is a placeholder answer standing in for a real "
            "Gemini-generated response. The prompt included "
            f"{len(prompt)} characters of evidence context."
        )
