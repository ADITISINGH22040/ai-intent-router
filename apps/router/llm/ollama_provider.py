import httpx
from django.conf import settings

from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMConfigurationError, LLMProviderError
from apps.router.llm.prompts import CLASSIFICATION_PROMPT


class OllamaProvider(BaseLLMProvider):
    """Local Ollama chat API (ollama serve)."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.LLM_REQUEST_TIMEOUT

        if not self.base_url:
            raise LLMConfigurationError("OLLAMA_BASE_URL is not configured.")

    def classify_intent(self, query: str) -> dict:
        raw_text = self._chat(query)
        return self.parse_classification(raw_text)

    def _chat(self, query: str) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": query},
            ],
            "options": {"temperature": 0},
        }

        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        try:
            return response.json()["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMProviderError("Unexpected response format from Ollama.") from exc
