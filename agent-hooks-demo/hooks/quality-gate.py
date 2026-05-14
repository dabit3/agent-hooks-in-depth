#!/usr/bin/env python3
import json
import subprocess
import sys
import time

from common import block, project_root, read_payload


payload = read_payload()
root = project_root(payload)
raw_path = payload.get("tool_input", {}).get("file_path") or payload.get("tool_input", {}).get("path") or ""

if raw_path and not raw_path.endswith((".py", ".json")):
    sys.exit(0)

state_dir = root / ".hook-state"
reports_dir = root / "reports"
state_dir.mkdir(exist_ok=True)
reports_dir.mkdir(exist_ok=True)

started = time.time()
result = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
    cwd=root,
    text=True,
    capture_output=True,
    timeout=60,
)

record = {
    "status": "passed" if result.returncode == 0 else "failed",
    "exit_code": result.returncode,
    "edited_file": raw_path,
    "duration_seconds": round(time.time() - started, 2),
    "stdout_tail": result.stdout[-4000:],
    "stderr_tail": result.stderr[-4000:]
}

(state_dir / "last_quality_gate.json").write_text(json.dumps(record, indent=2) + "\n")
with (reports_dir / "hook-audit.log").open("a") as log:
    log.write(f"quality_gate status={record['status']} file={raw_path}\n")

if record["status"] == "failed":
    block("Quality gate failed. Inspect .hook-state/last_quality_gate.json and fix the failure before finishing.")
