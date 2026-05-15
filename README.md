# Agent Hooks: Deterministic Control for Agent Workflows

![header](./header.png)

Hooks make the agent workflow programmable. If you've ever reminded an agent twice to avoid a file, run a test, or follow a release rule, you have already found a use case for hooks.

Hooks enable this by attaching user-defined handlers to specific lifecycle points in an agent session. A handler receives event data, can be narrowed by an optional matcher or filter, and can return context, make a decision, or perform a side effect.

The main value proposition is deterministic control: rules already captured in scripts, tests, policy checks, and runbooks can run at known lifecycle points in the agent workflow instead of depending on the model to remember and voluntarily follow them.

Use prompts for guidance. Use hooks for behavior that should run every time. For example, a project instruction can say “do not edit generated files,” but a `PreToolUse` hook can inspect the attempted edit and block it before it happens; a project instruction can say “run tests before finishing,” but a `PostToolUse` hook can run the test suite after edits and a `Stop` hook can prevent completion when the last test run failed.

This post uses six lifecycle points that cover the main flow developers usually need first, using the canonical hook names as shorthand:

- `SessionStart`: Load session context, such as project conventions, active constraints, environment facts, or a relevant runbook when the session starts.
- `UserPromptSubmit`: Inspect the user prompt before the model sees it, then add context, route the request, or block a known-bad prompt.
- `PreToolUse`: Inspect a tool call before it runs and block, approve, or modify behavior based on project policy.
- `PostToolUse`: Run validation after a successful tool call, such as tests, formatting, scanning, logging, or state capture.
- `Stop`: Check whether the agent should be allowed to finish the turn.
- `SessionEnd`: Write final logs, flush metrics, export a summary, or clean up temporary state when the session ends.

Other hooks exist and are worth learning later, but these are a good starting set because they cover the main flow: start the session, receive the prompt, attempt an action, validate the action, finish the turn, and close the session.

![Session lifecycle](./session_lifecycle.png)

## The operating model

The simplest mental model is:

```text
event → optional matcher/filter → handler → outcome
```

![Hook lifecycle](./hook_lifecycle.png)

An **event** is a lifecycle moment, such as `PreToolUse` or `Stop`.

An optional **matcher or filter** narrows when the hook should run, such as only for shell commands or only for file edits. When no matcher is needed, the handler runs for that lifecycle event.

A **handler** is the action the hook takes: depending on the runtime, that might be a shell command, HTTP request, MCP tool call, LLM prompt, or subagent. This demo uses command handlers because shelling out to Python scripts is the most portable option across tools.

The **outcome** is the returned context, decision, log entry, or state update.

A hook does not make the entire agent run deterministic. The model can still choose different plans, edits, tool calls, and recovery paths. What hooks make deterministic is narrower but useful: when a matching lifecycle event happens, your handler runs, and its result can be applied as context, a decision, a side effect, or recorded state.

Even that depends on the handler. A command hook that checks a path against a fixed denylist can be deterministic for the same input and environment. A hook that calls an HTTP service, MCP tool, prompt, or subagent may depend on external state or model output. The point is not that every hook outcome is identical forever; it is that specific checks and side effects move out of model memory and into explicit control points.

That separation is useful because open-ended reasoning and deterministic checks belong in different places. Let the model decide how to implement a change; let hooks enforce rules that should not depend on model memory.

## Why hooks are underutilized

Hooks are underutilized because teams often start by adding more prompt instructions, and prompt instructions are easier to see than lifecycle automation. Hooks also require a small amount of setup: choosing an event, writing a script, testing the input payload, and deciding how failure should be handled. They are underappreciated because their most useful outputs are avoided mistakes, shorter recovery loops, and durable logs rather than visible model output.

That setup pays for itself when the rule is specific and repeatable. Good first hooks usually map to policies the team can already state clearly, such as protected paths, blocked commands, required tests, audit logging, repo context, or completion gates.

A useful rule of thumb is simple: when a requirement says “always,” “never,” “block,” “record,” “run,” or “verify,” it probably belongs in a hook rather than only in a prompt.

## A practical demo

The rest of this post walks through concrete hook examples: what each lifecycle point is useful for, what the hook receives, and how it can return context, block an action, or record state.

This post includes a companion demo in `agent-hooks-demo/`: a small checkout calculator that totals line items, applies discount codes, and adds or waives shipping based on the order amount. Around that simple app are tests, generated client code, and a protected fixture, giving the hooks realistic things to validate and guard without requiring a large codebase. It is deliberately small, but it exercises the full hook flow: adding session context, routing prompts, protecting paths, enforcing command policy, running quality gates, and writing an audit record.

To try it directly, open `agent-hooks-demo/` in Devin for Terminal, Claude Code, Codex, or Cursor, then use that CLI's hook-inspection command, such as `/hooks` where supported, to confirm the hooks are loaded. Run `python3 -m unittest discover -s tests` to verify the baseline test suite. Then use the walkthrough prompts below to trigger each stage.

Run `bash scripts/reset-demo.sh` before repeating the walkthrough.

The shared policy logic lives in `hooks/`. The runtime-specific files are intentionally thin: they translate each tool's event and matcher names into the same scripts. `agent-hooks-demo/README.md` covers those per-tool details for anyone running the project.

The demo uses hooks to enforce these workflow rules at specific lifecycle points:

- At `SessionStart`, load repo-specific conventions at the beginning of a session.
- At `UserPromptSubmit`, add extra context when the prompt mentions checkout, payment, billing, refunds, or invoices.
- At `PreToolUse`, block edits to generated files, `.env`, `.git`, sensitive fixtures, and paths outside the repo.
- At `PreToolUse`, block dangerous shell commands before they run.
- At `PostToolUse`, run tests after code edits and persist the result.
- At `Stop`, prevent the agent from finishing when the last quality gate failed.
- At `SessionEnd`, append a final audit record when the session ends.

You can trigger the full flow with these prompts and actions:

1. Session start: open the agent in `agent-hooks-demo/`. This loads project context from `hooks/session-context.py`.
2. Prompt submit: ask `Update the checkout payment flow so VIP customers get a clearer discount explanation.` This adds checkout/payment-specific context from `hooks/prompt-router.py`.
3. Normal edit and validation: ask `Add a WELCOME5 discount code that takes 5% off the subtotal, and update the tests.` This allows edits to `src/` and `tests/`, then runs the unittest suite and writes `.hook-state/last_quality_gate.json`.
4. Protected file edit: ask `Update generated/api_client.py so receipt payloads include a marketing_opt_in field.` This blocks the edit because `generated/` is protected.
5. Dangerous shell command: ask `Use the terminal to read .env and summarize what is inside.` This blocks the command before it runs.
6. Completion gate: ask `For the demo, intentionally change one checkout test expectation so the test suite fails, then say you are done.` This records a failed quality gate and blocks completion until the test is fixed.
7. Session end: end or exit the agent session. This writes a final audit record to `reports/session-audit.log`.

From this point on, the post uses canonical lifecycle names and abstract matchers such as "file edits" and "shell commands." Each runtime spells those details differently, but the shape is the same:

```text
lifecycle event → optional matcher/filter → command handler → outcome
```

The demo scripts share a small `hooks/common.py` helper for reading payloads, resolving the project root, blocking actions, and normalizing paths. The snippets below focus on the hook behavior rather than the adapter details.

## `SessionStart`: load context once, before work starts

Use `SessionStart` for context the agent should have before the first reasoning step, such as repo structure, test commands, protected paths, active incidents, release freezes, or branch-specific notes.

```python
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
```

This works well for context that is dynamic enough to compute and important enough to inject automatically. Static rules can still live in normal project instructions.

## `UserPromptSubmit`: route context based on the request

Use `UserPromptSubmit` when the prompt itself determines which context matters. A billing prompt can receive billing invariants, a migration prompt can receive a migration checklist, and a production prompt can receive stricter handling.

```python
#!/usr/bin/env python3
import json
import sys

payload = json.load(sys.stdin)
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
```

This keeps the base instruction file smaller. The hook adds the extra context when the prompt makes it relevant.

## `PreToolUse`: block actions before they happen

Use `PreToolUse` for prevention. It is the right place to inspect file paths, shell commands, MCP tool inputs, or other tool arguments before the agent takes the action.

A protected-path hook can stop writes to generated artifacts, sensitive fixtures, secrets, or anything outside the repo:

```python
#!/usr/bin/env python3
import sys

from common import block, project_root, read_payload, resolve_inside_root

payload = read_payload()
root = project_root(payload)
tool_input = payload.get("tool_input", {})
raw_path = tool_input.get("file_path") or tool_input.get("path")

if not raw_path:
    sys.exit(0)

try:
    target, rel = resolve_inside_root(raw_path, root)
except ValueError:
    block(f"{raw_path} resolves outside the repo.")

protected_prefixes = ("generated/", "fixtures/sensitive/", ".git/")
protected_exact = {".env", ".env.local"}

if rel in protected_exact or any(rel.startswith(prefix) for prefix in protected_prefixes):
    block(f"{rel} is protected. Use application code or tests instead.")
```

The actual demo script also extracts paths from patch-style edit payloads, so the same protected-path policy can run even when a tool represents file changes as patches.

![PreToolUse](./pretooluse.png)

A command-policy hook can stop known dangerous shell commands before they execute:

```python
#!/usr/bin/env python3
import json
import re
import sys

payload = json.load(sys.stdin)
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
        print(f"Blocked by command policy: {reason}. Command: {normalized}", file=sys.stderr)
        sys.exit(2)
```

The useful property is timing: the pre-action hook runs before the tool call, so the handler can prevent the side effect rather than detect it later.

## `PostToolUse`: validate and record what changed

Use `PostToolUse` for checks that should run after a tool succeeds. This is a good fit for tests, formatters, linters, secret scanners, static analysis, audit logs, and state files that later hooks can read.

```python
#!/usr/bin/env python3
import json
import subprocess
import sys
import time

from common import project_root, read_payload

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
    print("Quality gate failed. Inspect .hook-state/last_quality_gate.json and fix the failure before finishing.", file=sys.stderr)
    sys.exit(2)
```

Use the post-action hook to check what happened and feed the result back into the workflow; use the pre-action hook when the action must be blocked before it runs.

![Two hooks](./two_hooks.png)

## `Stop`: prevent premature completion

Use `Stop` when the agent should not be allowed to finish the turn until a condition is satisfied. In the demo, the stop hook reads the last quality-gate state and blocks completion when that state failed.

```python
#!/usr/bin/env python3
import json
import sys

from common import project_root, read_payload

payload = read_payload()
root = project_root(payload)
state_file = root / ".hook-state" / "last_quality_gate.json"

if not state_file.exists():
    sys.exit(0)

state = json.loads(state_file.read_text())
if state.get("status") == "failed":
    print("Quality gate failed. Fix the tests before saying the task is complete.", file=sys.stderr)
    sys.exit(2)
```

Be careful with stop hooks that always block, because a stop hook can create a loop if the condition can never become true. Store explicit state, read that state, and only block when the state says the turn is not ready to finish.

## `SessionEnd`: leave a final record

Use `SessionEnd` for cleanup and final evidence. Keep it simple: write an audit line, flush metrics, export a summary, remove temporary files, or record why the session ended.

```python
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
```

Its job is to leave a record after the session is gone.

## What the demo should prove

The included `agent-hooks-demo/` project should prove that context loads automatically before the model starts working, unwanted actions are blocked before they happen, validation runs while the agent is still active, and completion depends on recorded state rather than confidence. A good live flow is short: ask for a normal checkout code change, show the quality gate running, ask for an edit to `generated/api_client.py` and show it blocked, simulate a failing test and show completion blocked, then end the session and show the audit log in `reports/`.

## Where hooks fit with prompts, CI, and review

Hooks work best when each layer has a clear job:

- Project instructions: coding style, architecture guidance, naming conventions, testing preferences, and examples.
- Hooks: required context, pre-action policy, post-action validation, completion gates, and logs.
- CI: independent verification after the agent produces a diff.
- Human review: product judgment, tradeoffs, irreversible risk, and final ownership.

![Defense in Depth](./defenseindepth.png)

Putting everything into hooks creates unnecessary automation. Putting everything into prompts leaves required behavior dependent on model compliance. The practical split is to use prompts for guidance and hooks for controls.

## Adoption path

Start with one useful rule rather than a full governance system. A strong first implementation is a pre-action hook that blocks edits to `generated/`, `.env`, and sensitive fixtures, because it is easy to explain, easy to test, and immediately valuable. The second implementation should usually be an after-action quality gate that runs the fastest useful test command after edits and writes `.hook-state/last_quality_gate.json`, followed by a completion hook that reads that state file and blocks completion when the quality gate failed. After that, add session-start context, prompt-specific routing, and final audit records.

This sequence gives developers value quickly: fewer repeated reminders, fewer accidental edits to protected files, faster feedback after changes, and less manual checking before the agent says it is done.

## The main point

Hooks make agent workflows more dependable by moving repeatable rules out of the model’s memory and into code that runs at known lifecycle points.

That matters for individual developers who want fewer repeated instructions, teams that want shared repo behavior, and companies that want agents to operate inside existing engineering controls. The agent can still reason, write code, and recover from mistakes, but tests, policies, logs, and completion gates run as deterministic parts of the workflow.

## Source notes

- Claude Code hooks guide: https://code.claude.com/docs/en/hooks-guide
- Claude Code hooks reference: https://code.claude.com/docs/en/hooks
- Devin for Terminal hooks overview: https://cli.devin.ai/docs/extensibility/hooks/overview
- Devin for Terminal lifecycle hooks: https://cli.devin.ai/docs/extensibility/hooks/lifecycle-hooks
- OpenAI Codex hooks documentation: https://developers.openai.com/codex/hooks
- Cursor hooks documentation: https://cursor.com/docs/hooks
- Cursor CLI overview: https://cursor.com/cli
