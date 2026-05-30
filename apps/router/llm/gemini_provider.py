import httpx
from django.conf import settings

from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMConfigurationError, LLMProviderError


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.LLM_REQUEST_TIMEOUT

        if not self.api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")

    def classify_intent(self, query: str) -> dict:
        raw_text = self._generate_content(query)
        return self.parse_classification(raw_text)

    def _generate_content(self, query: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [{"text": self.build_classification_prompt(query)}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
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
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(response_payload: dict) -> str:
        try:
            return response_payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("Unexpected response format from Gemini.") from exc
