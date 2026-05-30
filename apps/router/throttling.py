import json
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

RATE_LIMIT_MESSAGE = "Rate limit exceeded. Please try again later."


def _extract_query(request: Any) -> str:
    if request is None:
        return ""

    try:
        return str(request.data.get("query", "") or "")
    except Exception:
        pass

    try:
        body = request.body
        if body:
            payload = json.loads(body)
            if isinstance(payload, dict):
                return str(payload.get("query", "") or "")
    except Exception:
        pass

    return ""


def rate_limit_response() -> Response:
    return Response(
        {
            "success": False,
            "message": RATE_LIMIT_MESSAGE,
            "data": None,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    from django.conf import settings

    from apps.router.services.history_service import HistoryService
    from rest_framework.exceptions import Throttled

    if isinstance(exc, Throttled):
        request = context.get("request")
        HistoryService.save(
            query=_extract_query(request),
            success=False,
            error={"rate_limit": [RATE_LIMIT_MESSAGE]},
            provider=settings.LLM_PROVIDER,
            processing_time_ms=0,
        )
        return rate_limit_response()

    return exception_handler(exc, context)
