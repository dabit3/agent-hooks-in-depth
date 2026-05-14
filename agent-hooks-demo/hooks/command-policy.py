#!/usr/bin/env python3
import re
import sys

from common import block, read_payload


payload = read_payload()
tool_input = payload.get("tool_input", {})
command = tool_input.get("command") or payload.get("command") or payload.get("cmd") or ""
normalized = " ".join(command.split())

deny_patterns = [
    (r"\brm\s+-rf\s+(/|\.|~|\$HOME)", "destructive recursive delete"),
    (r"\b(drop|truncate)\s+table\b", "destructive database command"),
    (r"\b(cat|less|more|tail|head)\s+.*\.env\b", "reading env files"),
    (r"(>\s*|tee\s+|cat\s+>\s*)(generated/|fixtures/sensitive/|\.env)", "writing protected paths from the shell"),
    (r"deploy\.py\s+production\b", "production deploy"),
]

for pattern, reason in deny_patterns:
    if re.search(pattern, normalized, flags=re.IGNORECASE):
        block(f"Blocked by command policy: {reason}. Command: {normalized}")

sys.exit(0)
