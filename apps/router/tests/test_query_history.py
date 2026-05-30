from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.test import APIRequestFactory

from apps.router.constants.query_status import QueryStatus
from apps.router.models import QueryHistory
from apps.router.services.history_service import HistoryService
from apps.router.throttling import RATE_LIMIT_MESSAGE, api_exception_handler
from apps.router.views import QueryAPIView

LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK_SETTINGS = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_RATES": {
        "query": "10/min",
    },
    "EXCEPTION_HANDLER": "apps.router.throttling.api_exception_handler",
}


class HistoryServiceTests(TestCase):
    def test_save_creates_query_history_row(self):
        record = HistoryService.save(
            query="What's the weather in London?",
            intent="WEATHER_QUERY",
            confidence=0.91,
            parameters={"location": "London"},
            response={"query": "What's the weather in London?"},
            success=True,
            cached=False,
            provider="ollama",
            tool="WeatherTool",
            processing_time_ms=42,
        )

        self.assertEqual(QueryHistory.objects.count(), 1)
        self.assertEqual(record.query_text, "What's the weather in London?")
        self.assertEqual(record.llm_output["intent"], "WEATHER_QUERY")
        self.assertEqual(record.llm_output["confidence"], 0.91)
        self.assertEqual(record.tool_response["tool"], "WeatherTool")
        self.assertEqual(record.status, QueryStatus.COMPLETED)
        self.assertEqual(record.processing_time_ms, 42)


@override_settings(CACHES=LOC_MEM_CACHES, REST_FRAMEWORK=REST_FRAMEWORK_SETTINGS)
class QueryAPIViewHistoryTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.router.views.ToolRouter")
    @patch("apps.router.views.IntentClassifier")
    def test_successful_query_creates_history(self, mock_classifier_cls, mock_router_cls):
        mock_classifier_cls.return_value.classify.return_value = {
            "intent": "WEATHER_QUERY",
            "confidence": 0.95,
            "parameters": {"location": "London"},
        }
        mock_router_cls.return_value.route.return_value = {
            "success": True,
            "data": {"temperature_c": 18.0},
            "errors": None,
            "meta": {"cached": True},
        }

        factory = APIRequestFactory()
        request = factory.post("/api/query/", {"query": "Weather in London?"}, format="json")
        response = QueryAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(QueryHistory.objects.count(), 1)
        record = QueryHistory.objects.get()
        self.assertEqual(record.query_text, "Weather in London?")
        self.assertEqual(record.llm_output["intent"], "WEATHER_QUERY")
        self.assertEqual(record.llm_output["confidence"], 0.95)
        self.assertEqual(record.tool_response["tool"], "WeatherTool")
        self.assertTrue(record.tool_response["cached"])
        self.assertEqual(record.status, QueryStatus.COMPLETED)
        self.assertIsNotNone(record.processing_time_ms)

    @patch("apps.router.views.IntentClassifier")
    def test_validation_failure_creates_history(self, mock_classifier_cls):
        factory = APIRequestFactory()
        request = factory.post("/api/query/", {"query": ""}, format="json")
        response = QueryAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QueryHistory.objects.count(), 1)
        record = QueryHistory.objects.get()
        self.assertEqual(record.status, QueryStatus.FAILED)
        self.assertIn("query", record.llm_output["error"])
        mock_classifier_cls.assert_not_called()

    @patch("apps.router.views.IntentClassifier")
    def test_classification_failure_creates_history(self, mock_classifier_cls):
        from apps.router.services.exceptions import IntentClassificationError

        mock_classifier_cls.return_value.classify.side_effect = IntentClassificationError(
            "Could not determine a supported intent for this query."
        )

        factory = APIRequestFactory()
        request = factory.post("/api/query/", {"query": "hello there"}, format="json")
        response = QueryAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(QueryHistory.objects.count(), 1)
        record = QueryHistory.objects.get()
        self.assertEqual(record.query_text, "hello there")
        self.assertEqual(record.status, QueryStatus.FAILED)
        self.assertIn("classification", record.llm_output["error"])


@override_settings(CACHES=LOC_MEM_CACHES, REST_FRAMEWORK=REST_FRAMEWORK_SETTINGS)
class QueryAPIViewThrottleTests(TestCase):
    def test_throttle_exception_returns_clean_json_and_logs_history(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/api/query/",
            data='{"query": "Summarize hello"}',
            content_type="application/json",
        )

        response = api_exception_handler(
            Throttled(wait=60),
            {"request": request, "view": QueryAPIView()},
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], RATE_LIMIT_MESSAGE)
        self.assertIsNone(response.data["data"])
        self.assertEqual(QueryHistory.objects.count(), 1)
        record = QueryHistory.objects.get()
        self.assertEqual(record.query_text, "Summarize hello")
        self.assertEqual(record.status, QueryStatus.FAILED)
        self.assertIn("rate_limit", record.llm_output["error"])
