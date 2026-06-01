import logging
import time
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.router.llm.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseParseError,
    LLMValidationError,
)
from apps.router.models import QueryHistory
from apps.router.responses import api_response
from apps.router.serializers import QueryRequestSerializer
from apps.router.services import IntentClassifier, ToolRouter
from apps.router.services.tool_router import tool_name_for_intent
from apps.router.services.exceptions import IntentClassificationError
from apps.router.user_errors import (
    LLM_CONFIG_UNAVAILABLE,
    LLM_UNAVAILABLE,
    http_status_for_tool_result,
)

logger = logging.getLogger(__name__)


class QueryAPIView(APIView):
    # ScopedRateThrottle uses Django cache (Redis) to track per-client request counts.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "query"

    def post(self, request):
        started = time.perf_counter()
        audit_payload: dict[str, Any] = {
            "query": "",
            "provider": settings.LLM_PROVIDER,
        }

        try:
            serializer = QueryRequestSerializer(data=request.data)
            if not serializer.is_valid():
                audit_payload["success"] = False
                audit_payload["error"] = serializer.errors
                logger.warning("Query validation failed errors=%s", serializer.errors)
                return api_response(
                    success=False,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            query = serializer.validated_data["query"]
            audit_payload["query"] = query
            logger.info("Query received query=%s", query)

            classification = IntentClassifier().classify(query)
            audit_payload.update(
                {
                    "intent": classification["intent"],
                    "confidence": classification["confidence"],
                    "parameters": classification["parameters"],
                    "tool": tool_name_for_intent(classification["intent"]),
                }
            )

            tool_result = ToolRouter().route(
                classification["intent"],
                classification["parameters"],
            )

            audit_payload.update(
                {
                    "response": tool_result,
                    "success": tool_result["success"],
                    "error": tool_result["errors"] if not tool_result["success"] else None,
                    "cached": tool_result.get("meta", {}).get("cached", False),
                }
            )

            return api_response(
                success=tool_result["success"],
                data=tool_result["data"],
                errors=tool_result["errors"],
                status_code=http_status_for_tool_result(tool_result),
            )
        except IntentClassificationError as exc:
            audit_payload["success"] = False
            audit_payload["error"] = {"classification": [str(exc)]}
            logger.warning("Intent classification failed query=%s error=%s", audit_payload["query"], exc)
            return api_response(
                success=False,
                errors={"classification": [str(exc)]},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except LLMConfigurationError as exc:
            audit_payload["success"] = False
            audit_payload["error"] = {"llm": [str(exc)]}
            logger.error("LLM configuration error: %s", exc)
            return api_response(
                success=False,
                errors={"llm": [LLM_CONFIG_UNAVAILABLE]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (LLMProviderError, LLMResponseParseError, LLMValidationError) as exc:
            audit_payload["success"] = False
            audit_payload["error"] = {"llm": [str(exc)]}
            logger.error("LLM request failed query=%s error=%s", audit_payload["query"], exc)
            return api_response(
                success=False,
                errors={"llm": [LLM_UNAVAILABLE]},
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            audit_payload["processing_time_ms"] = int((time.perf_counter() - started) * 1000)
            QueryHistory.record(**audit_payload)
            log_message = (
                "Query processed success=%s intent=%s tool=%s cached=%s duration_ms=%s query=%s"
            )
            log_args = (
                audit_payload.get("success"),
                audit_payload.get("intent") or "-",
                audit_payload.get("tool") or "-",
                audit_payload.get("cached", False),
                audit_payload.get("processing_time_ms"),
                audit_payload.get("query", ""),
            )
            if audit_payload.get("success"):
                logger.info(log_message, *log_args)
            else:
                logger.warning(log_message, *log_args)
