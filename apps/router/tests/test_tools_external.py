from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.router.tools.currency_tool import CurrencyTool
from apps.router.tools.weather_tool import WeatherTool


class WeatherToolTests(SimpleTestCase):
    @override_settings(WEATHERAPI_API_KEY="")
    def test_requires_api_key(self):
        result = WeatherTool().execute({"location": "Lucknow"})
        self.assertFalse(result["success"])
        self.assertIn("config", result["errors"])

    @override_settings(WEATHERAPI_API_KEY="test-key", TOOL_REQUEST_TIMEOUT=5)
    @patch("apps.router.tools.weather_tool.requests.get")
    def test_fetches_current_weather(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "location": {
                        "name": "Lucknow",
                        "region": "Uttar Pradesh",
                        "country": "India",
                        "lat": 26.85,
                        "lon": 80.95,
                        "localtime": "2026-05-30 12:00",
                    },
                    "current": {
                        "temp_c": 34.0,
                        "temp_f": 93.2,
                        "feelslike_c": 36.0,
                        "humidity": 40,
                        "wind_kph": 12.0,
                        "condition": {"text": "Sunny", "icon": "//cdn.weatherapi.com/icon.png"},
                    },
                }
            ),
        )

        result = WeatherTool().execute({"location": "Lucknow"})

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["resolved_name"], "Lucknow")
        self.assertEqual(result["data"]["temperature_c"], 34.0)
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["key"], "test-key")
        self.assertEqual(call_kwargs["params"]["q"], "Lucknow")


class CurrencyToolTests(SimpleTestCase):
    @override_settings(EXCHANGERATE_API_KEY="")
    def test_requires_api_key(self):
        result = CurrencyTool().execute(
            {"amount": 100, "from_currency": "USD", "to_currency": "INR"}
        )
        self.assertFalse(result["success"])
        self.assertIn("config", result["errors"])

    @override_settings(EXCHANGERATE_API_KEY="test-key", TOOL_REQUEST_TIMEOUT=5)
    @patch("apps.router.tools.currency_tool.requests.get")
    def test_applies_conversion_rate_locally(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "result": "success",
                    "base_code": "USD",
                    "target_code": "INR",
                    "conversion_rate": 83.5,
                    "time_last_update_utc": "Fri, 30 May 2026 00:00:00 +0000",
                }
            ),
        )

        result = CurrencyTool().execute(
            {"amount": 100, "from_currency": "usd", "to_currency": "inr"}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["conversion_rate"], "83.5")
        self.assertEqual(result["data"]["converted_amount"], "8350.0000")
        self.assertEqual(Decimal(result["data"]["converted_amount"]), Decimal("100") * Decimal("83.5"))
        self.assertIn("/pair/USD/INR", mock_get.call_args.args[0])
