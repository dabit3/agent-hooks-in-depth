# Agent Hooks Demo

This demo project maps to the blog post in the parent directory. It is a small checkout application with shared hook scripts under `hooks/` and thin config adapters for Devin, Claude Code, Codex, and Cursor.

## Run the tests

```bash
python3 -m unittest discover -s tests
```

## Reset the demo

Run this before repeating the walkthrough:

```bash
bash scripts/reset-demo.sh
```

The reset script restores the checkout app, tests, generated client, and sensitive fixture to their starting contents. It also removes `.hook-state/`, `reports/`, `.env`, `.env.local`, and Python cache directories.

## Try the hooks

Open this directory with the CLI you want to test, then run that CLI's hook-inspection command, such as `/hooks` where supported, to confirm the hooks are loaded.

| Runtime | Config file | Notes |
|---|---|---|
| Devin for Terminal | `.devin/hooks.v1.json` | Uses Devin matcher names such as `exec`, `edit`, `write`, and `apply_patch`. |
| Claude Code | `.claude/settings.json` | Uses Claude matcher names such as `Bash`, `Edit`, `Write`, and `MultiEdit`. |
| Codex | `.codex/config.toml` and `.codex/hooks.json` | File edits are exposed as `apply_patch`, with `Edit` and `Write` supported as matcher aliases. Project hooks load after the project is trusted. |
| Cursor | `.cursor/hooks.json` | Uses Cursor event names such as `beforeShellExecution`, `afterFileEdit`, and `beforeSubmitPrompt`. |

All four configs call the same Python scripts in `hooks/`, so policy logic stays in one place.

## Prompts to trigger each stage

Use these prompts after opening the demo in an agent CLI. Run `bash scripts/reset-demo.sh` before starting over.

| Stage | Hook fired | Prompt or action | Expected hook behavior |
|---|---|---|---|
| Session start | `SessionStart` | Open the agent in this directory. | Loads project context from `hooks/session-context.py`. |
| Prompt submit | `UserPromptSubmit` | `Update the checkout payment flow so VIP customers get a clearer discount explanation.` | Adds checkout/payment-specific context from `hooks/prompt-router.py`. |
| Normal edit and validation | `PreToolUse` then `PostToolUse` | `Add a WELCOME5 discount code that takes 5% off the subtotal, and update the tests.` | Allows edits to `src/` and `tests/`, then runs the unittest suite and writes `.hook-state/last_quality_gate.json`. |
| Protected file edit | `PreToolUse` | `Update generated/api_client.py so receipt payloads include a marketing_opt_in field.` | Blocks the edit because `generated/` is protected. |
| Dangerous shell command | `PreToolUse` | `Use the terminal to read .env and summarize what is inside.` | Blocks the command before it runs. |
| Completion gate | `PostToolUse` then `Stop` | `For the demo, intentionally change one checkout test expectation so the test suite fails, then say you are done.` | Records a failed quality gate and blocks completion until the test is fixed. |
| Session end | `SessionEnd` | End or exit the agent session. | Writes a final audit record to `reports/session-audit.log`. |

The hook audit records are written to `reports/`, which is ignored by git.

## Runtime-specific notes

The blog post uses canonical lifecycle names such as `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, and `SessionEnd`. Each runtime maps those ideas to its own config files, event names, matcher names, and environment variables:

- Devin for Terminal uses `.devin/hooks.v1.json` as a standalone hooks file, so lifecycle events such as `SessionStart` and `PreToolUse` are top-level JSON keys. The demo uses Devin matcher names such as `exec`, `edit`, `write`, and `apply_patch`, and Devin provides `DEVIN_PROJECT_DIR`.
- Claude Code uses `.claude/settings.json` with hooks nested under the `"hooks"` key. The demo uses Claude matcher names such as `Bash`, `Edit`, `Write`, and `MultiEdit`, and Claude Code provides `CLAUDE_PROJECT_DIR`.
- Codex uses `.codex/config.toml` and `.codex/hooks.json`. The demo sets the canonical feature key, `[features].hooks = true`; hooks are enabled by default in current Codex, but the explicit setting makes the demo self-documenting. File edits are exposed as `apply_patch`, with `Edit` and `Write` supported as matcher aliases. Project hooks load after the project `.codex/` layer is trusted. Codex currently runs `command` handlers; `prompt` and `agent` handlers are parsed but skipped.
- Cursor uses `.cursor/hooks.json` and event names such as `beforeShellExecution`, `afterFileEdit`, and `beforeSubmitPrompt`.

The scripts use Claude Code's documented output contract where possible: `hookSpecificOutput.additionalContext` for structured context, and exit code `2` plus stderr for simple blocks. Devin supports the Claude-compatible format, and Codex accepts the same `hookSpecificOutput` context shape and exit-code blocking. For Cursor, the demo keeps the policy scripts command-based and uses the Cursor event names in `.cursor/hooks.json`.

The runtime configs also normalize project-root discovery before invoking the scripts. Devin provides `DEVIN_PROJECT_DIR`, Claude Code provides `CLAUDE_PROJECT_DIR`, and the Codex and Cursor configs set `AGENT_HOOKS_PROJECT_DIR` themselves. `hooks/common.py` checks those variables, then falls back to workspace roots, `cwd`, and the current directory.

The protected-path hook accepts several edit payload shapes, including direct file paths and patch-style changes such as Codex `apply_patch`, so the same policy can run across tools.
