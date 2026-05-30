from typing import Any

import requests
from django.conf import settings

from apps.router.tools.base import BaseTool
from apps.router.tools.exceptions import ToolExecutionError
from apps.router.tools.responses import tool_response

WEATHERAPI_CURRENT_URL = "https://api.weatherapi.com/v1/current.json"


class WeatherTool(BaseTool):
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        api_key = settings.WEATHERAPI_API_KEY
        if not api_key:
            return tool_response(
                success=False,
                errors={"config": ["WEATHERAPI_API_KEY is not configured."]},
            )

        location = parameters["location"]
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
            return tool_response(
                success=False,
                errors={"location": [message]},
            )

        try:
            place = payload["location"]
            current = payload["current"]
            condition = current.get("condition", {})
        except (KeyError, TypeError) as exc:
            raise ToolExecutionError("Unexpected response format from Weather API.") from exc

        return tool_response(
            success=True,
            data={
                "location": location,
                "resolved_name": place.get("name"),
                "region": place.get("region"),
                "country": place.get("country"),
                "latitude": place.get("lat"),
                "longitude": place.get("lon"),
                "localtime": place.get("localtime"),
                "temperature_c": current.get("temp_c"),
                "temperature_f": current.get("temp_f"),
                "feelslike_c": current.get("feelslike_c"),
                "humidity": current.get("humidity"),
                "wind_kph": current.get("wind_kph"),
                "condition": condition.get("text"),
                "condition_icon": condition.get("icon"),
            },
        )
