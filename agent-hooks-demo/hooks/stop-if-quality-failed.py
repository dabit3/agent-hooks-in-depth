#!/usr/bin/env python3
import json
import sys

from common import block, project_root, read_payload


payload = read_payload()
root = project_root(payload)
state_file = root / ".hook-state" / "last_quality_gate.json"

if not state_file.exists():
    sys.exit(0)

state = json.loads(state_file.read_text())
if state.get("status") == "failed":
    block("Quality gate failed. Fix the tests before saying the task is complete.")
