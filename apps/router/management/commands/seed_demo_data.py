from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.router.constants.invoice_status import InvoiceStatus
from apps.router.constants.order_status import OrderStatus
from apps.router.models import Customer, Invoice, Order, OrderItem


class Command(BaseCommand):
    help = "Load demo customers, orders, order items, and invoices for local development."

    def handle(self, *args, **options):
        created_counts = {"customers": 0, "orders": 0, "items": 0, "invoices": 0}

        def track_created(key: str, created: bool) -> None:
            if created:
                created_counts[key] += 1

        jane, created = Customer.objects.get_or_create(
            email="jane@example.com",
            defaults={"name": "Jane Doe"},
        )
        track_created("customers", created)

        john, created = Customer.objects.get_or_create(
            email="john@example.com",
            defaults={"name": "John Smith"},
        )
        track_created("customers", created)

        shipped_order, created = Order.objects.get_or_create(
            customer=jane,
            status=OrderStatus.SHIPPED,
            total_amount=Decimal("150.00"),
            defaults={"currency": "USD"},
        )
        track_created("orders", created)

        pending_order, created = Order.objects.get_or_create(
            customer=jane,
            status=OrderStatus.PENDING,
            total_amount=Decimal("80.00"),
            defaults={"currency": "USD"},
        )
        track_created("orders", created)

        confirmed_order, created = Order.objects.get_or_create(
            customer=john,
            status=OrderStatus.CONFIRMED,
            total_amount=Decimal("95.00"),
            defaults={"currency": "USD"},
        )
        track_created("orders", created)

        seed_items = [
            (shipped_order, "Widget", 2, Decimal("75.00"), Decimal("150.00")),
            (pending_order, "Notebook", 4, Decimal("20.00"), Decimal("80.00")),
            (confirmed_order, "USB Cable", 1, Decimal("95.00"), Decimal("95.00")),
        ]
        for order, item_name, quantity, unit_price, total_price in seed_items:
            _, created = OrderItem.objects.get_or_create(
                order=order,
                item_name=item_name,
                defaults={
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                },
            )
            track_created("items", created)

        _, created = Invoice.objects.get_or_create(
            order=shipped_order,
            defaults={
                "invoice_number": f"INV-{shipped_order.pk:06d}",
                "status": InvoiceStatus.GENERATED,
                "total_amount": shipped_order.total_amount,
                "currency": shipped_order.currency,
                "generated_at": timezone.now(),
            },
        )
        track_created("invoices", created)

        total_customers = Customer.objects.filter(
            email__in=["jane@example.com", "john@example.com"]
        ).count()
        total_orders = Order.objects.filter(
            customer__in=[jane, john],
            total_amount__in=[Decimal("150.00"), Decimal("80.00"), Decimal("95.00")],
        ).count()
        total_items = OrderItem.objects.filter(order__customer__in=[jane, john]).count()
        total_invoices = Invoice.objects.filter(order=shipped_order).count()

        created_total = sum(created_counts.values())
        if created_total:
            self.stdout.write(
                self.style.SUCCESS(
                    "Demo data seeded: "
                    f"{created_counts['customers']} customers, "
                    f"{created_counts['orders']} orders, "
                    f"{created_counts['items']} items, "
                    f"{created_counts['invoices']} invoices created."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Demo data already present — no new records created."
                )
            )

        self.stdout.write(
            f"Database totals: {total_customers} customers, "
            f"{total_orders} orders, {total_items} items, {total_invoices} invoices."
        )
