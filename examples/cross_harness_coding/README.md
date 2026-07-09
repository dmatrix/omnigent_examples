# Cross-Harness Coding with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**Codex implements, Claude reviews, cost-guarded — multi-harness orchestration with budget governance.**

![Cross-Harness Coding Architecture](images/cross_harness_coding_architecture.svg)

---

## Overview

The cross-harness coding example demonstrates **composition** and **governance** — Omnigent's ability to orchestrate multiple LLM providers within a single agent session while enforcing budget controls. Three different agents, from different providers, collaborate across two harnesses:

- **`Supervisor`** — Lightweight coordinator on the **Claude SDK** harness (Anthropic). Decomposes tasks, dispatches to sub-agents, checks test results, and synthesizes results. Never writes code itself.
- **`impl_worker`** — Implementation specialist on the **Codex** harness (OpenAI). Writes code, creates tests, and runs verification.
- **`review_worker`** — Code reviewer on the **Claude SDK** harness (Anthropic). Reviews for correctness, security, style, and performance.

The supervisor breaks down user requests, dispatches implementation to the Codex agent, which writes code and runs tests. If the impl_worker reports test failures, the supervisor sends failures back without bothering the reviewer. Once tests pass, the supervisor routes to Claude for review. If the review returns REVISE, the supervisor sends feedback back for another pass. All three agents share the same filesystem and session — no copy-paste, no context switching.

A layered **cost guardrail** caps spend at two levels: a per-agent `cost_guard` ($1.00 per sub-agent invocation) and a `daily_cost_guard` ($5.00/day across all agents).

---

## Get Started

No database setup needed.

### Prerequisites

- Python 3.12+
- The `omnigent` CLI installed (`pip install omnigent`)
- `pytest` installed (`pip install pytest`)
- `ANTHROPIC_API_KEY` in `.env` (for supervisor + reviewer)
- `OPENAI_API_KEY` in `.env` (for implementer)
- Codex CLI installed (`npm i -g @openai/codex`)

> **No Codex CLI?** Swap the implementer to `openai-agents` harness — see [Harness Swapping](#harness-swapping) below.

---

## Run Locally

### 1. Configure credentials (one-time)

```bash
omnigent setup
```

### 2. Export your API keys

```bash
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
export $(grep OPENAI_API_KEY .env | tr -d '"')
```

### 3. Run the agent

The default config uses `databricks-*` models, which require Databricks auth (`omnigent login`). To run locally with direct API keys instead, override the models:

```bash
# With Databricks auth configured (default config)
omnigent run examples/cross_harness_coding/

# With direct API keys (no Databricks dependency)
omnigent run examples/cross_harness_coding/ --model claude-sonnet-4-6

# Fresh session (no persistence)
omnigent run examples/cross_harness_coding/ --no-session
```

> **Note:** The `--model` flag overrides the supervisor only. The `impl_worker` sub-agent defaults to `databricks-gpt-5-4` on Codex — to use direct API, edit `agents/impl_worker/config.yaml` and change the model to `gpt-5.4` (see [Harness Swapping](#harness-swapping)).

---

## Run on Databricks

Override the models to route through Databricks AI Gateway:

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/cross_harness_coding/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

---

## Example Queries

**Implement, test, and review:**
```
Write a Python rate limiter class using the token bucket algorithm.
Put it in rate_limiter.py with unit tests in test_rate_limiter.py.
Make sure all tests pass before sending to review.
```

**Test failure → fix cycle:**
```
Write a binary search function in search.py with edge case tests
in test_search.py. Include a test for an empty list.
```

**Filesystem operations + test:**
```
Write a file_scanner.py that walks the current directory, collects
file sizes, and writes a summary report to scan_report.txt.
Include tests that verify the scanner handles permission errors
and symbolic links. Run the tests.
```

**Refactor + re-test + review:**
```
Read rate_limiter.py, refactor it to use async/await,
re-run the tests, then review the refactor for correctness.
```

**Cost guard trigger (run after the queries above):**
```
Now write a CLI wrapper in cli.py with argument parsing, help text,
and integration tests. Then review it.
```
> After one or two implement-test-review cycles, the per-agent `cost_guard` ASK threshold ($0.25) or the `daily_cost_guard` ASK threshold ($0.50) fires — the agent pauses and asks for approval to continue. This is layered cost governance in action across both providers.

All generated code is written to `examples/cross_harness_coding/omnigent_generated_code/`.

---

## Harness Swapping

The supervisor's harness can be overridden at the CLI. Sub-agent harnesses are set in each agent's own `config.yaml` under `agents/`.

**No Codex CLI? Use openai-agents instead:**

Edit `agents/impl_worker/config.yaml` and change the executor:
```yaml
executor:
  type: omnigent
  model: databricks-gpt-5-4
  config:
    harness: openai-agents    # No CLI dependency, just OPENAI_API_KEY
```

**Both agents on Claude (single provider):**

Edit `agents/impl_worker/config.yaml`:
```yaml
executor:
  type: omnigent
  model: databricks-claude-sonnet-4-6
  config:
    harness: claude-sdk
```

**Both agents on OpenAI:**

Edit `agents/review_worker/config.yaml`:
```yaml
executor:
  type: omnigent
  model: databricks-gpt-5-4
  config:
    harness: openai-agents
```

---

## How to Demo

See [demo.md](demo.md) for a timed walkthrough (8-10 min).

---

## Architecture

| Agent | Harness | Model | Role |
|---|---|---|---|
| **Supervisor** | `claude-sdk` | `databricks-claude-sonnet-4-6` | Coordinator — breaks down tasks, routes to sub-agents, synthesizes results |
| **impl_worker** | `codex` | `databricks-gpt-5-4` | Implementation — writes code, creates tests, runs verification |
| **review_worker** | `claude-sdk` | `databricks-claude-sonnet-4-6` | Review — correctness, security, style, performance analysis |

All three agents share the same `os_env` (filesystem and CWD). The supervisor dispatches sequentially: implement, test, then review. If the review returns REVISE, the cycle repeats.

### Request flow

```
1. User sends a coding task (e.g. "write a rate limiter")
2. Supervisor (Claude) breaks down the request, dispatches to impl_worker
3. impl_worker (Codex) writes code and runs tests
4. If tests fail → Supervisor sends failures back to impl_worker for fixes
5. Once tests pass → Supervisor dispatches to review_worker
6. review_worker (Claude) reviews the code → returns PASS, REVISE, or REJECT
7. If REVISE → Supervisor sends feedback back to impl_worker for revision
8. Supervisor synthesizes the final result and responds to the user
```

All three agents operate on the same working directory.

---

## Guardrails

| Policy | Scope | Limit |
|---|---|---|
| `cost_guard` | Per sub-agent invocation | $1.00 max, $0.25 ASK threshold |
| `daily_cost_guard` | Daily across all agents | $5.00 max, $0.50 ASK threshold |

Cost governance is layered at two levels. Each sub-agent (`impl_worker`, `review_worker`) has its own `cost_guard` that caps a single invocation at $1.00 (ASK at $0.25). On top of that, all three agents (supervisor + impl_worker + review_worker) share a `daily_cost_guard` that tracks cumulative daily spend across both providers (Anthropic + OpenAI). When daily spend crosses $0.50, the user is asked to approve. At $5.00, the session is terminated.

### Cost guard recovery

When a hard limit fires, recovery depends on which policy was triggered:

| Scenario | What happens | How to continue |
|---|---|---|
| **Per-invocation cap** (`cost_guard` hits $1.00) | The sub-agent invocation is terminated and an error is returned to the supervisor. The supervisor session stays alive. | Send a new message — the supervisor dispatches a fresh sub-agent call with a fresh $1.00 budget. |
| **Daily cap** (`daily_cost_guard` hits $5.00) | The entire session is terminated. No more turns until the budget resets. | Wait for the next calendar day (daily budget resets automatically), or raise `max_cost_usd` in all three `config.yaml` files and re-run. |
| **ASK threshold** (`$0.25` or `$0.50`) | The agent pauses and asks for approval. | Approve to continue, or deny to stop the current operation. |

**Adjusting limits:**

```bash
# Start a fresh session (resets per-invocation budgets, but daily budget is per-user)
omnigent run examples/cross_harness_coding/ --no-session
```

To permanently raise or lower limits, edit the `guardrails:` block in the relevant `config.yaml`:

- **Fewer pauses** — raise `ask_thresholds_usd` (e.g., `[1.00]` instead of `[0.25]`)
- **Higher per-invocation cap** — raise `max_cost_usd` in the sub-agent's `cost_guard`
- **Higher daily cap** — raise `max_cost_usd` in `daily_cost_guard` across all three configs (supervisor + both sub-agents)

