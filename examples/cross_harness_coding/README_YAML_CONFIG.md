# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Attribute-level walkthrough of all three config files (supervisor + two sub-agents). All three agents share the same filesystem (`os_env: caller_process`, `cwd: .`, `sandbox: none`). CLI `--model`/`--harness` flags override the supervisor only — sub-agent harnesses are set in their own configs.

---

## Supervisor (`config.yaml`)

| Attribute | Value | Notes |
|---|---|---|
| `model` | `databricks-claude-sonnet-4-6` | Override with `--model`. |
| `config.harness` | `claude-sdk` | Override with `--harness`. |

### `prompt:`

The system prompt defines orchestration logic (no code required):

1. **Role** — "You are a coding supervisor"
2. **Hard constraint** — "You MUST delegate all work — never write or review code yourself"
3. **Agent roster** — `impl_worker` (coder) and `review_worker` (reviewer)
4. **Workflow** — implement → verify tests → review → revise if needed
5. **Transparency rule** — "Always tell the user which agent is working"

### `tools:`

```yaml
tools:
  agents:
    - impl_worker
    - review_worker
```

The framework discovers `agents/<name>/config.yaml`, registers each as a callable tool, and spawns child sessions on invocation.

---

## Sub-agents

### `agents/impl_worker/config.yaml`

| Attribute | Value | Notes |
|---|---|---|
| `model` | `databricks-gpt-5-4` | Different provider from the supervisor — this is the cross-harness part. |
| `config.harness` | `codex` | Requires Codex CLI on PATH. |
| `cost_guard` | $1.00 max, $0.25 ASK | Per-invocation cap. |
| `daily_cost_guard` | $5.00 max, $0.50 ASK | Daily cap shared across all agents. |

### `agents/review_worker/config.yaml`

| Attribute | Value | Notes |
|---|---|---|
| `model` | `databricks-claude-sonnet-4-6` | Same model as supervisor, separate session. |
| `config.harness` | `claude-sdk` | Same harness as supervisor. |
| `cost_guard` | $1.00 max, $0.25 ASK | Per-invocation cap. |
| `daily_cost_guard` | $5.00 max, $0.50 ASK | Daily cap shared across all agents. |

---

## `guardrails:` — Layered cost governance

No labels, no taint, no deny policies — cost is the only governance dimension here.

### Two levels

| Policy | Function | Scope | Limit |
|---|---|---|---|
| `cost_guard` | `cost_budget` | Per sub-agent invocation | $1.00 max, $0.25 ASK |
| `daily_cost_guard` | `user_daily_cost_budget` | Daily across all agents | $5.00 max, $0.50 ASK |

The per-invocation cap catches runaway sub-agents early. The daily cap provides the session-wide ceiling across both providers (Anthropic + OpenAI). One implement-test-review cycle costs $0.50–1.00; the $1.00 per-invocation limit allows one full cycle, the $5.00 daily limit allows multiple revision cycles.

### Recovery

| Scenario | What happens | How to continue |
|---|---|---|
| Per-invocation cap ($1.00) | Sub-agent terminated, error returned to supervisor. Session stays alive. | Send a new message — fresh sub-agent call gets a fresh $1.00 budget. |
| Daily cap ($5.00) | Entire session terminated. | Wait for next calendar day, or raise `max_cost_usd` in all three configs. |
| ASK threshold | Agent pauses for approval. | Approve or deny. |

---

## Nesting summary

```
cross_harness_coding/
+-- config.yaml               # SUPERVISOR (harness: claude-sdk)
|   +-- executor               #   databricks-claude-sonnet-4-6
|   +-- prompt                 #   orchestration logic
|   +-- tools.agents           #   [impl_worker, review_worker]
|   +-- guardrails
|       +-- daily_cost_guard   #   $5.00/day, $0.50 ASK
+-- agents/
    +-- impl_worker/
    |   +-- config.yaml        # IMPL (harness: codex, gpt-5-4)
    |       +-- cost_guard     #   $1.00/invocation, $0.25 ASK
    |       +-- daily_cost_guard
    +-- review_worker/
        +-- config.yaml        # REVIEWER (harness: claude-sdk)
            +-- cost_guard     #   $1.00/invocation, $0.25 ASK
            +-- daily_cost_guard
```

---

## Session tree

```
Session: cross_harness_coding (root)
+-- supervisor turn 1
|   +-- impl_worker (child session)   <-- spawned as tool call
|   +-- review_worker (child session) <-- spawned as tool call
+-- supervisor turn 2
|   +-- impl_worker (child session)   <-- revision pass
...
```

**Shared:** session identity, filesystem (all agents read/write the same CWD), `daily_cost_guard` (cumulative daily cost), conversation history.

**Not shared:** context window (each sub-agent has its own), executor (each talks to its own LLM provider independently).

---

**Not in this config:** No labels, no taint/deny policies, no `web_search` builtin. See [secure_code_assistant](../secure_code_assistant/) and [telco_customer_agent](../telco_customer_agent/) for those patterns.
