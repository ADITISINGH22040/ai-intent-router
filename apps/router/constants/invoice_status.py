from django.db import models


class InvoiceStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    CANCELLED = "cancelled", "Cancelled"
