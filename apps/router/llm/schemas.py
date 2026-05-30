import json
import re
from typing import Any

from apps.router.constants.intents import ALLOWED_INTENTS, INTENT_PARAMETERS, Intent
from apps.router.llm.exceptions import LLMResponseParseError, LLMValidationError

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def extract_json_payload(raw_text: str) -> dict[str, Any]:
    if not raw_text or not raw_text.strip():
        raise LLMResponseParseError("LLM returned an empty response.")

    cleaned = _JSON_FENCE_PATTERN.sub("", raw_text.strip())

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMResponseParseError("LLM response did not contain valid JSON.") from None
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMResponseParseError("LLM response contained malformed JSON.") from exc

    if not isinstance(payload, dict):
        raise LLMResponseParseError("LLM response JSON must be an object.")

    return payload


def validate_classification(payload: dict[str, Any]) -> dict[str, Any]:
    intent = payload.get("intent")
    if not isinstance(intent, str) or intent not in ALLOWED_INTENTS:
        intent = Intent.UNKNOWN

    confidence = payload.get("confidence")
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise LLMValidationError("Confidence must be a number between 0 and 1.") from exc

    if not 0.0 <= confidence_value <= 1.0:
        raise LLMValidationError("Confidence must be between 0 and 1.")

    raw_parameters = payload.get("parameters", {})
    if raw_parameters is None:
        raw_parameters = {}
    if not isinstance(raw_parameters, dict):
        raise LLMValidationError("Parameters must be a JSON object.")

    allowed_keys = INTENT_PARAMETERS.get(intent, ())
    parameters = {
        key: raw_parameters.get(key)
        for key in allowed_keys
    }

    return {
        "intent": intent,
        "confidence": round(confidence_value, 4),
        "parameters": parameters,
    }


def parse_classification_response(raw_text: str) -> dict[str, Any]:
    payload = extract_json_payload(raw_text)
    return validate_classification(payload)
