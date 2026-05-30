from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.router.constants.invoice_status import InvoiceStatus
from apps.router.models import Invoice, Order
from apps.router.tools.base import BaseTool


class InvoiceTool(BaseTool):
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        try:
            order_id = int(parameters["order_id"])
        except (TypeError, ValueError):
            return {
                "success": False,
                "data": None,
                "errors": {"order_id": ["order_id must be a valid integer."]},
                "meta": {"cached": False},
            }

        try:
            order = Order.objects.select_related("customer", "invoice").get(pk=order_id)
        except Order.DoesNotExist:
            return {
                "success": False,
                "data": None,
                "errors": {"order_id": [f"Order {order_id} does not exist."]},
                "meta": {"cached": False},
            }

        existing_invoice = getattr(order, "invoice", None)
        if existing_invoice is not None:
            return {
                "success": True,
                "data": {
                    "created": False,
                    "invoice": self._serialize_invoice(existing_invoice),
                },
                "errors": None,
                "meta": {"cached": False},
            }

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            existing_invoice = Invoice.objects.filter(order=order).first()
            if existing_invoice:
                return {
                    "success": True,
                    "data": {
                        "created": False,
                        "invoice": self._serialize_invoice(existing_invoice),
                    },
                    "errors": None,
                    "meta": {"cached": False},
                }

            invoice = Invoice.objects.create(
                invoice_number=self._build_invoice_number(order),
                order=order,
                status=InvoiceStatus.GENERATED,
                total_amount=order.total_amount,
                currency=order.currency,
                generated_at=timezone.now(),
            )

        return {
            "success": True,
            "data": {
                "created": True,
                "invoice": self._serialize_invoice(invoice),
            },
            "errors": None,
            "meta": {"cached": False},
        }

    @staticmethod
    def _build_invoice_number(order: Order) -> str:
        return f"INV-{order.pk:06d}"

    @staticmethod
    def _serialize_invoice(invoice: Invoice) -> dict[str, Any]:
        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "status": invoice.status,
            "total_amount": str(invoice.total_amount),
            "currency": invoice.currency,
            "generated_at": invoice.generated_at.isoformat() if invoice.generated_at else None,
            "created_at": invoice.created_at.isoformat(),
        }
