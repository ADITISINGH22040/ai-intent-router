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
from apps.router.responses import api_response
from apps.router.serializers import QueryRequestSerializer
from apps.router.services import IntentClassifier, ToolRouter
from apps.router.services.exceptions import IntentClassificationError
from apps.router.services.history_service import HistoryService


class QueryAPIView(APIView):
    # ScopedRateThrottle uses Django cache (Redis) to track per-client request counts.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "query"

    def post(self, request):
        started = time.perf_counter()
        history: dict[str, Any] = {
            "query": "",
            "provider": settings.LLM_PROVIDER,
        }

        try:
            serializer = QueryRequestSerializer(data=request.data)
            if not serializer.is_valid():
                history["success"] = False
                history["error"] = serializer.errors
                return api_response(
                    success=False,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            query = serializer.validated_data["query"]
            history["query"] = query

            classification = IntentClassifier().classify(query)
            history.update(
                {
                    "intent": classification["intent"],
                    "confidence": classification["confidence"],
                    "parameters": classification["parameters"],
                    "tool": HistoryService.tool_name_for_intent(classification["intent"]),
                }
            )

            tool_result = ToolRouter().route(
                classification["intent"],
                classification["parameters"],
            )

            history.update(
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
            )
        except IntentClassificationError as exc:
            history["success"] = False
            history["error"] = {"classification": [str(exc)]}
            return api_response(
                success=False,
                errors={"classification": [str(exc)]},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except LLMConfigurationError as exc:
            history["success"] = False
            history["error"] = {"llm": [str(exc)]}
            return api_response(
                success=False,
                errors={"llm": [str(exc)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (LLMProviderError, LLMResponseParseError, LLMValidationError) as exc:
            history["success"] = False
            history["error"] = {"llm": [str(exc)]}
            return api_response(
                success=False,
                errors={"llm": [str(exc)]},
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            history["processing_time_ms"] = int((time.perf_counter() - started) * 1000)
            HistoryService.save(**history)
