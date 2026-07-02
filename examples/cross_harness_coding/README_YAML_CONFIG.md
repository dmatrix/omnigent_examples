# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Detailed breakdown of every attribute in `config.yaml`, its role, scope, and nesting.

---

## Top-level metadata (lines 1-7)

| Attribute | Value | Role |
|---|---|---|
| `spec_version` | `1` | Schema version of the Omnigent agent YAML spec. Tells the framework which parser to use. |
| `name` | `cross_harness_coding` | Unique identifier for this agent. Used in session logs, CLI output, and the `omnigent run` resolver. |
| `description` | *(multiline string)* | Human-readable summary shown in `omnigent list` and the Web UI. The `>` folding style collapses newlines into spaces. |

---

## `executor:` — The supervisor's brain

This block tells the framework which LLM provider and model to use for the **supervisor agent** (the top-level agent that the user talks to).

| Attribute | Value | Role |
|---|---|---|
| `type` | `omnigent` | The executor type. `omnigent` means the framework manages the agent loop (tool dispatch, session state, policy evaluation). |
| `model` | `databricks-claude-sonnet-4-6` | Which model to call. Routed through Databricks AI Gateway. Can be overridden at the CLI with `--model`. |
| `config.harness` | `claude-sdk` | Which SDK/protocol adapter to use for API calls. `claude-sdk` = Anthropic's native API. Can be overridden with `--harness`. |

**Scope:** This executor only governs the supervisor. Each sub-agent has its own `executor:` block.

---

## `prompt:` — The supervisor's system prompt

A `|` literal block (preserves newlines). This is the system message sent to the supervisor model on every turn. It defines:

1. **Role** — "You are a coding supervisor"
2. **Hard constraint** — "You MUST delegate all work — never write or review code yourself"
3. **Agent roster** — Names and capabilities of `impl_worker` and `review_worker`
4. **Workflow** — implement → verify tests → review → revise:
   - `impl_worker` writes code and runs tests
   - Supervisor checks the test report — if tests fail, sends failures back to `impl_worker` (skips review)
   - Once tests pass, `review_worker` reviews the code
   - If REVISE, feedback goes back to `impl_worker` for another cycle
5. **Transparency rule** — "Always tell the user which agent is working"

The prompt is the only place the orchestration logic lives — no code. The LLM follows these instructions to decide when to call which tool.

---

## `os_env:` — The supervisor's environment access

Grants the supervisor access to the host operating system (shell, filesystem).

| Attribute | Value | Role |
|---|---|---|
| `type` | `caller_process` | Inherit the shell environment of the process that launched `omnigent run` — same filesystem, env vars, and CWD. |
| `cwd` | `.` | Working directory. `.` = wherever you ran `omnigent run` from (typically the repo root). |
| `sandbox.type` | `none` | No sandboxing — the agent can read/write anywhere the calling process can. |

**Scope:** Each agent declares its own `os_env`. All three agents use `sandbox: none` and share the same `cwd: .` filesystem.

---

## `tools:` — Sub-agent references

The `tools:` block declares what the supervisor can call. It references two sub-agents by name — each lives in its own directory under `agents/`.

```yaml
tools:
  agents:
    - impl_worker
    - review_worker
```

The framework discovers `agents/impl_worker/config.yaml` and `agents/review_worker/config.yaml`, registers them as callable tools, and spawns child sessions when the supervisor invokes them.

---

### `agents/impl_worker/config.yaml` — The implementation sub-agent

| Attribute | Value | Role |
|---|---|---|
| `name` | `impl_worker` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `prompt` | *(literal block)* | System prompt for the implementation agent. Defines its role (coder), output directory (`omnigent_generated_code/`), and rules (write tests, run them, report results). |
| `executor.type` | `omnigent` | Same executor type as the supervisor. |
| `executor.model` | `databricks-gpt-5-4` | This sub-agent runs on OpenAI via Databricks AI Gateway, not Anthropic. This is the cross-harness part. |
| `executor.config.harness` | `codex` | Uses the Codex CLI harness (requires `codex` binary on PATH). |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as the supervisor and reviewer. All agents share the same working directory. |
| `guardrails.policies.cost_guard` | `cost_budget`, $1.00 max, $0.25 ASK | Per-invocation cost cap — prevents a single impl_worker call from running away. |
| `guardrails.policies.daily_cost_guard` | `user_daily_cost_budget`, $5.00 max, $0.50 ASK | Daily cost cap — shared across all agents in the session tree. |

**Key point:** The impl_worker's `executor` is completely independent from the supervisor's. Different model, different harness, different provider. The framework handles the protocol translation. The impl_worker also has its own guardrails — a per-invocation `cost_guard` and a `daily_cost_guard` — so cost is controlled at both the agent and session level.

---

### `agents/review_worker/config.yaml` — The review sub-agent

| Attribute | Value | Role |
|---|---|---|
| `name` | `review_worker` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `prompt` | *(literal block)* | System prompt for the reviewer. Reads from `omnigent_generated_code/`, evaluates on seven dimensions (correctness, style, security, performance, documentation, type hints, best practices), returns a structured verdict (PASS/REVISE/REJECT). |
| `executor.type` | `omnigent` | Same executor type as the supervisor. |
| `executor.model` | `databricks-claude-sonnet-4-6` | Same model as the supervisor but running as a separate agent session. |
| `executor.config.harness` | `claude-sdk` | Same harness as the supervisor. |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as the other agents. |
| `guardrails.policies.cost_guard` | `cost_budget`, $1.00 max, $0.25 ASK | Per-invocation cost cap — prevents a single review_worker call from running away. |
| `guardrails.policies.daily_cost_guard` | `user_daily_cost_budget`, $5.00 max, $0.50 ASK | Daily cost cap — shared across all agents in the session tree. |

---

## `guardrails:` — Cost governance

This config uses **layered cost governance** — no labels, no taint, no deny policies. Cost is controlled at two levels:

### Supervisor guardrails (session-wide daily budget)

```yaml
guardrails:
  policies:
    daily_cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.user_daily_cost_budget
        arguments:
          max_cost_usd: 5.0
          ask_thresholds_usd: [0.50]
```

| Attribute | Role |
|---|---|
| `function.path` | `omnigent.policies.builtins.cost.user_daily_cost_budget` — built-in daily cost tracker that evaluates on every turn. Tracks cumulative spend per user per day. |
| `max_cost_usd` | Hard cap — session terminates if daily cost exceeds $5.00. |
| `ask_thresholds_usd` | `[0.50]` — pause and ask the user for approval when daily cost crosses $0.50. |

### Sub-agent guardrails (per-invocation + daily budget)

Each sub-agent (`impl_worker`, `review_worker`) has **two** policies:

```yaml
guardrails:
  policies:
    cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.cost_budget
        arguments:
          max_cost_usd: 1.0
          ask_thresholds_usd: [0.25]
    daily_cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.user_daily_cost_budget
        arguments:
          max_cost_usd: 5.0
          ask_thresholds_usd: [0.50]
```

| Policy | Function | Role |
|---|---|---|
| `cost_guard` | `cost_budget` | Per-invocation cap — a single sub-agent call terminates at $1.00, asks at $0.25. Prevents any one agent from running away on a single task. |
| `daily_cost_guard` | `user_daily_cost_budget` | Daily cap — cumulative spend across all agents terminates at $5.00, asks at $0.50. Same policy as the supervisor, tracked at the user level. |

**Why two levels?** The per-invocation `cost_guard` ($1.00) catches runaway sub-agents early — if an implementation task loops on test failures, it stops before burning through the daily budget. The `daily_cost_guard` ($5.00) provides the session-wide ceiling across all agents and both providers.

**Why $5.00 daily and $1.00 per-invocation?** Three LLMs, two providers. One implement-test-review cycle can cost $0.50–1.00. The $1.00 per-invocation cap allows one full cycle per sub-agent call. The $5.00 daily cap allows multiple revision cycles across a working session.

**Why no labels or taint policies?** All three agents need full read/write access to the same files — there are no natural information-flow boundaries. See [secure_code_assistant](../secure_code_assistant/) and [telco_customer_agent](../telco_customer_agent/) for taint/deny examples.

**Scope:** The `daily_cost_guard` tracks spend across the entire session tree — supervisor, impl_worker, and review_worker all contribute to one cumulative daily budget across both providers. The `cost_guard` is scoped to each individual sub-agent invocation.

---

## What's NOT in this config

Compared to the secure_code_assistant and telco examples, this config has:
- **No labels** — no taint tracking (cost governance only)
- **No taint/deny policies** — no information flow control
- **No builtins** — no `web_search`

---

## Nesting summary

```
cross_harness_coding/
+-- config.yaml               # SUPERVISOR config
|   +-- spec_version          # schema version
|   +-- name                  # agent identifier
|   +-- description           # human-readable summary
|   +-- executor              # SUPERVISOR's LLM config
|   |   +-- type
|   |   +-- model
|   |   +-- config.harness
|   +-- prompt                # SUPERVISOR's system prompt
|   +-- os_env                # SUPERVISOR's filesystem access
|   |   +-- type
|   |   +-- cwd
|   |   +-- sandbox.type
|   +-- tools                 # SUPERVISOR's callable tools
|   |   +-- agents: [impl_worker, review_worker]
|   +-- guardrails            # session-scoped governance
|       +-- policies
|           +-- daily_cost_guard  # daily budget: $5.00 max, $0.50 ASK
+-- agents/
|   +-- impl_worker/
|   |   +-- config.yaml       # IMPL's config (harness: codex)
|   |       +-- guardrails
|   |           +-- cost_guard        # per-invocation: $1.00 max, $0.25 ASK
|   |           +-- daily_cost_guard  # daily budget: $5.00 max, $0.50 ASK
|   +-- review_worker/
|       +-- config.yaml       # REVIEWER's config (harness: claude-sdk)
|           +-- guardrails
|               +-- cost_guard        # per-invocation: $1.00 max, $0.25 ASK
|               +-- daily_cost_guard  # daily budget: $5.00 max, $0.50 ASK
```

Each sub-agent is a fully self-contained agent definition in its own directory under `agents/`. They get their own model, harness, prompt, and environment — the only thing they share with the supervisor is the session tree.

---

## What is the session tree?

The **session tree** is the hierarchical session structure that ties the supervisor and its sub-agents together:

```
Session: cross_harness_coding (root)
+-- supervisor turn 1
|   +-- impl_worker (child session)   <-- spawned as tool call
|   +-- review_worker (child session) <-- spawned as tool call
+-- supervisor turn 2
|   +-- impl_worker (child session)   <-- revision pass
...
```

**Shared across the tree:**

- **Session identity** — one session ID for the whole conversation (`omnigent attach`, logs, Web UI)
- **Filesystem** — all agents see the same CWD, so impl_worker writes files and review_worker reads them
- **Policy state** — `daily_cost_guard` tracks cumulative daily cost across all sub-agent sessions; per-invocation `cost_guard` is scoped to each sub-agent call
- **Conversation history** — the supervisor's transcript includes sub-agent calls and results

**Not shared:**

- **Context window** — each sub-agent has its own context and system prompt; the reviewer only sees what the supervisor passes as the tool call argument
- **Executor** — each agent talks to its own LLM provider independently

The session tree is what makes cross-harness delegation feel like one conversation, even though three different LLM sessions are involved.
