#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


def read_payload():
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def project_root(payload=None):
    payload = payload or {}
    workspace_roots = payload.get("workspace_roots") or []
    workspace_root = workspace_roots[0] if workspace_roots else None
    for candidate in (
        os.environ.get("AGENT_HOOKS_PROJECT_DIR"),
        os.environ.get("DEVIN_PROJECT_DIR"),
        os.environ.get("CLAUDE_PROJECT_DIR"),
        workspace_root,
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate:
            return Path(candidate).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_inside_root(raw_path, root):
    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    return target, target.relative_to(root).as_posix()


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)
