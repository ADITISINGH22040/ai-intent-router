from abc import ABC, abstractmethod

from apps.router.llm.prompts import CLASSIFICATION_PROMPT
from apps.router.llm.schemas import parse_classification_response


class BaseLLMProvider(ABC):
    """Base class for LLM-backed intent classification providers."""

    @abstractmethod
    def classify_intent(self, query: str) -> dict:
        """
        Classify a natural language query.

        Returns:
            dict with keys: intent, confidence, parameters
        """

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Run a plain-text completion (used by SummaryTool)."""

    def parse_classification(self, raw_text: str) -> dict:
        return parse_classification_response(raw_text)

    @staticmethod
    def build_classification_prompt(query: str) -> str:
        return f"{CLASSIFICATION_PROMPT.strip()}\n\nUser query:\n{query}"
