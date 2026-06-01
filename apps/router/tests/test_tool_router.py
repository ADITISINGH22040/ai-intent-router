from django.test import SimpleTestCase, TestCase

from apps.router.constants.intents import Intent
from apps.router.constants.order_status import OrderStatus
from apps.router.models import Customer, Invoice, Order
from apps.router.services.tool_router import ToolRouter
from apps.router.tools.base import BaseTool
from apps.router.tools.invoice_tool import InvoiceTool


class StubTool(BaseTool):
    def __init__(self, response: dict) -> None:
        self.response = response
        self.received_parameters = None

    def execute(self, parameters: dict) -> dict:
        self.received_parameters = parameters
        return self.response


def stub_success(data: dict) -> dict:
    return {
        "success": True,
        "data": data,
        "errors": None,
        "meta": {"cached": False},
    }


class ToolRouterTests(SimpleTestCase):
    def test_validates_missing_required_parameters(self):
        router = ToolRouter(
            tools={Intent.WEATHER_QUERY: StubTool(stub_success({}))}
        )
        result = router.route(Intent.WEATHER_QUERY, {})

        self.assertFalse(result["success"])
        self.assertIn("location", result["errors"])

    def test_rejects_unregistered_intent(self):
        router = ToolRouter(tools={Intent.WEATHER_QUERY: StubTool(stub_success({}))})
        result = router.route(Intent.UNKNOWN, {})

        self.assertFalse(result["success"])
        self.assertIn("intent", result["errors"])

    def test_executes_mapped_tool(self):
        stub = StubTool(stub_success({"ok": True}))
        router = ToolRouter(tools={Intent.TEXT_SUMMARY: stub})
        parameters = {"text": "hello world"}

        result = router.route(Intent.TEXT_SUMMARY, parameters)

        self.assertTrue(result["success"])
        self.assertFalse(result["meta"]["cached"])
        self.assertEqual(stub.received_parameters, parameters)


class InvoiceToolTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(name="Jane Doe", email="jane@example.com")
        self.order = Order.objects.create(
            customer=customer,
            status=OrderStatus.CONFIRMED,
            total_amount="150.00",
            currency="USD",
        )

    def test_invoice_is_idempotent(self):
        tool = InvoiceTool()
        first = tool.execute({"order_id": self.order.id})
        second = tool.execute({"order_id": self.order.id})

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertFalse(first["meta"]["cached"])
        self.assertFalse(second["meta"]["cached"])
        self.assertTrue(first["data"]["created"])
        self.assertFalse(second["data"]["created"])
        self.assertEqual(
            first["data"]["invoice"]["invoice_number"],
            second["data"]["invoice"]["invoice_number"],
        )
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)

    def test_rejects_ineligible_order_statuses(self):
        tool = InvoiceTool()
        ineligible_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
        ]

        for index, status in enumerate(ineligible_statuses):
            with self.subTest(status=status):
                order = Order.objects.create(
                    customer=self.order.customer,
                    status=status,
                    total_amount="50.00",
                    currency="USD",
                )
                result = tool.execute({"order_id": order.id})

                self.assertFalse(result["success"])
                self.assertIn("status", result["errors"])
                self.assertEqual(Invoice.objects.filter(order=order).count(), 0)

    def test_allows_shipped_and_delivered_orders(self):
        tool = InvoiceTool()

        for status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            with self.subTest(status=status):
                order = Order.objects.create(
                    customer=self.order.customer,
                    status=status,
                    total_amount="75.00",
                    currency="USD",
                )
                result = tool.execute({"order_id": order.id})

                self.assertTrue(result["success"])
                self.assertTrue(result["data"]["created"])
                self.assertEqual(Invoice.objects.filter(order=order).count(), 1)
