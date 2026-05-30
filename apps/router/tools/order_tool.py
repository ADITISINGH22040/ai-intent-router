from typing import Any

from apps.router.constants.order_status import OrderStatus
from apps.router.models import Order
from apps.router.tools.base import BaseTool
from apps.router.tools.responses import tool_response


class OrderTool(BaseTool):
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        status_filter = str(parameters["status"]).lower()

        if status_filter not in OrderStatus.values:
            return tool_response(
                success=False,
                errors={
                    "status": [
                        f"Invalid status. Allowed values: {', '.join(OrderStatus.values)}."
                    ]
                },
            )

        queryset = (
            Order.objects.filter(status=status_filter)
            .select_related("customer")
            .order_by("-created_at")
        )
        orders = list(queryset[:50])

        return tool_response(
            success=True,
            data={
                "status": status_filter,
                "count": queryset.count(),
                "orders": [self._serialize_order(order) for order in orders],
            },
        )

    @staticmethod
    def _serialize_order(order: Order) -> dict[str, Any]:
        return {
            "id": order.id,
            "customer_name": order.customer.name,
            "customer_email": order.customer.email,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "created_at": order.created_at.isoformat(),
        }
