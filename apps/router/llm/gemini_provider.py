import logging

import httpx
from django.conf import settings

from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMConfigurationError, LLMProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.LLM_REQUEST_TIMEOUT

        if not self.api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")

    def classify_intent(self, query: str) -> dict:
        raw_text = self._generate_content(
            self.build_classification_prompt(query),
            response_json=True,
        )
        return self.parse_classification(raw_text)

    def complete(self, prompt: str) -> str:
        return self._generate_content(prompt, response_json=False)

    def _generate_content(self, prompt: str, *, response_json: bool) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        generation_config = {"temperature": 0}
        if response_json:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }

        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Gemini request failed model=%s error=%s", self.model, exc)
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(response_payload: dict) -> str:
        try:
            return response_payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("Unexpected response format from Gemini.") from exc
