import unittest

from src.checkout import LineItem, calculate_order_total_cents


class CheckoutTests(unittest.TestCase):
    def test_adds_shipping_below_free_shipping_threshold(self):
        total = calculate_order_total_cents([
            LineItem(name="Notebook", unit_price_cents=1200, quantity=2)
        ])

        self.assertEqual(total, 2999)

    def test_waives_shipping_at_free_shipping_threshold(self):
        total = calculate_order_total_cents([
            LineItem(name="Backpack", unit_price_cents=5000)
        ])

        self.assertEqual(total, 5000)

    def test_applies_known_discount_code_before_shipping(self):
        total = calculate_order_total_cents([
            LineItem(name="Backpack", unit_price_cents=5000)
        ], discount_code="save10")

        self.assertEqual(total, 4500)


if __name__ == "__main__":
    unittest.main()
