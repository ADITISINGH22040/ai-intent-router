from django.conf import settings

from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMConfigurationError
from apps.router.llm.gemini_provider import GeminiProvider
from apps.router.llm.ollama_provider import OllamaProvider

_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def get_llm_provider() -> BaseLLMProvider:
    provider_name = settings.LLM_PROVIDER.lower().strip()

    try:
        provider_class = _PROVIDER_REGISTRY[provider_name]
    except KeyError as exc:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise LLMConfigurationError(
            f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
            f"Supported values: {supported}."
        ) from exc

    return provider_class()
