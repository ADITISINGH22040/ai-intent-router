from typing import Any

import requests
from django.conf import settings

from apps.router.services.cache_service import WEATHER_CACHE_TTL, CacheService
from apps.router.tools.base import BaseTool
from apps.router.tools.exceptions import ToolExecutionError

WEATHERAPI_CURRENT_URL = "https://api.weatherapi.com/v1/current.json"


class WeatherTool(BaseTool):
    def __init__(self, cache_service: CacheService | None = None) -> None:
        self._cache = cache_service or CacheService()

    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        api_key = settings.WEATHERAPI_API_KEY
        if not api_key:
            return {
                "success": False,
                "data": None,
                "errors": {"config": ["WEATHERAPI_API_KEY is not configured."]},
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
            raise ToolExecutionError(f"Weather API request failed: {exc}") from exc

        if payload.get("error"):
            message = payload["error"].get("message", "Weather API returned an error.")
            return {
                "success": False,
                "data": None,
                "errors": {"location": [message]},
                "meta": {"cached": False},
            }

        try:
            place = payload["location"]
            current = payload["current"]
            condition = current.get("condition", {})
        except (KeyError, TypeError) as exc:
            raise ToolExecutionError("Unexpected response format from Weather API.") from exc

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
