#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$script_dir/.." && pwd)"

if [[ ! -f "$root/pyproject.toml" ]] || ! grep -q 'name = "agent-hooks-demo"' "$root/pyproject.toml"; then
  echo "Refusing to reset: $root does not look like agent-hooks-demo." >&2
  exit 1
fi

mkdir -p "$root/src" "$root/tests" "$root/generated" "$root/fixtures/sensitive"

cat > "$root/src/__init__.py" <<'PY'
PY

cat > "$root/src/checkout.py" <<'PY'
from dataclasses import dataclass


STANDARD_SHIPPING_CENTS = 599
FREE_SHIPPING_THRESHOLD_CENTS = 5000
DISCOUNT_CODES = {
    "SAVE10": 0.10,
    "VIP20": 0.20,
}


@dataclass(frozen=True)
class LineItem:
    name: str
    unit_price_cents: int
    quantity: int = 1

    def subtotal_cents(self):
        return self.unit_price_cents * self.quantity


def calculate_order_total_cents(items, discount_code=None):
    subtotal = sum(item.subtotal_cents() for item in items)
    discount_rate = DISCOUNT_CODES.get((discount_code or "").upper(), 0)
    discount = round(subtotal * discount_rate)
    shipping = 0 if subtotal >= FREE_SHIPPING_THRESHOLD_CENTS else STANDARD_SHIPPING_CENTS
    return max(0, subtotal - discount) + shipping
PY

cat > "$root/tests/test_checkout.py" <<'PY'
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
PY

cat > "$root/generated/api_client.py" <<'PY'
GENERATED_NOTICE = "This file stands in for generated client code."


def send_receipt(order_id, total_cents):
    return {
        "order_id": order_id,
        "total_cents": total_cents,
        "status": "queued"
    }
PY

cat > "$root/fixtures/sensitive/customer_snapshot.json" <<'JSON'
{
  "customer_id": "demo-customer-001",
  "email": "customer@example.com",
  "last_order_total_cents": 4500
}
JSON

rm -rf "$root/.hook-state" "$root/reports"
rm -f "$root/.env" "$root/.env.local"
find "$root" -name __pycache__ -type d -prune -exec rm -rf {} +

echo "agent-hooks-demo reset to a pristine state."
