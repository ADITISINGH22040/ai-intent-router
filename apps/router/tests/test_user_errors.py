from django.test import SimpleTestCase
from requests import ConnectionError, HTTPError, Timeout
from rest_framework import status

from apps.router.user_errors import (
    CURRENCY_PAIR_NOT_FOUND,
    CURRENCY_UNAVAILABLE,
    INVOICE_ORDER_STATUS_NOT_ELIGIBLE,
    PARAMETER_REQUIRED,
    REQUEST_TIMED_OUT,
    SUMMARY_UNAVAILABLE,
    TOOL_EXECUTION_FAILED,
    WEATHER_LOCATION_NOT_FOUND,
    WEATHER_UNAVAILABLE,
    http_status_for_tool_errors,
    http_status_for_tool_result,
    message_for_request_exception,
)


class UserErrorMessageTests(SimpleTestCase):
    def test_maps_bad_request_to_not_found_message(self):
        response = type("Response", (), {"status_code": 400})()
        exc = HTTPError("400 Client Error", response=response)

        message = message_for_request_exception(
            exc,
            not_found=WEATHER_LOCATION_NOT_FOUND,
            unavailable=CURRENCY_UNAVAILABLE,
        )

        self.assertEqual(message, WEATHER_LOCATION_NOT_FOUND)

    def test_maps_timeout_to_generic_message(self):
        message = message_for_request_exception(
            Timeout("timed out"),
            not_found=WEATHER_LOCATION_NOT_FOUND,
        )

        self.assertEqual(message, REQUEST_TIMED_OUT)

    def test_maps_connection_error_to_unavailable_message(self):
        message = message_for_request_exception(
            ConnectionError("connection failed"),
            not_found=WEATHER_LOCATION_NOT_FOUND,
            unavailable=CURRENCY_UNAVAILABLE,
        )

        self.assertEqual(message, CURRENCY_UNAVAILABLE)


class HttpStatusForToolResultTests(SimpleTestCase):
    def test_success_returns_200(self):
        self.assertEqual(
            http_status_for_tool_result({"success": True, "errors": None}),
            status.HTTP_200_OK,
        )

    def test_order_not_found_returns_404(self):
        self.assertEqual(
            http_status_for_tool_errors(
                {"order_id": ["Order 123 does not exist."]}
            ),
            status.HTTP_404_NOT_FOUND,
        )

    def test_invalid_order_id_returns_400(self):
        self.assertEqual(
            http_status_for_tool_errors(
                {"order_id": ["order_id must be a valid integer."]}
            ),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_weather_location_not_found_returns_404(self):
        self.assertEqual(
            http_status_for_tool_errors(
                {"location": [WEATHER_LOCATION_NOT_FOUND]}
            ),
            status.HTTP_404_NOT_FOUND,
        )

    def test_weather_unavailable_returns_503(self):
        self.assertEqual(
            http_status_for_tool_errors({"location": [WEATHER_UNAVAILABLE]}),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_currency_pair_not_found_returns_404(self):
        self.assertEqual(
            http_status_for_tool_errors({"currency": [CURRENCY_PAIR_NOT_FOUND]}),
            status.HTTP_404_NOT_FOUND,
        )

    def test_currency_unavailable_returns_503(self):
        self.assertEqual(
            http_status_for_tool_errors({"service": [CURRENCY_UNAVAILABLE]}),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_invalid_order_status_returns_422(self):
        self.assertEqual(
            http_status_for_tool_errors(
                {
                    "status": [
                        "Invalid status. Allowed values: pending, confirmed."
                    ]
                }
            ),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def test_ineligible_invoice_status_returns_422(self):
        self.assertEqual(
            http_status_for_tool_errors(
                {"status": [INVOICE_ORDER_STATUS_NOT_ELIGIBLE]}
            ),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def test_summary_failure_returns_502(self):
        self.assertEqual(
            http_status_for_tool_errors({"summary": [SUMMARY_UNAVAILABLE]}),
            status.HTTP_502_BAD_GATEWAY,
        )

    def test_tool_execution_failure_returns_500(self):
        self.assertEqual(
            http_status_for_tool_errors({"tool": [TOOL_EXECUTION_FAILED]}),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def test_missing_parameter_returns_400(self):
        self.assertEqual(
            http_status_for_tool_errors({"location": [PARAMETER_REQUIRED]}),
            status.HTTP_400_BAD_REQUEST,
        )
