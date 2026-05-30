class LLMProviderError(Exception):
    """Raised when an LLM provider fails to classify a query."""


class LLMConfigurationError(LLMProviderError):
    """Raised when provider configuration is missing or invalid."""


class LLMResponseParseError(LLMProviderError):
    """Raised when provider output cannot be parsed as valid classification JSON."""


class LLMValidationError(LLMProviderError):
    """Raised when provider output fails schema validation."""
