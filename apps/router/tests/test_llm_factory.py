from django.test import SimpleTestCase, override_settings

from apps.router.llm.exceptions import LLMConfigurationError
from apps.router.llm.factory import get_llm_provider
from apps.router.llm.gemini_provider import GeminiProvider
from apps.router.llm.ollama_provider import OllamaProvider


class LLMProviderFactoryTests(SimpleTestCase):
    @override_settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key")
    def test_returns_gemini_provider(self):
        provider = get_llm_provider()
        self.assertIsInstance(provider, GeminiProvider)

    @override_settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
        OLLAMA_MODEL="gemma3:4b",
    )
    def test_returns_ollama_provider(self):
        provider = get_llm_provider()
        self.assertIsInstance(provider, OllamaProvider)

    @override_settings(LLM_PROVIDER="invalid")
    def test_raises_for_unsupported_provider(self):
        with self.assertRaises(LLMConfigurationError):
            get_llm_provider()
