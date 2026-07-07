# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Detailed breakdown of every attribute in `config.yaml`, its role, scope, and nesting.

---

## Top-level metadata (lines 1-6)

| Attribute | Value | Role |
|---|---|---|
| `spec_version` | `1` | Schema version of the Omnigent agent YAML spec. Tells the framework which parser to use. |
| `name` | `telco_customer_agent` | Unique identifier for this agent. Used in session logs, CLI output, and the `omnigent run` resolver. |
| `description` | `Telco customer data agent with plan, customer, and billing tools.` | Human-readable summary. Shown in `omnigent list` and the Web UI agent picker. |

---

## `executor:` — The agent's brain

Tells the framework which LLM provider and model to use.

| Attribute | Value | Role |
|---|---|---|
| `type` | `omnigent` | The executor type. `omnigent` means the framework manages the agent loop (tool dispatch, session state, policy evaluation). |
| `model` | `claude-sonnet-4-6` | Which model to call. Can be overridden at the CLI with `--model`. |
| `config.harness` | `claude-sdk` | Which SDK/protocol adapter to use for API calls. `claude-sdk` = Anthropic's native API. Can be overridden with `--harness`. |

---

## `os_env:` — Environment access

Grants the agent access to the host operating system (shell, filesystem).

| Attribute | Value | Role |
|---|---|---|
| `type` | `caller_process` | Inherit the environment of the process that launched `omnigent run`. The agent sees the same filesystem, env vars, and CWD as your terminal. |
| `cwd` | `.` | Working directory. `.` = wherever you ran `omnigent run` from (typically the repo root). |
| `sandbox.type` | `none` | No sandboxing — the agent can read/write anywhere the calling process can. Other options include `docker` or `firecracker` for isolation. |

---

## `tools:` — Available tools

### What's declared in config.yaml

The only tool explicitly declared in the YAML is a single builtin:

```yaml
tools:
  builtins:
    - web_search
```

| Tool | Role |
|---|---|
| `web_search` | Framework-provided web search. Listed here to make it available to the agent and targetable by DENY policies. |

Builtins are tools the Omnigent framework ships out of the box — no Python code required. Listing a builtin in `tools.builtins` makes it callable by the agent.

### Tools NOT in config.yaml (auto-discovered by the framework)

The agent has three additional Python tools that don't appear in the YAML. These are important for understanding the policies, which reference tool names like `query_customers` and `query_billing` that you won't find declared in `config.yaml`.

**Auto-discovered Python tools** — Any `.py` file in `tools/python/` with an `@tool`-decorated function is automatically registered at load time:

| File | Tool function | Why it matters |
|---|---|---|
| `tools/python/query_plans.py` | `query_plans` | Referenced by `risk_score` (1 point per call) — public data, no taint labels |
| `tools/python/query_customers.py` | `query_customers` | Referenced by the `taint_pii` policy (`on_tools: [query_customers]`) |
| `tools/python/query_billing.py` | `query_billing` | Referenced by the `taint_financial` policy (`on_tools: [query_billing]`) |

**Key takeaway:** The policies in `guardrails:` reference tool names (`query_customers`, `query_billing`, `web_search`) that include auto-discovered tools never declared in the `tools:` block. This works because the framework resolves tool names at runtime — auto-discovered tools are registered alongside explicitly declared builtins. The policy engine can target any of them.

---

## `guardrails:` — Session-scoped governance

This is the section that distinguishes this example from a bare LLM agent. The guardrails block defines **labels** (session state) and **9 policies** across five categories: taint/deny (information flow), cost governance, PII leak prevention, stateful risk scoring, and a custom bulk access guard.

### `guardrails.labels:` — Session state tracking

```yaml
guardrails:
  labels:
    has_pii:
      initial: "False"
      values: ["False", "True"]
      monotonic: increasing
    has_financial:
      initial: "False"
      values: ["False", "True"]
      monotonic: increasing
    used_web:
      initial: "False"
      values: ["False", "True"]
      monotonic: increasing
```

Labels are **session-scoped variables** that track what the agent has seen or done. Each label has:

| Attribute | Role |
|---|---|
| `initial` | Starting value when a new session begins. All three start as `"False"`. |
| `values` | Ordered list of allowed values. The ordering matters for `monotonic`. |
| `monotonic: increasing` | The label can only move forward in the `values` list — from `"False"` to `"True"`, never back. Once set, it cannot be unset for the rest of the session. |

**Why monotonic?** This is the core of session-scoped governance. If the agent reads customer PII in turn 2, that fact persists for the entire session. There's no way for the model to "forget" it saw PII — the label is a one-way latch. This is what makes Omnigent's taint tracking different from stateless request-level scanning (like an API gateway).

| Label | What it tracks |
|---|---|
| `has_pii` | The agent has read customer PII (names, emails, phone numbers, SSN last-4) |
| `has_financial` | The agent has read financial data (billing, revenue, discounts, payment status) |
| `used_web` | The agent has used web search (external content in session) |

---

### `guardrails.policies:` — Rules that evaluate on every tool call

Policies are evaluated by the PolicyEngine on every tool call. They run **before** the tool executes — the LLM never gets a vote.

In the YAML, the nine policies are organized into four groups by implementation pattern: **taint policies** (set labels), **deny policies** (block tool calls), **builtin policies** (cost, PII, risk), and a **custom policy** (bulk access guard).

#### Taint policies — Tag session state on tool access

```yaml
taint_pii:
  type: function
  function:
    path: omnigent.policies.function.make_fixed_action_callable
    arguments:
      action: allow
      set_labels:
        has_pii: "True"
      on_phases: [tool_call]
      on_tools: [query_customers]
  set_labels: [has_pii]
```

| Attribute | Role |
|---|---|
| `type: function` | This policy is implemented as a Python callable, not a static rule. |
| `function.path` | Dotted import path to the policy factory. `make_fixed_action_callable` is a built-in that returns a fixed action (allow/deny) with optional label side-effects. |
| `function.arguments.action` | `allow` — the tool call proceeds. The policy's purpose is the side-effect (setting labels), not blocking. |
| `function.arguments.set_labels` | Labels to set when this policy fires. `has_pii: "True"` latches the PII taint. |
| `function.arguments.on_phases` | `[tool_call]` — evaluate this policy during the tool_call phase (before the tool executes). |
| `function.arguments.on_tools` | `[query_customers]` — only evaluate when this specific tool is called. |
| `set_labels` (top-level) | Declares which labels this policy can modify. Used by the framework for dependency analysis. |

The three taint policies follow the same pattern:

| Policy | Fires on | Sets |
|---|---|---|
| `taint_pii` | `query_customers` | `has_pii: "True"` |
| `taint_financial` | `query_billing` | `has_financial: "True"` |
| `taint_web` | `web_search` | `used_web: "True"` |

#### Deny policies — Block tool calls based on session state

```yaml
block_web_after_pii:
  type: function
  condition:
    has_pii: "True"
  function:
    path: omnigent.policies.function.make_fixed_action_callable
    arguments:
      action: deny
      reason: |
        Web search blocked — customer PII (names, emails, phone numbers, SSN)
        is in session context. Search queries could leak identity data.
      on_phases: [tool_call]
      on_tools: [web_search]
```

| Attribute | Role |
|---|---|
| `condition` | **Pre-condition**: this policy only activates when `has_pii` is `"True"`. If the label is still `"False"`, the policy is skipped entirely. |
| `function.arguments.action` | `deny` — the tool call is blocked. The framework returns the `reason` message to the model instead of executing the tool. |
| `function.arguments.reason` | Human-readable explanation returned to the LLM (and shown to the user) when the tool call is denied. |
| `function.arguments.on_phases` | `[tool_call]` — intercept during the tool_call phase, before execution. |
| `function.arguments.on_tools` | `[web_search]` — only block web_search, not other tools. |

The two deny policies:

| Policy | Condition | Blocks | Why |
|---|---|---|---|
| `block_web_after_pii` | `has_pii = True` | `web_search` | PII in session could leak via search queries |
| `block_web_after_financial` | `has_financial = True` | `web_search` | Financial data in session could leak |

**How policies compose:** Both deny policies target `web_search`. If either `has_pii` or `has_financial` is true, web search is blocked. The taint policies fire first (they ALLOW with side-effects), then the deny policies evaluate against the updated labels. This means calling `query_customers` and `web_search` in the same turn will still block — the taint fires before the deny evaluates.

#### Cost governance — Session-level budget

```yaml
cost_budget:
  type: function
  function:
    path: omnigent.policies.builtins.cost.cost_budget
    arguments:
      max_cost_usd: 5.0
      ask_thresholds_usd: [1.00]
```

| Attribute | Role |
|---|---|
| `function.path` | Built-in cost tracking policy. Accumulates LLM spend (USD) across the session. |
| `max_cost_usd` | Hard limit — DENYs further tool calls at $5.00. The session stays alive; switch models or start fresh to continue. |
| `ask_thresholds_usd` | `[1.00]` — pause and ask the user for approval when spend crosses $1.00. |

**Why:** The telco agent makes multiple tool calls per question (query + follow-up). Without a cost cap, a long conversation could run away. The ASK threshold fires early to keep the user informed.

#### PII leak prevention — Outgoing message scanning

```yaml
deny_pii_in_llm_request:
  type: function
  function:
    path: omnigent.policies.builtins.safety.deny_pii_in_llm_request
    arguments:
      pii_types: [ssn, email, phone]
      action: ASK
```

| Attribute | Role |
|---|---|
| `function.path` | Built-in PII scanner. Evaluates on `llm_request` phase — before the message is sent to the model. |
| `pii_types` | Pattern categories to scan for: SSN patterns, email addresses, phone numbers. |
| `action` | `ASK` — pause for user approval instead of hard-blocking. The user can approve if the PII exposure is intentional. |

**Why:** The taint labels prevent PII from leaking *out* via web search, but they don't prevent PII from being sent *to* the LLM in user messages or system prompts. This policy adds the complementary guard — scanning outgoing messages for PII patterns before they reach the model. Together, taint labels and PII scanning cover both directions of the data flow.

#### Stateful risk scoring — Accumulative session risk

```yaml
risk_score:
  type: function
  function:
    path: omnigent.policies.builtins.risk_score.risk_score_policy
    arguments:
      threshold: 10
      tool_points:
        query_customers: 3
        query_billing: 5
        query_plans: 1
      guarded_tools: [query_customers, query_billing]
      escalate_action: ASK
      reason: "Risk score exceeded — multiple sensitive data accesses in this session."
```

| Attribute | Role |
|---|---|
| `function.path` | Built-in risk score accumulator. Uses `session_state` to persist the score across turns. |
| `threshold` | Score at which `guarded_tools` escalate. `10` = roughly 2 billing queries or 3 customer queries. |
| `tool_points` | Points added per tool call. `query_billing` (5) is weighted higher than `query_customers` (3) because financial data is more sensitive. `query_plans` (1) adds minimal risk. |
| `guarded_tools` | Tools that require approval once the threshold is crossed. Only `query_customers` and `query_billing` are gated — `query_plans` remains unrestricted. |
| `escalate_action` | `ASK` — pause for human approval, not hard deny. |
| `reason` | Message shown to the user when the threshold fires. |

**Why:** The taint labels are binary (on/off) — they can't express *how much* sensitive data the agent has touched. The risk score adds a quantitative dimension: one billing query is fine, but querying 3 customers' billing in a row is a pattern worth flagging. This is the first *stateful* policy in the example — it accumulates across turns and can't be expressed as a static rule.

#### Custom policy — Bulk access guard

```yaml
bulk_access_guard:
  type: function
  function:
    path: examples.telco_customer_agent.policies.bulk_access_guard.bulk_access_guard
    arguments:
      max_customers: 3
```

| Attribute | Role |
|---|---|
| `function.path` | Dotted path to a custom Python module in `policies/bulk_access_guard.py`. The framework imports it at load time. |
| `max_customers` | Configurable limit — ASK after this many distinct customers are accessed. |

**Why:** This is the "write your own policy" example. It demonstrates four things a developer needs to know:

1. **Factory pattern** — the function takes arguments and returns a policy callable
2. **Session state** — the callable reads/writes `session_state` to track customer IDs across turns
3. **Pattern extraction** — it uses regex to find `CUST-XXXX` patterns in tool call arguments
4. **POLICY_REGISTRY** — the module exports a registry list so the framework can discover and validate the policy

The use case is real: preventing bulk data exfiltration by flagging when an agent accesses too many distinct customer records. The implementation is ~30 lines.

---

## `prompt:` — The agent's system prompt

A `|` literal block (preserves newlines). The system message sent to the model on every turn. Key directives:

1. **Strict tool usage** — "You MUST use your tools to answer every question. You are FORBIDDEN from answering from your training data."
2. **Failure reporting** — "If a tool call fails, report the error — do NOT fall back to your own knowledge."
3. **Scope enforcement** — "If a question is outside your scope, say 'I can only help with telco customer data questions' and stop."
4. **Tool routing** — Maps question types to tools (plans -> `query_plans`, customers -> `query_customers`, billing -> `query_billing`, external -> `web_search`)
5. **Schema reference** — Full column definitions for all five tables, plus common JOIN patterns

The prompt is long (~100 lines) because it includes the database schema. This gives the model enough context to write correct SQL without needing to introspect the database at runtime.

---

## What's NOT in this config

- **No sub-agents** — unlike cross_harness_coding, this is a single-agent config. All tools are Python functions or builtins, not `type: agent` declarations.
- **No `os_env` write access needed** — the agent reads from SQLite and the web, but doesn't write files. The `os_env` is declared for shell access (grep, find, etc.) but the agent's prompt doesn't instruct it to use the filesystem.

---

## Nesting summary

```
config.yaml
+-- spec_version              # schema version
+-- name                      # agent identifier
+-- description               # human-readable summary
+-- executor                  # LLM config
|   +-- type
|   +-- model
|   +-- config.harness
+-- os_env                    # filesystem/shell access
|   +-- type
|   +-- cwd
|   +-- sandbox.type
+-- tools                     # callable tools
|   +-- builtins              # framework-provided tools
|       +-- web_search
+-- guardrails                # session-scoped governance
|   +-- labels                # session state variables
|   |   +-- has_pii           # PII taint (monotonic)
|   |   +-- has_financial     # financial taint (monotonic)
|   |   +-- used_web          # web search taint (monotonic)
|   +-- policies              # rules evaluated on every tool call
|       +-- taint_pii                  # ALLOW query_customers, set has_pii
|       +-- taint_financial            # ALLOW query_billing, set has_financial
|       +-- taint_web                  # ALLOW web_search, set used_web
|       +-- block_web_after_pii        # DENY web_search if has_pii
|       +-- block_web_after_financial   # DENY web_search if has_financial
|       +-- cost_budget                # ASK at $1.00, DENY at $5.00
|       +-- deny_pii_in_llm_request    # ASK on SSN/email/phone in outgoing messages
|       +-- risk_score                 # ASK when cumulative risk score exceeds 10
|       +-- bulk_access_guard          # ASK after 3+ distinct customer records
+-- prompt                    # system prompt (strict tool usage + schema)
```

---

## Policy evaluation flow

When the agent calls a tool, the PolicyEngine evaluates policies in order. Here are two representative flows:

### Flow 1: `web_search` after PII access

```
Agent calls web_search
        |
        v
Phase: tool_call
        |
        v
1. taint_web fires              --> ALLOW, set used_web = True
2. block_web_after_pii?         --> check has_pii label
   - if True  --> DENY (return reason to model, tool never executes)
   - if False --> skip
3. block_web_after_financial?   --> check has_financial label
   - if True  --> DENY
   - if False --> skip
4. cost_budget                  --> check cumulative spend
   - if over $1.00 --> ASK
   - if over $5.00 --> DENY
5. risk_score                   --> add 0 points (web_search has no tool_points)
        |
        v
All policies passed? --> tool executes
```

### Flow 2: `query_billing` with accumulated risk

```
Agent calls query_billing(CUST-1003)
        |
        v
Phase: tool_call
        |
        v
1. taint_financial fires        --> ALLOW, set has_financial = True
2. cost_budget                  --> check cumulative spend
3. deny_pii_in_llm_request      --> scan args for PII patterns (SSN/email/phone)
4. risk_score                   --> add 5 points, check threshold
   - if score >= 10 --> ASK ("Risk score exceeded")
5. bulk_access_guard            --> extract CUST-1003, add to seen set
   - if distinct count > 3 --> ASK ("Bulk access guard")
        |
        v
All policies passed? --> tool executes
```

Taint policies always fire (no condition). Deny policies only activate when their condition label is `"True"`. Stateful policies (risk_score, bulk_access_guard) accumulate state and may escalate on any call. The first DENY or unresolved ASK is final — the model receives the reason string and must respond without the tool result.
