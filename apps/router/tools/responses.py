from typing import Any


def tool_response(
    *,
    success: bool,
    data: Any = None,
    errors: Any = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "data": data,
        "errors": errors,
    }
