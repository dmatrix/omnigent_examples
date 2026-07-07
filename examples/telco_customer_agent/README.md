# Telco Customer Agent with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**Multi-tool customer data agent with 9 policies: taint labels, cost governance, PII leak prevention, stateful risk scoring, and a custom bulk access guard.**

![Telco Customer Agent Architecture](images/telco_customer_agent_architecture.svg)

---

## Overview

The telco agent demonstrates **governance** — Omnigent's ability to enforce data access boundaries that the LLM cannot override. Nine policies across five categories show the full range of what the PolicyEngine can do:

- **Taint labels + information flow** — when the agent reads customer PII or financial data, the session is tainted with monotonic labels and web search is blocked to prevent data leakage.
- **Cost governance** — a session-level cost budget caps LLM spend and ASKs for approval at configurable thresholds.
- **PII leak prevention** — outgoing LLM messages are scanned for SSN, email, and phone patterns before reaching the model.
- **Stateful risk scoring** — each tool call accumulates risk points; when the score crosses a threshold, sensitive tools require human approval.
- **Custom policy** — a bulk access guard (written in Python) tracks distinct customer records accessed and ASKs after the configured limit.

Unlike prompt-based guardrails, all nine policies are enforced at the framework layer — the tool call is denied or paused before it reaches the model. The agent also demonstrates **portability** — the same policies fire identically on Claude, GPT, or any supported harness.

It has three database tools and one builtin:

- **`query_plans`** -- Queries public plan/pricing data (5 plans mirroring real carrier tiers). Adds 1 risk point per call.

- **`query_customers`** -- Queries the customers and devices tables (20 customers with PII: names, emails, phone numbers, SSN last-4, IMEI). Triggers `has_pii`, adds 3 risk points, and increments the bulk access counter.

- **`query_billing`** -- Queries the billing and subscriptions tables (60 billing records across 3 months, 20 subscriptions with revenue, discounts, payment status). Triggers `has_financial`, adds 5 risk points, and increments the bulk access counter.

- **`web_search`** -- Builtin web search for external/competitor/market questions. Blocked after PII or financial data access.

The agent also includes a **`customer-report` skill** (`skills/customer-report/SKILL.md`) that generates structured quarterly business reviews with PII redaction rules. The skill is loaded on demand via `load_skill` when the user requests a report.

The prompt enforces **strict tool usage** -- the agent must use tools for every answer and declines out-of-scope questions rather than answering from training data.

See the [design doc](design.md) for the full design, policy rationale, and staged implementation plan.

---

## Get Started

Build the database:

```bash
python examples/tools/create_telco_db.py
```

This creates `examples/tools/data/telco.db` with 5 tables and 125 records.

---

## Run on Databricks

Override the model to route through Databricks AI Gateway:

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/telco_customer_agent/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

The CLI opens an interactive REPL. A Web UI is also available at the Databricks Apps URL.

---

## Run Locally

The default config uses `claude-sonnet-4-6` via direct Anthropic API (`claude-sdk` harness). Runs fully on your machine with no Databricks dependency.

### 1. Configure credentials (one-time)

```bash
omnigent setup
```

### 2. Export your API key

```bash
# Default harness is claude-sdk — needs ANTHROPIC_API_KEY
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
```

### 3. Run the agent

```bash
# Default: claude-sonnet-4-6 via claude-sdk
omnigent run examples/telco_customer_agent/

# Override with OpenAI models (requires OPENAI_API_KEY)
export $(grep OPENAI_API_KEY .env | tr -d '"')
omnigent run examples/telco_customer_agent/ --model gpt-5.5 --harness openai-agents
omnigent run examples/telco_customer_agent/ --model gpt-5.4 --harness openai-agents

# Fresh session (no persistence)
omnigent run examples/telco_customer_agent/ --no-session
```

---

## Example Queries

**Plans** (public data -- no labels triggered):
```
What plans are available and what do they cost?
Compare the Experience More and Experience Beyond plans
```

**Customers** (PII data -- triggers `has_pii`):
```
List all customers in California with their phone numbers
Show me customers whose contracts expire in the next 90 days
```

**Billing** (financial data -- triggers `has_financial`):
```
What's our total monthly revenue across all plans?
Which customers have overage charges this month?
Show me all past-due accounts with amounts owed
```

**Web search denied** (after PII or financial data access):
```
Search the web for competitor pricing on unlimited family plans
→ BLOCKED: "Web search blocked — customer PII is in session context."
```

**PII leak prevention** (flags PII patterns in outgoing messages):
```
Show me customer CUST-1001's full details
→ ASK: agent flags SSN/email/phone patterns before sending to the model
```

**Risk score accumulation** (stateful risk tracking across turns):
```
Show me CUST-1001's billing history
Show me CUST-1002's billing history
Show me CUST-1003's billing history
→ ASK: "Risk score exceeded — multiple sensitive data accesses in this session."
```

**Bulk access guard** (custom policy -- distinct customer count, query one per turn):
```
Show me CUST-1001's account details
Show me CUST-1002's account details
Show me CUST-1003's account details
Show me CUST-1004's account details
→ ASK on the 4th: "Bulk access guard: this session has accessed 4 distinct customer records (limit: 3). Continue?"
```

**Skill** (on-demand structured report):
```
Use the customer-report skill to produce a quarterly business review
```

**Out-of-scope** (strict tool enforcement -- should decline):
```
What's the weather in San Francisco?
→ "I can only help with telco customer data questions."
```

---

## Policy Engine

The agent's `config.yaml` defines session-scoped guardrails across five categories: information flow (taint labels + deny rules), cost governance, PII leak prevention, stateful risk scoring, and a custom bulk access guard.

### Labels

| Label | Triggered by | Monotonic |
|---|---|---|
| `has_pii` | `query_customers` | Yes (once set, cannot be unset) |
| `has_financial` | `query_billing` | Yes |
| `used_web` | `web_search` | Yes |

### Policies

| Policy | Type | Action | Description |
|---|---|---|---|
| `block_web_after_pii` | Taint/deny | DENY `web_search` | Blocks web search when PII is in session context |
| `block_web_after_financial` | Taint/deny | DENY `web_search` | Blocks web search when financial data is in session context |
| `cost_budget` | Builtin | ASK at $1.00, DENY at $5.00 | Session-level cost cap across all LLM calls |
| `deny_pii_in_llm_request` | Builtin | ASK | Scans outgoing messages for SSN, email, and phone patterns |
| `risk_score` | Builtin | ASK | Accumulates risk points per tool call (query_billing: 5, query_customers: 3, query_plans: 1). ASKs when score exceeds 10 |
| `bulk_access_guard` | Custom | ASK | Tracks distinct customer IDs accessed. ASKs after 3 unique customers |

### Custom policy: `bulk_access_guard`

Located at `policies/bulk_access_guard.py`, this is a custom policy that demonstrates Omnigent's policy authoring pattern:

- **Factory function** -- takes `max_customers` as a configurable argument
- **Session state** -- tracks distinct customer IDs (CUST-XXXX) seen across turns via `session_state`
- **POLICY_REGISTRY** -- exports metadata so the framework can discover and validate the policy

The policy extracts customer ID patterns from tool call arguments, maintains a deduplicated set in session state, and ASKs for approval when the count exceeds the configured limit. This prevents bulk data exfiltration by flagging when an agent accesses too many customer records in a single session.

---

## How to Demo (15-18 min)

### Act 1: The YAML (3 min) — "Nine policies, five categories, one file"

**Show** `config.yaml` — scroll through the labels and policies:

**Say:** "This agent has three tools that query a telco database — plans, customers, and billing. The YAML defines nine policies across five categories: taint labels that track what data the agent has seen, DENY policies that block web search after sensitive data access, a cost budget, a PII leak scanner, a stateful risk score, and a custom bulk access guard. All declarative, all enforced at the framework layer."

**Pause on the `block_web_after_pii` policy:**
> "This is one YAML block. It says: if `has_pii` is true, deny `web_search`. The LLM never gets a vote."

**Pause on the `risk_score` policy:**
> "This one accumulates points — 5 for billing, 3 for customer data, 1 for plans. Once the score hits 10, the agent has to ask for permission. It's stateful — no single query triggers it, but a pattern of sensitive access does."

---

### Act 2: Safe queries (2 min) — "Public data, no restrictions"

**Run:** `omnigent run examples/telco_customer_agent/ --no-session`

**Prompt:**
```
What plans are available and what do they cost?
```

**Watch:** The agent calls `query_plans` and returns pricing data. No labels triggered, risk score goes from 0 to 1.

**Say:** "Plan data is public — no PII, no financial data. The agent answers freely. The risk score ticked up by 1, but we're nowhere near the threshold."

---

### Act 3: The taint (4 min) — "One query changes everything"

**Prompt:**
```
List all customers in California with their phone numbers
```

**Watch:** The agent calls `query_customers`. The `has_pii` label is now set, risk score jumps by 3.

**Say:** "The agent just read customer names, emails, phone numbers, and SSN last-4. The session is now tainted with PII. Watch what happens next."

**Prompt:**
```
Use web_search to find T-Mobile's current pricing
```

**Watch:** The agent attempts `web_search` → DENIED.

**Say:** "The search query 'T-Mobile pricing' is completely clean — no PII in it. But Omnigent knows this session has seen customer data. The framework blocks the call before it reaches the LLM. This is what session-scoped governance means — AI Gateway can't do this because it's stateless per-request."

---

### Act 4: Risk score escalation (3 min) — "The pattern matters"

**Start a fresh session:** `omnigent run examples/telco_customer_agent/ --no-session`

**Prompt:**
```
Show me CUST-1001's billing history
```

**Watch:** Risk score: +5 (billing). No ASK yet.

**Prompt:**
```
Show me CUST-1002's billing history
```

**Watch:** Risk score: +5 more = 10, crosses threshold → ASK fires.

**Say:** "No single query triggered this — it's the accumulation. Two billing queries in a row pushed the risk score to 10. The framework sees a pattern of sensitive access and pauses for human approval. A static per-request rule can't do this — it requires session state."

---

### Act 5: Bulk access guard (2 min) — "Too many customers"

**Continue the session (approve the ASK), then:**

**Prompt:**
```
Now look up CUST-1003's account details
```

**Then:**
```
Look up CUST-1004's account details
```

**Watch:** On the 4th distinct customer → ASK: "Bulk access guard: this session has accessed 4 distinct customer records (limit: 3). Continue?"

**Say:** "This is a custom policy — 30 lines of Python. It tracks distinct customer IDs across the session and ASKs when you've accessed more than 3. This is the 'write your own policy' pattern — factory function, session state, POLICY_REGISTRY export. Everything a developer needs to build org-specific rules."

---

### Act 6: The contrast (2 min) — "Order matters"

**Start a fresh session:** `omnigent run examples/telco_customer_agent/ --no-session`

**Prompt:**
```
Use web_search to find T-Mobile's current unlimited plan prices
```

**Watch:** Web search succeeds — no taint yet.

**Say:** "Same query that was blocked before. But this time we searched before touching customer data — so it works. Labels are monotonic — once set, they can't be unset. The order matters."

---

### Act 7: Strict tool enforcement (1 min) — "Out of scope"

**Prompt:**
```
What's the weather in San Francisco?
```

**Watch:** The agent declines — "I can only help with telco customer data questions."

**Say:** "The agent won't answer from training data. Every answer must come from a tool. Out-of-scope questions are declined, not hallucinated."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 3 min | Nine policies, five categories, declarative governance |
| 2. Safe queries | 2 min | Public plan data — no restrictions |
| 3. The taint | 4 min | PII taint → web search denied |
| 4. Risk score | 3 min | Stateful risk accumulation across turns |
| 5. Bulk access | 2 min | Custom policy — distinct customer count |
| 6. The contrast | 2 min | Web search works before data access, blocked after |
| 7. Out of scope | 1 min | Strict tool enforcement — declines unrelated questions |
| **Total** | **17 min** | |

---

## Database

The agent queries `examples/tools/data/telco.db` — 5 tables (plans, customers, devices, subscriptions, billing) with 125 records. Rebuild with `python examples/tools/create_telco_db.py`. See the create script for the full schema.
