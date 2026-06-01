import requests
from rest_framework import status

SERVICE_UNAVAILABLE = (
    "This service is temporarily unavailable. Please try again later."
)
REQUEST_TIMED_OUT = "The request timed out. Please try again later."

WEATHER_LOCATION_NOT_FOUND = (
    "Could not find weather information for that location."
)
WEATHER_UNAVAILABLE = (
    "Weather lookup is temporarily unavailable. Please try again later."
)

CURRENCY_PAIR_NOT_FOUND = (
    "Could not fetch an exchange rate for those currencies."
)
CURRENCY_UNAVAILABLE = (
    "Currency conversion is temporarily unavailable. Please try again later."
)

SUMMARY_UNAVAILABLE = (
    "Could not generate a summary right now. Please try again later."
)

TOOL_EXECUTION_FAILED = (
    "Something went wrong while processing your request. Please try again."
)

LLM_UNAVAILABLE = (
    "Could not process your query right now. Please try again later."
)
LLM_CONFIG_UNAVAILABLE = "Query processing is temporarily unavailable."

INVOICE_ORDER_STATUS_NOT_ELIGIBLE = (
    "An invoice can only be generated for confirmed, shipped, or delivered orders."
)

PARAMETER_REQUIRED = "This parameter is required."
PARAMETER_EMPTY = "This parameter must not be empty."

PARAMETER_VALIDATION_MESSAGES = frozenset({PARAMETER_REQUIRED, PARAMETER_EMPTY})

MESSAGE_HTTP_STATUS: dict[str, int] = {
    WEATHER_LOCATION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    WEATHER_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    CURRENCY_PAIR_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    CURRENCY_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    REQUEST_TIMED_OUT: status.HTTP_503_SERVICE_UNAVAILABLE,
    SUMMARY_UNAVAILABLE: status.HTTP_502_BAD_GATEWAY,
    TOOL_EXECUTION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    INVOICE_ORDER_STATUS_NOT_ELIGIBLE: status.HTTP_422_UNPROCESSABLE_ENTITY,
}

ERROR_FIELD_HTTP_STATUS: dict[str, int] = {
    "intent": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "tool": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "service": status.HTTP_503_SERVICE_UNAVAILABLE,
    "summary": status.HTTP_502_BAD_GATEWAY,
    "amount": status.HTTP_400_BAD_REQUEST,
}


def message_for_request_exception(
    exc: requests.RequestException,
    *,
    not_found: str,
    unavailable: str = SERVICE_UNAVAILABLE,
) -> str:
    if isinstance(exc, requests.Timeout):
        return REQUEST_TIMED_OUT

    if isinstance(exc, requests.ConnectionError):
        return unavailable

    response = getattr(exc, "response", None)
    if response is not None:
        status_code = response.status_code
        if status_code in (400, 404):
            return not_found
        if status_code in (401, 403, 429) or status_code >= 500:
            return unavailable

    return unavailable


def http_status_for_tool_result(tool_result: dict) -> int:
    if tool_result.get("success"):
        return status.HTTP_200_OK

    errors = tool_result.get("errors")
    if not errors:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    return http_status_for_tool_errors(errors)


def http_status_for_tool_errors(errors: dict[str, list[str]]) -> int:
    for field, field_status in ERROR_FIELD_HTTP_STATUS.items():
        if field in errors:
            return field_status

    if _has_parameter_validation_error(errors):
        return status.HTTP_400_BAD_REQUEST

    if "order_id" in errors:
        return _http_status_for_order_id_errors(errors["order_id"])

    if "location" in errors:
        return _http_status_for_messages(
            errors["location"],
            default=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if "currency" in errors:
        return _http_status_for_messages(
            errors["currency"],
            default=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if "status" in errors:
        return _http_status_for_status_errors(errors["status"])

    return status.HTTP_400_BAD_REQUEST


def _http_status_for_messages(messages: list[str], *, default: int) -> int:
    for message in messages:
        if message in MESSAGE_HTTP_STATUS:
            return MESSAGE_HTTP_STATUS[message]
    return default


def _http_status_for_order_id_errors(messages: list[str]) -> int:
    for message in messages:
        if message in MESSAGE_HTTP_STATUS:
            return MESSAGE_HTTP_STATUS[message]
        if "does not exist" in message:
            return status.HTTP_404_NOT_FOUND
    return status.HTTP_400_BAD_REQUEST


def _http_status_for_status_errors(messages: list[str]) -> int:
    for message in messages:
        if message in MESSAGE_HTTP_STATUS:
            return MESSAGE_HTTP_STATUS[message]
        if message.startswith("Invalid status."):
            return status.HTTP_422_UNPROCESSABLE_ENTITY
    return status.HTTP_422_UNPROCESSABLE_ENTITY


def _has_parameter_validation_error(errors: dict[str, list[str]]) -> bool:
    return any(
        message in PARAMETER_VALIDATION_MESSAGES
        for messages in errors.values()
        for message in messages
    )
