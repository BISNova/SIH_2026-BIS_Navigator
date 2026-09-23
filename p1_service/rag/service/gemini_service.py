from __future__ import annotations

import os
import random
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError


load_dotenv()


class GeminiService:
    """
    Service wrapper around the Google Gemini API.

    Handles temporary Gemini 503/UNAVAILABLE and 429/RESOURCE_EXHAUSTED
    errors with bounded exponential backoff and jitter, AND rotates
    across multiple API keys when a key's quota is exhausted - so a
    free-tier daily/per-minute limit getting hit mid-demo (or during a
    judge's automated test run that fires many requests back to back)
    degrades to "use the next key" instead of every subsequent request
    failing until someone manually swaps the key and redeploys.

    The RAG/evidence pipeline remains unchanged.
    """

    def __init__(self, model: Optional[str] = None):
        api_keys = self._load_api_keys()

        if not api_keys:
            raise ValueError(
                "No Gemini API key is configured. Set GEMINI_API_KEYS "
                "(comma-separated, preferred) or GEMINI_API_KEY in "
                "the .env file."
            )

        self._api_keys = api_keys
        self._clients = [
            genai.Client(api_key=key) for key in api_keys
        ]

        # Sticky rotation: stay on the current key until it's found
        # exhausted, then move forward and never go back within this
        # process's lifetime. Simple and correct for a hackathon demo
        # / judge test run - a full restart (new deploy/process) resets
        # back to key 0, which is fine since quotas are usually
        # per-day anyway.
        self._current_key_index = 0

        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        # Number of additional attempts on the SAME key before moving
        # to the next one. Example: 3 retries = maximum 4 API attempts
        # per key before rotating.
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
    def _load_api_keys() -> list[str]:
        """
        GEMINI_API_KEYS (comma-separated, 2-5 keys) is preferred so the
        service can rotate when one key's quota runs out. Falls back
        to the single GEMINI_API_KEY for backward compatibility.
        """
        multi = os.getenv("GEMINI_API_KEYS", "")
        keys = [k.strip() for k in multi.split(",") if k.strip()]

        if keys:
            return keys

        single = os.getenv("GEMINI_API_KEY")
        return [single] if single else []

    @property
    def client(self):
        """Current active client - kept as a property (not a plain
        attribute) so existing external references to `self.client`
        always see whichever key is currently active after a rotation."""
        return self._clients[self._current_key_index]

    def _rotate_to_next_key(self) -> bool:
        """
        Move to the next API key. Returns False if every key has
        already been tried (all exhausted) - the caller should then
        fall back to the degraded response instead of looping forever.
        """
        if self._current_key_index >= len(self._clients) - 1:
            return False

        self._current_key_index += 1

        print(
            f"Gemini key #{self._current_key_index} exhausted/failing - "
            f"rotating to key #{self._current_key_index + 1} of "
            f"{len(self._clients)}."
        )

        return True

    # Retryable status codes: 503 (temporary unavailability, original
    # behaviour) plus 429 (rate limit / RESOURCE_EXHAUSTED). A 429 was
    # observed causing an unhandled HTTP 500 out of P1 in testing
    # ("And what about the marking requirements?") because it isn't a
    # ServerError-with-503 and so fell straight through this check
    # before, skipping retry/backoff entirely and re-raising immediately.
    _RETRYABLE_STATUS_CODES = frozenset({503, 429})

    @staticmethod
    def _is_retryable_503(exc: Exception) -> bool:
        """
        Return True for Gemini 503 (UNAVAILABLE) and 429 (rate limit /
        RESOURCE_EXHAUSTED) errors - both are transient and worth a
        bounded retry.

        We deliberately do not retry every exception because errors
        such as invalid API keys, invalid requests, or missing models
        should fail immediately.
        """

        status_code = getattr(exc, "code", None)

        if status_code in GeminiService._RETRYABLE_STATUS_CODES:
            return True

        status_code = getattr(exc, "status_code", None)

        if status_code in GeminiService._RETRYABLE_STATUS_CODES:
            return True

        message = str(exc).upper()

        return (
            "503" in message
            or "UNAVAILABLE" in message
            or "429" in message
            or "RESOURCE_EXHAUSTED" in message
            or "RATE LIMIT" in message
        )

    @staticmethod
    def _is_quota_exhausted(exc: Exception) -> bool:
        """
        A quota/rate-limit error (429 / RESOURCE_EXHAUSTED) means THIS
        KEY specifically is out of budget - retrying the same key with
        backoff just burns time for the same result. Rotate to the
        next key immediately instead. A 503/UNAVAILABLE, by contrast,
        is Gemini's server having a temporary problem and is unrelated
        to which key is used, so that still gets the normal backoff
        retry on the same key first (see generate()).
        """
        status_code = getattr(exc, "code", None) or getattr(
            exc, "status_code", None
        )

        if status_code == 429:
            return True

        message = str(exc).upper()

        return "429" in message or "RESOURCE_EXHAUSTED" in message

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

        Two layers of resilience:
          1. Per-key retry with bounded backoff for transient 503
             (server temporarily unavailable) errors.
          2. Key rotation for 429/RESOURCE_EXHAUSTED (this key's quota
             is used up) - moves straight to the next configured key
             instead of wasting retries on a key that will keep
             failing until its quota resets. This is what lets a judge
             running many automated test queries in a row not hit a
             wall the moment one free-tier key's daily/per-minute
             limit is reached.

        If every configured key is exhausted/failing, returns a
        controlled message instead of crashing P1 with HTTP 500.
        """

        last_exc: Exception | None = None

        while True:
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

                except (ServerError, ClientError) as exc:
                    # IMPORTANT: a 429 rate-limit response comes back as
                    # a ClientError, not a ServerError - the original
                    # `except ServerError` here never caught it at all,
                    # so a 429 skipped this whole retry block and
                    # propagated straight up through p1_service.run()
                    # as an unhandled exception (the raw HTTP 500 seen
                    # in testing on "And what about the marking
                    # requirements?"). Now both exception types are
                    # caught.
                    if not self._is_retryable_503(exc):
                        raise

                    last_exc = exc

                    # Quota exhausted on this key specifically -
                    # rotate immediately rather than burning retries.
                    if self._is_quota_exhausted(exc):
                        print(
                            f"Gemini key #{self._current_key_index + 1} "
                            f"quota exhausted: {exc}"
                        )
                        break

                    # Transient 503 - no retries left on this key.
                    if attempt >= self.max_retries:
                        print(
                            "Gemini temporarily unavailable on key "
                            f"#{self._current_key_index + 1} after "
                            f"{self.max_retries} retries: {exc}"
                        )
                        break

                    retry_number = attempt + 1
                    delay = self._retry_delay(retry_number)

                    print(
                        "Gemini returned HTTP 503 (UNAVAILABLE). "
                        f"Retrying in {delay:.2f}s "
                        f"(retry {retry_number}/{self.max_retries})..."
                    )

                    time.sleep(delay)

            # Retries on the current key are exhausted (either quota
            # or repeated 503s) - try the next configured key, if any.
            if self._rotate_to_next_key():
                continue

            # Every key has been tried and failed.
            print(
                f"All {len(self._clients)} Gemini API key(s) "
                f"exhausted/failing. Last error: {last_exc}"
            )

            return (
                "The BIS evidence was retrieved successfully, "
                "but the answer-generation service is temporarily "
                "unavailable. Please try the same question again "
                "in a few moments."
            )