from typing import Any

from django.db import models

from apps.router.constants.invoice_status import InvoiceStatus
from apps.router.constants.order_status import OrderStatus
from apps.router.constants.query_status import QueryStatus


class QueryHistory(models.Model):
    query_text = models.TextField()
    llm_output = models.JSONField(blank=True, null=True)
    tool_response = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=QueryStatus.choices,
        default=QueryStatus.PENDING,
    )
    processing_time_ms = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "query_history"
        ordering = ["-created_at"]
        verbose_name_plural = "query histories"

    def __str__(self):
        preview = self.query_text[:50]
        if len(self.query_text) > 50:
            preview += "..."
        return f"Query {self.pk}: {preview}"

    @classmethod
    def record(
        cls,
        *,
        query: str,
        intent: str = "",
        confidence: float | None = None,
        parameters: dict[str, Any] | None = None,
        response: Any = None,
        success: bool = False,
        error: Any = None,
        cached: bool = False,
        provider: str = "",
        tool: str = "",
        processing_time_ms: int | None = None,
    ) -> "QueryHistory":
        llm_output: dict[str, Any] | None = None
        if intent:
            llm_output = {
                "intent": intent,
                "confidence": confidence,
                "parameters": parameters,
                "provider": provider,
            }
        elif error:
            llm_output = {"error": error}

        tool_response = response
        if tool or cached or isinstance(tool_response, dict):
            payload = dict(tool_response) if isinstance(tool_response, dict) else {}
            payload.pop("meta", None)
            if tool:
                payload["tool"] = tool
            if cached:
                payload["cached"] = cached
            tool_response = payload or tool_response

        return cls.objects.create(
            query_text=query,
            llm_output=llm_output,
            tool_response=tool_response,
            status=QueryStatus.COMPLETED if success else QueryStatus.FAILED,
            processing_time_ms=processing_time_ms,
        )


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Order(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.pk} ({self.status}) - {self.customer}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="order_id",
    )
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.item_name} x{self.quantity} (Order {self.order_id})"


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=64, unique=True)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="invoice",
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.GENERATED,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    generated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.status})"
