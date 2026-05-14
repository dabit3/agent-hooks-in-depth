#!/usr/bin/env python3
import json


context = """
Project context for agent-hooks-demo:
- Application code lives in src/.
- Tests live in tests/.
- Run `python3 -m unittest discover -s tests` before calling work complete.
- Do not edit generated/, fixtures/sensitive/, .env, .env.local, .git, or files outside the repo.
- Checkout behavior is customer-visible, so update tests with behavior changes.
""".strip()

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context
    }
}))
