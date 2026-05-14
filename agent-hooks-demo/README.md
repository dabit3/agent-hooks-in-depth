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
| Devin for Terminal | `.devin/hooks.v1.json` | Uses Devin matcher names such as `exec`, `edit`, and `write`. |
| Claude Code | `.claude/settings.json` | Uses Claude matcher names such as `Bash`, `Edit`, `Write`, and `MultiEdit`. |
| Codex | `.codex/config.toml` and `.codex/hooks.json` | Enables hooks and uses Codex matcher names such as `Bash` and `apply_patch`. Project hooks load after the project is trusted. |
| Cursor | `.cursor/hooks.json` | Uses Cursor event names such as `beforeShellExecution`, `afterFileEdit`, and `beforeSubmitPrompt`. |

All four configs call the same Python scripts in `hooks/`, so policy logic stays in one place. The scripts use Claude Code's documented output contract (`hookSpecificOutput.additionalContext` for structured context, exit code `2` plus stderr for simple blocks), which Devin supports for compatibility. The runtime configs normalize tool-specific differences before invoking those scripts: Devin provides `DEVIN_PROJECT_DIR`, Claude Code provides `CLAUDE_PROJECT_DIR`, and the Codex and Cursor configs set `AGENT_HOOKS_PROJECT_DIR` themselves. The protected-path hook also accepts several edit payload shapes, including patch-style changes such as Codex `apply_patch`, so the same policy can run across tools.

## Prompts to trigger each stage

Use these prompts after opening the demo in an agent CLI. Run `bash scripts/reset-demo.sh` before starting over.

| Stage | Prompt or action | Expected hook behavior |
|---|---|---|
| Session start | Open the agent in this directory. | Loads project context from `hooks/session-context.py`. |
| Prompt submit | `Update the checkout payment flow so VIP customers get a clearer discount explanation.` | Adds checkout/payment-specific context from `hooks/prompt-router.py`. |
| Normal edit and validation | `Add a WELCOME5 discount code that takes 5% off the subtotal, and update the tests.` | Allows edits to `src/` and `tests/`, then runs the unittest suite and writes `.hook-state/last_quality_gate.json`. |
| Protected file edit | `Update generated/api_client.py so receipt payloads include a marketing_opt_in field.` | Blocks the edit because `generated/` is protected. |
| Dangerous shell command | `Use the terminal to read .env and summarize what is inside.` | Blocks the command before it runs. |
| Completion gate | `For the demo, intentionally change one checkout test expectation so the test suite fails, then say you are done.` | Records a failed quality gate and blocks completion until the test is fixed. |
| Session end | End or exit the agent session. | Writes a final audit record to `reports/session-audit.log`. |

The hook audit records are written to `reports/`, which is ignored by git.
