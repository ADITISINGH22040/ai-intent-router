from typing import Any

import logging
import requests
from django.conf import settings

from apps.router.services.cache_service import WEATHER_CACHE_TTL, CacheService
from apps.router.tools.base import BaseTool
from apps.router.user_errors import (
    WEATHER_LOCATION_NOT_FOUND,
    WEATHER_UNAVAILABLE,
    message_for_request_exception,
)

logger = logging.getLogger(__name__)

WEATHERAPI_CURRENT_URL = "https://api.weatherapi.com/v1/current.json"


class WeatherTool(BaseTool):
    def __init__(self, cache_service: CacheService | None = None) -> None:
        self._cache = cache_service or CacheService()

    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        api_key = settings.WEATHERAPI_API_KEY
        if not api_key:
            logger.error("Weather lookup unavailable: WEATHERAPI_API_KEY is not configured")
            return {
                "success": False,
                "data": None,
                "errors": {"service": [WEATHER_UNAVAILABLE]},
                "meta": {"cached": False},
            }

        location = str(parameters["location"]).strip()
        cache_key = self._cache.build_key("weather", location)

        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return {
                "success": True,
                "data": cached_data,
                "errors": None,
                "meta": {"cached": True},
            }

        timeout = settings.TOOL_REQUEST_TIMEOUT

        try:
            response = requests.get(
                WEATHERAPI_CURRENT_URL,
                params={"key": api_key, "q": location},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning("Weather lookup request failed location=%s error=%s", location, exc)
            return {
                "success": False,
                "data": None,
                "errors": {
                    "location": [
                        message_for_request_exception(
                            exc,
                            not_found=WEATHER_LOCATION_NOT_FOUND,
                            unavailable=WEATHER_UNAVAILABLE,
                        )
                    ]
                },
                "meta": {"cached": False},
            }

        if payload.get("error"):
            logger.warning(
                "Weather lookup returned error location=%s payload=%s",
                location,
                payload.get("error"),
            )
            return {
                "success": False,
                "data": None,
                "errors": {"location": [WEATHER_LOCATION_NOT_FOUND]},
                "meta": {"cached": False},
            }

        try:
            place = payload["location"]
            current = payload["current"]
            condition = current.get("condition", {})
        except (KeyError, TypeError) as exc:
            logger.error("Unexpected weather response format location=%s error=%s", location, exc)
            return {
                "success": False,
                "data": None,
                "errors": {"location": [WEATHER_UNAVAILABLE]},
                "meta": {"cached": False},
            }

        data = {
            "location": location,
            "resolved_name": place.get("name"),
            "temperature_c": current.get("temp_c"),
            "condition": condition.get("text"),
        }
        self._cache.set(cache_key, data, WEATHER_CACHE_TTL)
        return {
            "success": True,
            "data": data,
            "errors": None,
            "meta": {"cached": False},
        }
