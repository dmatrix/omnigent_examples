# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Attribute-level breakdown of `config.yaml` for the telco customer agent.

---

## Executor

| Attribute | Value | Notes |
|---|---|---|
| `model` | `claude-sonnet-4-6` | Override with `--model` at the CLI. |
| `config.harness` | `claude-sdk` | Override with `--harness`. |

## OS Environment

Declares `os_env: caller_process` with `cwd: .` and `sandbox: none` — the agent inherits the calling shell's filesystem and env vars.

---

## Tools

The only tool explicitly declared in YAML is `web_search` (a framework builtin). Three additional tools are **auto-discovered** from `tools/python/`:

| File | Tool | Policy relevance |
|---|---|---|
| `tools/python/query_plans.py` | `query_plans` | `risk_score` (1 point per call) — public data, no taint labels |
| `tools/python/query_customers.py` | `query_customers` | `taint_pii` sets `has_pii`; `risk_score` adds 3 points |
| `tools/python/query_billing.py` | `query_billing` | `taint_financial` sets `has_financial`; `risk_score` adds 5 points |

Policies reference these auto-discovered tool names even though they never appear in the `tools:` block — the framework resolves all tool names at runtime.

---

## Guardrails: Labels

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

Labels are session-scoped variables. `monotonic: increasing` means they can only move forward in the `values` list — once `"True"`, they stay `"True"` for the rest of the session. This is a one-way latch: the model cannot "forget" that PII was accessed. This is what distinguishes Omnigent's taint tracking from stateless request-level scanning.

| Label | Tracks |
|---|---|
| `has_pii` | Agent read customer PII (names, emails, phones, SSN last-4) |
| `has_financial` | Agent read financial data (billing, revenue, discounts, payment status) |
| `used_web` | Agent used web search (external content in session) |

---

## Guardrails: Policies

Nine policies in four groups.

### Taint policies — set labels on tool access

All use `make_fixed_action_callable` with `action: allow` + `set_labels`. The tool call proceeds; the side-effect is the label update.

| Policy | Fires on | Sets |
|---|---|---|
| `taint_pii` | `query_customers` | `has_pii: "True"` |
| `taint_financial` | `query_billing` | `has_financial: "True"` |
| `taint_web` | `web_search` | `used_web: "True"` |

### Deny policies — block tool calls based on session state

Same `make_fixed_action_callable`, but with `action: deny` and a `condition` pre-check. The policy is skipped entirely when its condition label is still `"False"`.

| Policy | Condition | Blocks | Reason |
|---|---|---|---|
| `block_web_after_pii` | `has_pii = True` | `web_search` | PII in session could leak via search queries |
| `block_web_after_financial` | `has_financial = True` | `web_search` | Financial data in session could leak |

Both target `web_search`. If either label is true, web search is blocked. Taint policies fire first (ALLOW with side-effects), then deny policies evaluate against updated labels — so calling `query_customers` and `web_search` in the same turn still blocks.

### Cost governance

```yaml
cost_budget:
  type: function
  function:
    path: omnigent.policies.builtins.cost.cost_budget
    arguments:
      max_cost_usd: 5.0
      ask_thresholds_usd: [1.00]
```

Accumulates LLM spend across the session. ASKs at $1.00, DENYs at $5.00.

### PII leak prevention

```yaml
deny_pii_in_llm_request:
  type: function
  function:
    path: omnigent.policies.builtins.safety.deny_pii_in_llm_request
    arguments:
      pii_types: [ssn, email, phone]
      action: ASK
```

Evaluates on `llm_request` phase — scans outgoing messages for PII patterns before they reach the model. Complements the taint labels: taint blocks PII from leaking *out* via web search; this blocks PII from being sent *to* the model.

### Risk score — stateful accumulation

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

Persists score in `session_state` across turns. `query_billing` (5 pts) is weighted higher than `query_customers` (3 pts). Once the threshold is crossed, `guarded_tools` require approval — `query_plans` stays unrestricted. This adds a quantitative dimension that binary taint labels can't express.

### Custom policy: `bulk_access_guard`

```yaml
bulk_access_guard:
  type: function
  function:
    path: examples.telco_customer_agent.policies.bulk_access_guard.bulk_access_guard
    arguments:
      max_customers: 3
```

Custom Python policy in `policies/bulk_access_guard.py` (~30 lines). Demonstrates the authoring pattern:
1. **Factory function** — takes `max_customers`, returns a policy callable
2. **Session state** — reads/writes `session_state` to track customer IDs across turns
3. **Pattern extraction** — regex finds `CUST-XXXX` in tool call arguments
4. **`POLICY_REGISTRY`** — module exports metadata for framework discovery

ASKs when distinct customer count exceeds the limit. Prevents bulk data exfiltration.

---

## Prompt

The system prompt (~100 lines) enforces strict tool usage ("FORBIDDEN from answering from training data"), maps question types to tools, and includes full column definitions for all 5 tables plus common JOIN patterns. The schema is inline so the model can write correct SQL without introspecting the database.

---

## Not in this config

No sub-agents (single-agent config). No `os_env` write tools needed — the agent reads from SQLite and the web.

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
