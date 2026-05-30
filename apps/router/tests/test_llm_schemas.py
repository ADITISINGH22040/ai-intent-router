from django.test import SimpleTestCase

from apps.router.constants.intents import Intent
from apps.router.llm.exceptions import LLMResponseParseError, LLMValidationError
from apps.router.llm.schemas import parse_classification_response


class ParseClassificationResponseTests(SimpleTestCase):
    def test_parses_valid_json(self):
        result = parse_classification_response(
            """
            {
              "intent": "CURRENCY_CONVERSION",
              "confidence": 0.94,
              "parameters": {
                "amount": 100,
                "from_currency": "USD",
                "to_currency": "INR",
                "extra": "ignored"
              }
            }
            """
        )

        self.assertEqual(result["intent"], Intent.CURRENCY_CONVERSION)
        self.assertEqual(result["confidence"], 0.94)
        self.assertEqual(
            result["parameters"],
            {
                "amount": 100,
                "from_currency": "USD",
                "to_currency": "INR",
            },
        )

    def test_rejects_unknown_intent(self):
        result = parse_classification_response(
            '{"intent": "BOOK_FLIGHT", "confidence": 0.8, "parameters": {}}'
        )

        self.assertEqual(result["intent"], Intent.UNKNOWN)
        self.assertEqual(result["parameters"], {})

    def test_parses_json_inside_code_fence(self):
        result = parse_classification_response(
            '```json\n{"intent": "UNKNOWN", "confidence": 0.2, "parameters": {}}\n```'
        )

        self.assertEqual(result["intent"], Intent.UNKNOWN)

    def test_raises_on_invalid_json(self):
        with self.assertRaises(LLMResponseParseError):
            parse_classification_response("not json")

    def test_raises_on_invalid_confidence(self):
        with self.assertRaises(LLMValidationError):
            parse_classification_response(
                '{"intent": "UNKNOWN", "confidence": 1.5, "parameters": {}}'
            )
