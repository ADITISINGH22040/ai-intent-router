from typing import Any

from apps.router.constants.intents import Intent
from apps.router.constants.query_status import QueryStatus
from apps.router.models import QueryHistory

INTENT_TOOL_NAMES = {
    Intent.WEATHER_QUERY: "WeatherTool",
    Intent.CURRENCY_CONVERSION: "CurrencyTool",
    Intent.TEXT_SUMMARY: "SummaryTool",
    Intent.ORDER_LOOKUP: "OrderTool",
    Intent.INVOICE_GENERATION: "InvoiceTool",
}


class HistoryService:
    @staticmethod
    def save(
        *,
        query: str,
        intent: str = "",
        confidence: float | None = None,
        parameters: dict[str, Any] | None = None,
        response: Any = None,
        success: bool = False,
        error: Any = None,
        cached: bool = False,
        provider: str = "",
        tool: str = "",
        processing_time_ms: int | None = None,
    ) -> QueryHistory:
        llm_output: dict[str, Any] | None = None
        if intent:
            llm_output = {
                "intent": intent,
                "confidence": confidence,
                "parameters": parameters,
                "provider": provider,
            }
        elif error:
            llm_output = {"error": error}

        tool_response = response
        if tool or cached:
            payload = dict(tool_response) if isinstance(tool_response, dict) else {}
            if tool:
                payload["tool"] = tool
            if cached:
                payload["cached"] = cached
            tool_response = payload or tool_response

        return QueryHistory.objects.create(
            query_text=query,
            llm_output=llm_output,
            tool_response=tool_response,
            status=QueryStatus.COMPLETED if success else QueryStatus.FAILED,
            processing_time_ms=processing_time_ms,
        )

    @staticmethod
    def tool_name_for_intent(intent: str) -> str:
        return INTENT_TOOL_NAMES.get(intent, "")
