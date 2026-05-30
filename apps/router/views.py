from rest_framework import status
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


class QueryAPIView(APIView):
    def post(self, request):
        serializer = QueryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        query = serializer.validated_data["query"]

        try:
            classification = IntentClassifier().classify(query)
            tool_result = ToolRouter().route(
                classification["intent"],
                classification["parameters"],
            )
        except IntentClassificationError as exc:
            return api_response(
                success=False,
                errors={"classification": [str(exc)]},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except LLMConfigurationError as exc:
            return api_response(
                success=False,
                errors={"llm": [str(exc)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (LLMProviderError, LLMResponseParseError, LLMValidationError) as exc:
            return api_response(
                success=False,
                errors={"llm": [str(exc)]},
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return api_response(
            success=True,
            data={
                "query": query,
                "classification": classification,
                "tool_result": tool_result,
            },
        )
