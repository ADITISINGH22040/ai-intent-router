from typing import Any

from apps.router.constants.intents import (
    ALLOWED_INTENTS,
    INTENT_PARAMETERS,
    INTENT_CONFIDENCE_THRESHOLD,
    Intent,
)
from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMValidationError
from apps.router.llm.factory import get_llm_provider


class IntentClassifier:
    """
    Classifies user queries via the LLM layer.

    Responsible for intent validation, confidence checks, and parameter extraction.
    Does not execute tools.
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self._provider = provider

    def classify(self, query: str) -> dict[str, Any]:
        raw_classification = self._get_provider().classify_intent(query)
        classification = self._validate_classification(raw_classification)
        return self._apply_confidence_threshold(classification)

    def _get_provider(self) -> BaseLLMProvider:
        return self._provider or get_llm_provider()

    def _validate_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        intent = self._validate_intent(payload.get("intent"))
        confidence = self._validate_confidence(payload.get("confidence"))
        parameters = self._extract_parameters(intent, payload.get("parameters"))

        return {
            "intent": intent,
            "confidence": confidence,
            "parameters": parameters,
        }

    @staticmethod
    def _validate_intent(intent: Any) -> str:
        if isinstance(intent, str) and intent in ALLOWED_INTENTS:
            return intent
        return Intent.UNKNOWN

    @staticmethod
    def _validate_confidence(confidence: Any) -> float:
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise LLMValidationError("Confidence must be a number between 0 and 1.") from exc

        if not 0.0 <= confidence_value <= 1.0:
            raise LLMValidationError("Confidence must be between 0 and 1.")

        return round(confidence_value, 4)

    @staticmethod
    def _extract_parameters(intent: str, raw_parameters: Any) -> dict[str, Any]:
        if raw_parameters is None:
            raw_parameters = {}
        if not isinstance(raw_parameters, dict):
            raise LLMValidationError("Parameters must be a JSON object.")

        allowed_keys = INTENT_PARAMETERS.get(intent, ())
        return {key: raw_parameters.get(key) for key in allowed_keys}

    @staticmethod
    def _apply_confidence_threshold(classification: dict[str, Any]) -> dict[str, Any]:
        if classification["confidence"] < INTENT_CONFIDENCE_THRESHOLD:
            return {
                "intent": Intent.UNKNOWN,
                "confidence": classification["confidence"],
                "parameters": {},
            }
        return classification
