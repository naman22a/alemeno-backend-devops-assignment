"""All LLM I/O goes through this one client. Keeping it isolated means:

  - the retry/backoff policy (assignment 5e) lives in exactly one place
  - swapping Ollama for Gemini later is a one-file change, not a
    find-and-replace across the codebase
  - services/classification.py and services/narrative.py never touch
    httpx directly, so they're trivially mockable in tests
"""

import json
import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)

class LLMCallError(Exception):
    """Raised for both transport failures and malformed JSON responses.

    Treating "Ollama is unreachable" and "Ollama returned garbage JSON"
    as the same retryable error is intentional - a flaky model response
    deserves the same backoff-and-retry treatment as a flaky network call.
    """

class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(LLMCallError),
        reraise=True,
    )
    def generate_json(self, prompt: str, timeout: float = 180.0) -> dict:
        """Send a prompt, force structured JSON output, return it parsed.

        Raises LLMCallError (after exhausting retries) on any failure -
        callers decide what "give up gracefully" means for their step
        (e.g. mark a batch llm_failed instead of crashing the whole job).
        """
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise LLMCallError(f"Ollama request failed: {exc}") from exc

        body = response.json()
        raw_text = body.get("response", "")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Ollama returned non-JSON response: %s", raw_text[:300])
            raise LLMCallError(f"Ollama returned invalid JSON: {raw_text[:300]}") from exc
