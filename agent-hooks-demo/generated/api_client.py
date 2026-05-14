GENERATED_NOTICE = "This file stands in for generated client code."


def send_receipt(order_id, total_cents):
    return {
        "order_id": order_id,
        "total_cents": total_cents,
        "status": "queued"
    }
