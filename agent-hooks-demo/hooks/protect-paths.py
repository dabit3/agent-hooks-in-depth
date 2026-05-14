#!/usr/bin/env python3
import sys

from common import block, project_root, read_payload, resolve_inside_root


def candidate_paths(tool_input):
    values = []
    for key in ("file_path", "filePath", "path", "target_file", "targetPath"):
        value = tool_input.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ("operation", "change", "fileChange"):
        value = tool_input.get(key)
        if isinstance(value, dict):
            nested_path = value.get("path") or value.get("file_path") or value.get("filePath")
            if isinstance(nested_path, str):
                values.append(nested_path)
    for key in ("files", "paths"):
        value = tool_input.get(key)
        if isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    for key in ("changes", "operations", "edits"):
        value = tool_input.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested_path = item.get("path") or item.get("file_path") or item.get("filePath")
                    if isinstance(nested_path, str):
                        values.append(nested_path)
    patch = tool_input.get("patch") or tool_input.get("diff") or tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or ""
    if isinstance(patch, str):
        for line in patch.splitlines():
            for prefix in ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: "):
                if line.startswith(prefix):
                    values.append(line.removeprefix(prefix).strip())
            if line.startswith(("+++ b/", "--- b/")):
                values.append(line[6:].strip())
    return values


payload = read_payload()
root = project_root(payload)
tool_input = payload.get("tool_input", {})
raw_paths = candidate_paths({**payload, **tool_input})

if not raw_paths:
    sys.exit(0)

protected_prefixes = ("generated/", "fixtures/sensitive/", ".git/")
protected_exact = {".env", ".env.local"}

for raw_path in raw_paths:
    try:
        target, rel = resolve_inside_root(raw_path, root)
    except ValueError:
        block(f"{raw_path} resolves outside the repo.")

    if rel in protected_exact or any(rel.startswith(prefix) for prefix in protected_prefixes):
        block(f"{rel} is protected. Use application code or tests instead.")
