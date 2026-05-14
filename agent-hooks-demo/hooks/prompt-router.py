#!/usr/bin/env python3
import json

from common import read_payload


payload = read_payload()
prompt = payload.get("prompt", "").lower()

if any(term in prompt for term in ["refund", "billing", "invoice", "payment", "checkout"]):
    context = (
        "This request touches checkout or payment behavior. Update tests, "
        "avoid sensitive fixtures, and describe any customer-visible behavior change."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context
        }
    }))
