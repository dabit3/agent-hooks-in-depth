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
