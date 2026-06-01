import json
import logging
from typing import Any

from rest_framework import status
from rest_framework.views import exception_handler

from apps.router.models import QueryHistory
from apps.router.responses import api_response

RATE_LIMIT_MESSAGE = "Rate limit exceeded. Please try again later."

logger = logging.getLogger(__name__)


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


def rate_limit_response():
    return api_response(
        success=False,
        errors={"rate_limit": [RATE_LIMIT_MESSAGE]},
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def api_exception_handler(exc: Exception, context: dict[str, Any]):
    from django.conf import settings

    from rest_framework.exceptions import Throttled

    if isinstance(exc, Throttled):
        request = context.get("request")
        client_ip = getattr(request, "META", {}).get("REMOTE_ADDR", "unknown")
        logger.warning(
            "Rate limit exceeded client_ip=%s query=%s",
            client_ip,
            _extract_query(request)[:120],
        )
        QueryHistory.record(
            query=_extract_query(request),
            success=False,
            error={"rate_limit": [RATE_LIMIT_MESSAGE]},
            provider=settings.LLM_PROVIDER,
            processing_time_ms=0,
        )
        return rate_limit_response()

    return exception_handler(exc, context)
