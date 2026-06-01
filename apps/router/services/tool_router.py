import logging
from typing import Any

from apps.router.constants.intents import INTENT_PARAMETERS, Intent
from apps.router.tools.base import BaseTool
from apps.router.tools.currency_tool import CurrencyTool
from apps.router.tools.exceptions import ToolExecutionError
from apps.router.user_errors import PARAMETER_EMPTY, PARAMETER_REQUIRED, TOOL_EXECUTION_FAILED
from apps.router.tools.invoice_tool import InvoiceTool
from apps.router.tools.order_tool import OrderTool
from apps.router.tools.summary_tool import SummaryTool
from apps.router.tools.weather_tool import WeatherTool

INTENT_TOOL_CLASSES: dict[str, type[BaseTool]] = {
    Intent.WEATHER_QUERY: WeatherTool,
    Intent.CURRENCY_CONVERSION: CurrencyTool,
    Intent.TEXT_SUMMARY: SummaryTool,
    Intent.ORDER_LOOKUP: OrderTool,
    Intent.INVOICE_GENERATION: InvoiceTool,
}


logger = logging.getLogger(__name__)


def tool_name_for_intent(intent: str) -> str:
    tool_class = INTENT_TOOL_CLASSES.get(intent)
    return tool_class.__name__ if tool_class else ""


class ToolRouter:
    """Maps classified intents to tools and executes them."""

    def __init__(self, tools: dict[str, BaseTool] | None = None) -> None:
        self._tools = tools or self._default_tools()

    def route(self, intent: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        parameters = parameters or {}

        if intent not in self._tools:
            logger.warning("No tool registered for intent=%s", intent)
            return {
                "success": False,
                "data": None,
                "errors": {"intent": [f"No tool is registered for intent '{intent}'."]},
                "meta": {"cached": False},
            }

        validation_errors = self._validate_required_parameters(intent, parameters)
        if validation_errors:
            logger.warning(
                "Tool parameter validation failed intent=%s errors=%s",
                intent,
                validation_errors,
            )
            return {
                "success": False,
                "data": None,
                "errors": validation_errors,
                "meta": {"cached": False},
            }

        try:
            result = self._tools[intent].execute(parameters)
            logger.info(
                "Tool executed intent=%s tool=%s success=%s cached=%s",
                intent,
                type(self._tools[intent]).__name__,
                result.get("success"),
                result.get("meta", {}).get("cached", False),
            )
            return result
        except ToolExecutionError as exc:
            logger.warning("Tool execution failed intent=%s error=%s", intent, exc)
            return {
                "success": False,
                "data": None,
                "errors": {"tool": [TOOL_EXECUTION_FAILED]},
                "meta": {"cached": False},
            }

    @staticmethod
    def _default_tools() -> dict[str, BaseTool]:
        return {intent: tool_cls() for intent, tool_cls in INTENT_TOOL_CLASSES.items()}

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
                errors[key] = [PARAMETER_REQUIRED]
                continue
            if isinstance(value, str) and not value.strip():
                errors[key] = [PARAMETER_EMPTY]

        return errors or None
