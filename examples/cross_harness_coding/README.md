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

A `cost_guard` policy caps total spend across all three agents and both providers, making this the first example to combine **composition** and **governance** in one config.

This is the pattern described in the Omnigent value proposition as **_composition_**: *"Start a coding task in Codex, then route a subtask to Claude Code while keeping one shared session."*

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

```bash
# Default: Codex implements, Claude reviews
omnigent run examples/cross_harness_coding/

# Fresh session (no persistence)
omnigent run examples/cross_harness_coding/ --no-session
```

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
> After one or two implement-test-review cycles, the `cost_guard` ASK threshold ($0.10) fires — the supervisor pauses and asks for approval to continue. This is the cost budget in action across both providers.

All generated code is written to `examples/cross_harness_coding/omnigent_generated_code/`.

---

## Harness Swapping

The supervisor's harness can be overridden at the CLI. Sub-agent harnesses are set in each agent's own `config.yaml` under `agents/`.

**No Codex CLI? Use openai-agents instead:**

Edit `agents/impl_worker/config.yaml` and change the executor:
```yaml
executor:
  type: omnigent
  model: gpt-5.4
  config:
    harness: openai-agents    # No CLI dependency, just OPENAI_API_KEY
```

**Both agents on Claude (single provider):**

Edit `agents/impl_worker/config.yaml`:
```yaml
executor:
  type: omnigent
  model: claude-sonnet-4-6
  config:
    harness: claude-sdk
```

**Both agents on OpenAI:**

Edit `agents/review_worker/config.yaml`:
```yaml
executor:
  type: omnigent
  model: gpt-5.4
  config:
    harness: openai-agents
```

---

## How to Demo (8-10 min)

### Act 1: The YAML (2 min) — "Three agents, two harnesses, one directory"

**Show** `config.yaml` — the supervisor references its sub-agents by name:

**Say:** "The supervisor runs on Claude and references two sub-agents: `impl_worker` and `review_worker`. Each lives in its own directory under `agents/` with its own `config.yaml`."

**Open** `agents/impl_worker/config.yaml` and `agents/review_worker/config.yaml`:
> "The implementer runs on Codex — OpenAI's coding agent. The reviewer runs on Claude. Two different LLM providers, each with their own executor config. The framework handles the routing — you don't write any glue code."

---

### Act 2: The Pipeline (4 min) — "Implement, test, and review"

**Run:** `omnigent run examples/cross_harness_coding/ --no-session`

**Prompt:**
```
Write a Python rate limiter class using the token bucket algorithm.
Put it in rate_limiter.py with unit tests in test_rate_limiter.py.
```

**Watch:** The supervisor dispatches to `impl_worker` (OpenAI writes the code and runs tests), then dispatches to `review_worker` (Claude reviews it).

**Say:** "Two different models, two different providers, talking through one session. The implementer wrote the code and ran tests. Then Claude reviewed it. The supervisor coordinates but never touches the code."

**If tests fail:**
> "Tests failed. Watch — the supervisor sends the failures back to the Codex implementer. It doesn't bother the reviewer until tests pass."

**If review returns REVISE:**
> "The reviewer found an issue. Watch — the supervisor sends the feedback back to the Codex implementer for revision. Same session, same files, different harnesses."

---

### Act 3: The Swap (2 min) — "Same config, different brains"

**Say:** "Your team wants both agents on Claude? One YAML change."

**Show** the harness swapping section — point out that changing `harness: codex` to `harness: claude-sdk` is the only edit.

**Say:** "The tools, the prompts, the delegation logic — nothing changes. Only the executor block. This is what harness portability means. Your workflow survives model migrations."

---

### Act 4: The Budget (1 min) — "One budget, two providers"

**Show** the `guardrails:` block in `config.yaml`.

**Say:** "One policy — `cost_guard`. It tracks spend across all three agents and both providers. The ASK threshold fires at fifty cents, so the user stays informed. The hard cap is three dollars — enough for a couple revision cycles. This is governance plus composition — one budget, two providers, three agents."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 2 min | Three configs, two harnesses, one directory |
| 2. The Pipeline | 4 min | Implement on Codex → test → review on Claude |
| 3. The Swap | 2 min | Swap harnesses without changing tools/prompts |
| 4. The Budget | 1 min | One cost budget across all providers |
| **Total** | **9 min** | |

---

## Architecture

| Agent | Harness | Model | Role |
|---|---|---|---|
| **Supervisor** | `claude-sdk` | `claude-sonnet-4-6` | Coordinator — breaks down tasks, routes to sub-agents, synthesizes results |
| **impl_worker** | `codex` | `gpt-5.5` | Implementation — writes code, creates tests, runs verification |
| **review_worker** | `claude-sdk` | `claude-sonnet-4-6` | Review — correctness, security, style, performance analysis |

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

| Policy | Action | Limit |
|---|---|---|
| `cost_guard` | Budget | $3.00 max, $0.50 ASK threshold |

The cost guard tracks cumulative LLM spend across all three agents (supervisor + impl_worker + review_worker) and both providers (Anthropic + OpenAI). When spend crosses $0.50, the user is asked to approve. At $3.00, the session is terminated.

---

## Key Concepts

- **Cross-harness delegation**: Sub-agents run on different LLM providers (Codex + Claude SDK) within one session
- **Shared session**: All agents share the same session tree — context, files, and state persist across harness boundaries
- **Sequential dispatch**: Supervisor enforces implement→test→review ordering to avoid file conflicts
- **Cost-guarded composition**: A single budget policy caps spend across all three agents and both providers
- **Harness portability**: Swap any agent's harness without changing tools or prompts

---

## See Also: Polly

For a production-grade orchestrator, see [**Polly**](https://github.com/omnigent-ai/omnigent/tree/main/examples/polly/) in the Omnigent framework. Polly is a built-in multi-agent supervisor that extends this pattern with:

- **Three sub-agents** — Claude Code, Codex, and Pi, each in isolated git worktrees
- **Parallel fanout** — independent tasks run concurrently with automatic worktree isolation
- **Cross-vendor review** — every PR is reviewed by a different LLM provider than the one that wrote it
- **Investigation skills** — read-only exploration and debugging delegated to sub-agents

```bash
omnigent run examples/polly/
```
