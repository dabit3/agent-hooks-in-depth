import unittest

from generated.api_client import send_receipt


class ApiClientTests(unittest.TestCase):
    def test_receipt_payload_includes_marketing_opt_in(self):
        receipt = send_receipt("order-123", 2500, marketing_opt_in=True)

        self.assertEqual(receipt, {
            "order_id": "order-123",
            "total_cents": 2500,
            "marketing_opt_in": True,
            "status": "queued",
        })


if __name__ == "__main__":
    unittest.main()
