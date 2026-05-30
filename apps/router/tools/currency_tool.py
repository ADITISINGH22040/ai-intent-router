from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings

from apps.router.tools.base import BaseTool
from apps.router.tools.exceptions import ToolExecutionError
from apps.router.tools.responses import tool_response

EXCHANGERATE_API_PAIR_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{base}/{target}"


class CurrencyTool(BaseTool):
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        api_key = settings.EXCHANGERATE_API_KEY
        if not api_key:
            return tool_response(
                success=False,
                errors={"config": ["EXCHANGERATE_API_KEY is not configured."]},
            )

        try:
            amount = Decimal(str(parameters["amount"]))
        except (InvalidOperation, TypeError):
            return tool_response(
                success=False,
                errors={"amount": ["Amount must be a valid number."]},
            )

        if amount <= 0:
            return tool_response(
                success=False,
                errors={"amount": ["Amount must be greater than zero."]},
            )

        from_currency = str(parameters["from_currency"]).upper()
        to_currency = str(parameters["to_currency"]).upper()

        url = EXCHANGERATE_API_PAIR_URL.format(
            api_key=api_key,
            base=from_currency,
            target=to_currency,
        )

        try:
            response = requests.get(url, timeout=settings.TOOL_REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ToolExecutionError(f"Exchange rate API request failed: {exc}") from exc

        if payload.get("result") != "success":
            return tool_response(
                success=False,
                errors={
                    "currency": [
                        f"Could not fetch exchange rate for {from_currency}/{to_currency}."
                    ]
                },
            )

        try:
            conversion_rate = Decimal(str(payload["conversion_rate"]))
        except (KeyError, InvalidOperation) as exc:
            raise ToolExecutionError(
                "Unexpected response format from Exchange Rate API."
            ) from exc

        converted_amount = (amount * conversion_rate).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

        return tool_response(
            success=True,
            data={
                "amount": str(amount),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "conversion_rate": str(conversion_rate),
                "converted_amount": str(converted_amount),
                "rate_last_updated_utc": payload.get("time_last_update_utc"),
            },
        )
