from __future__ import annotations

import os
import random
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError


load_dotenv()


class GeminiService:
    """
    Service wrapper around the Google Gemini API.

    Handles temporary Gemini 503/UNAVAILABLE errors with
    bounded exponential backoff and jitter.

    The RAG/evidence pipeline remains unchanged.
    """

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

        # Number of additional attempts after the first request.
        # Example: 3 retries = maximum 4 API attempts.
        self.max_retries = int(
            os.getenv("GEMINI_MAX_RETRIES", "3")
        )

        self.initial_retry_delay = float(
            os.getenv("GEMINI_RETRY_INITIAL_DELAY", "2")
        )

        self.max_retry_delay = float(
            os.getenv("GEMINI_RETRY_MAX_DELAY", "10")
        )

    @staticmethod
    def _is_retryable_503(exc: Exception) -> bool:
        """
        Return True only for Gemini 503 / UNAVAILABLE errors.

        We deliberately do not retry every exception because errors
        such as invalid API keys, invalid requests, or missing models
        should fail immediately.
        """

        status_code = getattr(exc, "code", None)

        if status_code == 503:
            return True

        status_code = getattr(exc, "status_code", None)

        if status_code == 503:
            return True

        message = str(exc).upper()

        return (
            "503" in message
            or "UNAVAILABLE" in message
        )

    def _retry_delay(self, retry_number: int) -> float:
        """
        Calculate bounded exponential backoff with jitter.

        retry_number:
            1 -> roughly initial delay
            2 -> roughly 2x initial delay
            3 -> roughly 4x initial delay
        """

        delay = min(
            self.initial_retry_delay * (2 ** (retry_number - 1)),
            self.max_retry_delay,
        )

        # Small random jitter prevents repeated requests from
        # retrying at exactly the same time.
        jitter = random.uniform(0, min(1.0, delay * 0.25))

        return delay + jitter

    def generate(self, prompt: str) -> str:
        """
        Generate a grounded answer using Gemini.

        Temporary 503 errors are retried with bounded backoff.

        If Gemini remains temporarily unavailable after all retries,
        return a controlled message instead of crashing P1 with HTTP 500.
        """

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

                text = getattr(response, "text", None)

                if not text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return text.strip()

            except ServerError as exc:
                # Retry only temporary 503 errors.
                if not self._is_retryable_503(exc):
                    raise

                # No retries remaining.
                if attempt >= self.max_retries:
                    print(
                        "Gemini temporarily unavailable after "
                        f"{self.max_retries} retries: {exc}"
                    )

                    return (
                        "The BIS evidence was retrieved successfully, "
                        "but the answer-generation service is temporarily "
                        "unavailable. Please try the same question again "
                        "in a few moments."
                    )

                retry_number = attempt + 1
                delay = self._retry_delay(retry_number)

                print(
                    "Gemini returned HTTP 503 (UNAVAILABLE). "
                    f"Retrying in {delay:.2f}s "
                    f"(retry {retry_number}/{self.max_retries})..."
                )

                time.sleep(delay)