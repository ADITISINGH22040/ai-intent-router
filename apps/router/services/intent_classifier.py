import logging
from typing import Any

from apps.router.constants.intents import (
    ALLOWED_INTENTS,
    INTENT_CONFIDENCE_THRESHOLD,
    INTENT_PARAMETERS,
    Intent,
)
from apps.router.llm.base import BaseLLMProvider
from apps.router.llm.exceptions import LLMValidationError
from apps.router.llm.factory import get_llm_provider
from apps.router.services.exceptions import IntentClassificationError

ACTIONABLE_INTENTS = ALLOWED_INTENTS - {Intent.UNKNOWN}

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies user queries via the LLM layer.

    Responsible for intent validation, confidence checks, and parameter extraction.
    Raises IntentClassificationError when intent is UNKNOWN or confidence is too low.
    Does not execute tools.
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self._provider = provider

    def classify(self, query: str) -> dict[str, Any]:
        raw_classification = self._get_provider().classify_intent(query)
        classification = self._validate_classification(raw_classification)
        self._ensure_actionable(classification)
        logger.info(
            "Intent classified intent=%s confidence=%s parameters=%s",
            classification["intent"],
            classification["confidence"],
            classification["parameters"],
        )
        return classification

    def _get_provider(self) -> BaseLLMProvider:
        return self._provider or get_llm_provider()

    def _validate_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        intent = self._normalize_intent(payload.get("intent"))
        confidence = self._validate_confidence(payload.get("confidence"))
        parameters = self._extract_parameters(intent, payload.get("parameters"))

        return {
            "intent": intent,
            "confidence": confidence,
            "parameters": parameters,
        }

    @staticmethod
    def _normalize_intent(intent: Any) -> str:
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
    def _ensure_actionable(classification: dict[str, Any]) -> None:
        confidence = classification["confidence"]
        intent = classification["intent"]

        if confidence < INTENT_CONFIDENCE_THRESHOLD:
            raise IntentClassificationError(
                f"Confidence {confidence} is below the minimum threshold "
                f"of {INTENT_CONFIDENCE_THRESHOLD}."
            )

        if intent not in ACTIONABLE_INTENTS:
            raise IntentClassificationError(
                "Could not determine a supported intent for this query."
            )
