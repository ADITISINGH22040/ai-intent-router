from django.test import SimpleTestCase

from apps.router.constants.intents import Intent
from apps.router.services.intent_classifier import IntentClassifier


class StubLLMProvider:
    def __init__(self, classification: dict) -> None:
        self.classification = classification
        self.last_query = None

    def classify_intent(self, query: str) -> dict:
        self.last_query = query
        return self.classification


class IntentClassifierTests(SimpleTestCase):
    def test_returns_valid_classification(self):
        provider = StubLLMProvider(
            {
                "intent": "CURRENCY_CONVERSION",
                "confidence": 0.94,
                "parameters": {
                    "amount": 100,
                    "from_currency": "USD",
                    "to_currency": "INR",
                    "ignored": "value",
                },
            }
        )
        result = IntentClassifier(provider=provider).classify("Convert 100 USD to INR")

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
        self.assertEqual(provider.last_query, "Convert 100 USD to INR")

    def test_rejects_unknown_intent_from_llm(self):
        provider = StubLLMProvider(
            {
                "intent": "BOOK_FLIGHT",
                "confidence": 0.9,
                "parameters": {},
            }
        )
        result = IntentClassifier(provider=provider).classify("Book a flight")

        self.assertEqual(result["intent"], Intent.UNKNOWN)
        self.assertEqual(result["parameters"], {})

    def test_low_confidence_returns_unknown(self):
        provider = StubLLMProvider(
            {
                "intent": "WEATHER_QUERY",
                "confidence": 0.5,
                "parameters": {"location": "Mumbai"},
            }
        )
        result = IntentClassifier(provider=provider).classify("Weather in Mumbai")

        self.assertEqual(result["intent"], Intent.UNKNOWN)
        self.assertEqual(result["confidence"], 0.5)
        self.assertEqual(result["parameters"], {})

    def test_confidence_at_threshold_keeps_intent(self):
        provider = StubLLMProvider(
            {
                "intent": "ORDER_LOOKUP",
                "confidence": 0.65,
                "parameters": {"status": "pending"},
            }
        )
        result = IntentClassifier(provider=provider).classify("Show pending orders")

        self.assertEqual(result["intent"], Intent.ORDER_LOOKUP)
        self.assertEqual(result["parameters"], {"status": "pending"})
