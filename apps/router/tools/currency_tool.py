from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import logging
import requests
from django.conf import settings

from apps.router.services.cache_service import CURRENCY_RATE_CACHE_TTL, CacheService
from apps.router.tools.base import BaseTool
from apps.router.user_errors import (
    CURRENCY_PAIR_NOT_FOUND,
    CURRENCY_UNAVAILABLE,
    message_for_request_exception,
)

logger = logging.getLogger(__name__)

EXCHANGERATE_API_PAIR_URL = "https://v6.exchangerate-api.com/v6/{api_key}/pair/{base}/{target}"


class CurrencyTool(BaseTool):
    def __init__(self, cache_service: CacheService | None = None) -> None:
        self._cache = cache_service or CacheService()

    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        api_key = settings.EXCHANGERATE_API_KEY
        if not api_key:
            logger.error("Currency conversion unavailable: EXCHANGERATE_API_KEY is not configured")
            return {
                "success": False,
                "data": None,
                "errors": {"service": [CURRENCY_UNAVAILABLE]},
                "meta": {"cached": False},
            }

        try:
            amount = Decimal(str(parameters["amount"]))
        except (InvalidOperation, TypeError):
            return {
                "success": False,
                "data": None,
                "errors": {"amount": ["Amount must be a valid number."]},
                "meta": {"cached": False},
            }

        if amount <= 0:
            return {
                "success": False,
                "data": None,
                "errors": {"amount": ["Amount must be greater than zero."]},
                "meta": {"cached": False},
            }

        from_currency = str(parameters["from_currency"]).upper()
        to_currency = str(parameters["to_currency"]).upper()
        cache_key = self._cache.build_key("currency_rate", from_currency, to_currency)

        cached_rate = self._cache.get(cache_key)
        if cached_rate is not None:
            return self._build_success_response(
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                conversion_rate=Decimal(str(cached_rate["conversion_rate"])),
                rate_last_updated_utc=cached_rate.get("rate_last_updated_utc"),
                cached=True,
            )

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
            logger.warning(
                "Exchange rate request failed pair=%s/%s error=%s",
                from_currency,
                to_currency,
                exc,
            )
            return {
                "success": False,
                "data": None,
                "errors": {
                    "currency": [
                        message_for_request_exception(
                            exc,
                            not_found=CURRENCY_PAIR_NOT_FOUND,
                            unavailable=CURRENCY_UNAVAILABLE,
                        )
                    ]
                },
                "meta": {"cached": False},
            }

        if payload.get("result") != "success":
            logger.warning(
                "Exchange rate lookup failed pair=%s/%s payload=%s",
                from_currency,
                to_currency,
                payload,
            )
            return {
                "success": False,
                "data": None,
                "errors": {"currency": [CURRENCY_PAIR_NOT_FOUND]},
                "meta": {"cached": False},
            }

        try:
            conversion_rate = Decimal(str(payload["conversion_rate"]))
        except (KeyError, InvalidOperation) as exc:
            logger.error(
                "Unexpected exchange rate response format pair=%s/%s error=%s",
                from_currency,
                to_currency,
                exc,
            )
            return {
                "success": False,
                "data": None,
                "errors": {"currency": [CURRENCY_UNAVAILABLE]},
                "meta": {"cached": False},
            }

        rate_last_updated_utc = payload.get("time_last_update_utc")
        self._cache.set(
            cache_key,
            {
                "conversion_rate": str(conversion_rate),
                "rate_last_updated_utc": rate_last_updated_utc,
            },
            CURRENCY_RATE_CACHE_TTL,
        )

        return self._build_success_response(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            conversion_rate=conversion_rate,
            rate_last_updated_utc=rate_last_updated_utc,
            cached=False,
        )

    @staticmethod
    def _build_success_response(
        *,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        conversion_rate: Decimal,
        rate_last_updated_utc: str | None,
        cached: bool,
    ) -> dict[str, Any]:
        converted_amount = (amount * conversion_rate).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

        return {
            "success": True,
            "data": {
                "amount": str(amount),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "conversion_rate": str(conversion_rate),
                "converted_amount": str(converted_amount),
                "rate_last_updated_utc": rate_last_updated_utc,
            },
            "errors": None,
            "meta": {"cached": cached},
        }
