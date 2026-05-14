#!/usr/bin/env python3
import json
import time

from common import project_root, read_payload


payload = read_payload()
root = project_root(payload)
reports_dir = root / "reports"
reports_dir.mkdir(exist_ok=True)

record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "event": "SessionEnd",
    "session_id": payload.get("session_id"),
    "reason": payload.get("reason", "unknown"),
    "transcript_path": payload.get("transcript_path")
}

with (reports_dir / "session-audit.log").open("a") as log:
    log.write(json.dumps(record) + "\n")
