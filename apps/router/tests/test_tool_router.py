from django.test import SimpleTestCase, TestCase

from apps.router.constants.intents import Intent
from apps.router.constants.order_status import OrderStatus
from apps.router.models import Customer, Invoice, Order
from apps.router.services.tool_router import ToolRouter
from apps.router.tools.base import BaseTool
from apps.router.tools.invoice_tool import InvoiceTool
from apps.router.tools.responses import tool_response


class StubTool(BaseTool):
    def __init__(self, response: dict) -> None:
        self.response = response
        self.received_parameters = None

    def execute(self, parameters: dict) -> dict:
        self.received_parameters = parameters
        return self.response


class ToolRouterTests(SimpleTestCase):
    def test_validates_missing_required_parameters(self):
        router = ToolRouter(
            tools={Intent.WEATHER_QUERY: StubTool(tool_response(success=True, data={}))}
        )
        result = router.route(Intent.WEATHER_QUERY, {})

        self.assertFalse(result["success"])
        self.assertIn("location", result["errors"])

    def test_rejects_unregistered_intent(self):
        router = ToolRouter(tools={Intent.WEATHER_QUERY: StubTool(tool_response(success=True, data={}))})
        result = router.route(Intent.UNKNOWN, {})

        self.assertFalse(result["success"])
        self.assertIn("intent", result["errors"])

    def test_executes_mapped_tool(self):
        stub = StubTool(tool_response(success=True, data={"ok": True}))
        router = ToolRouter(tools={Intent.TEXT_SUMMARY: stub})
        parameters = {"text": "hello world"}

        result = router.route(Intent.TEXT_SUMMARY, parameters)

        self.assertTrue(result["success"])
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
        self.assertTrue(first["data"]["created"])
        self.assertFalse(second["data"]["created"])
        self.assertEqual(
            first["data"]["invoice"]["invoice_number"],
            second["data"]["invoice"]["invoice_number"],
        )
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)
