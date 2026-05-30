from typing import Any

from rest_framework import status
from rest_framework.response import Response


def api_response(
    *,
    success: bool,
    data: Any = None,
    errors: Any = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {
            "success": success,
            "data": data,
            "errors": errors,
        },
        status=status_code,
    )
