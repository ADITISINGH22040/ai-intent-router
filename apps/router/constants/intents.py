from enum import StrEnum


class Intent(StrEnum):
    WEATHER_QUERY = "WEATHER_QUERY"
    CURRENCY_CONVERSION = "CURRENCY_CONVERSION"
    TEXT_SUMMARY = "TEXT_SUMMARY"
    INVOICE_GENERATION = "INVOICE_GENERATION"
    ORDER_LOOKUP = "ORDER_LOOKUP"
    UNKNOWN = "UNKNOWN"


ALLOWED_INTENTS = frozenset(intent.value for intent in Intent)

INTENT_CONFIDENCE_THRESHOLD = 0.65

INTENT_PARAMETERS: dict[str, tuple[str, ...]] = {
    Intent.WEATHER_QUERY: ("location",),
    Intent.CURRENCY_CONVERSION: ("amount", "from_currency", "to_currency"),
    Intent.TEXT_SUMMARY: ("text",),
    Intent.INVOICE_GENERATION: ("order_id",),
    Intent.ORDER_LOOKUP: ("status",),
    Intent.UNKNOWN: (),
}
