from rest_framework import status
from rest_framework.views import APIView

from apps.router.responses import api_response
from apps.router.serializers import QueryRequestSerializer


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
        return api_response(
            success=True,
            data={
                "query": query,
                "intent": None,
                "response": "Query received. LLM processing is not implemented yet.",
            },
        )
