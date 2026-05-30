from typing import Any

from apps.router.constants.intents import INTENT_PARAMETERS, Intent
from apps.router.tools.base import BaseTool
from apps.router.tools.currency_tool import CurrencyTool
from apps.router.tools.exceptions import ToolExecutionError
from apps.router.tools.invoice_tool import InvoiceTool
from apps.router.tools.order_tool import OrderTool
from apps.router.tools.summary_tool import SummaryTool
from apps.router.tools.weather_tool import WeatherTool


class ToolRouter:
    """Maps classified intents to tools and executes them."""

    def __init__(self, tools: dict[str, BaseTool] | None = None) -> None:
        self._tools = tools or self._default_tools()

    def route(self, intent: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        parameters = parameters or {}

        if intent not in self._tools:
            return {
                "success": False,
                "data": None,
                "errors": {"intent": [f"No tool is registered for intent '{intent}'."]},
                "meta": {"cached": False},
            }

        validation_errors = self._validate_required_parameters(intent, parameters)
        if validation_errors:
            return {
                "success": False,
                "data": None,
                "errors": validation_errors,
                "meta": {"cached": False},
            }

        try:
            return self._tools[intent].execute(parameters)
        except ToolExecutionError as exc:
            return {
                "success": False,
                "data": None,
                "errors": {"tool": [str(exc)]},
                "meta": {"cached": False},
            }

    @staticmethod
    def _default_tools() -> dict[str, BaseTool]:
        return {
            Intent.WEATHER_QUERY: WeatherTool(),
            Intent.CURRENCY_CONVERSION: CurrencyTool(),
            Intent.TEXT_SUMMARY: SummaryTool(),
            Intent.ORDER_LOOKUP: OrderTool(),
            Intent.INVOICE_GENERATION: InvoiceTool(),
        }

    @staticmethod
    def _validate_required_parameters(
        intent: str,
        parameters: dict[str, Any],
    ) -> dict[str, list[str]] | None:
        required_keys = INTENT_PARAMETERS.get(intent, ())
        errors: dict[str, list[str]] = {}

        for key in required_keys:
            value = parameters.get(key)
            if value is None:
                errors[key] = ["This parameter is required."]
                continue
            if isinstance(value, str) and not value.strip():
                errors[key] = ["This parameter must not be empty."]

        return errors or None
