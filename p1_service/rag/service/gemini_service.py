from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiService:
    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Add it to the .env file."
            )

        self.client = genai.Client(api_key=api_key)

        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

    def generate(self, prompt: str) -> str:
        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt,
            generation_config={
                "thinking_level": "low",
            },
        )

        text = getattr(interaction, "output_text", None)

        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        return text.strip()