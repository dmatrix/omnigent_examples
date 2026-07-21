# Cross-Harness Coding — Demo Script

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

### Act 4: The Budget (1 min) — "Layered budgets, two providers"

**Show** the `guardrails:` blocks in all three `config.yaml` files.

**Say:** "Two layers of cost governance. Each sub-agent has a `cost_guard` — a dollar cap per invocation so no single agent runs away. Then all three agents share a `daily_cost_guard` — five dollars per day across both providers. The ASK thresholds fire early so the user stays informed. Layered budgets across two providers and three agents."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 2 min | Three configs, two harnesses, one directory |
| 2. The Pipeline | 4 min | Implement on Codex → test → review on Claude |
| 3. The Swap | 2 min | Swap harnesses without changing tools/prompts |
| 4. The Budget | 1 min | Layered cost budgets across all providers |
| **Total** | **9 min** | |
