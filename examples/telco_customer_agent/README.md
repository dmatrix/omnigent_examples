# Telco Customer Agent with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**Multi-tool customer data agent with nine contextual and session-based policies: taint labels, cost governance, PII leak prevention, stateful risk scoring, and a custom bulk access guard.**

![Telco Customer Agent Architecture](images/telco_customer_agent_architecture.svg)

---

## Overview

Multi-tool customer data agent with nine [session-based contextual policies](https://www.databricks.com/blog/contextual-policies-omnigent-using-session-state-better-govern-ai-agents) enforced at the framework layer — the LLM never gets a vote. Policies span five categories:

- **Taint labels + information flow** — Monotonic labels (`has_pii`, `has_financial`) DENY web search after sensitive data access. Three label-setters, two deny rules.
- **Cost budget** — ASKs at $1.00, DENYs at $5.00. Session-scoped, not per-request.
- **PII leak prevention** — Scans outgoing messages for SSN/email/phone patterns before they reach the model.
- **Risk score** — Accumulates points per tool call (billing: 5, customers: 3, plans: 1). ASKs when score crosses threshold.
- **Bulk access guard** — Custom policy (`policies/bulk_access_guard.py`) tracks distinct customer IDs across the session. ASKs after 3 unique customers.

All nine policies fire identically on Claude, GPT, or any supported harness. See the [Policy Engine](#policy-engine) section for full details.

It has three database tools and one builtin:

- **`query_plans`** -- Queries public plan/pricing data (5 plans mirroring real carrier tiers). Adds 1 risk point per call.

- **`query_customers`** -- Queries the customers and devices tables (20 customers with PII: names, emails, phone numbers, SSN last-4, IMEI). Triggers `has_pii`, adds 3 risk points, and increments the bulk access counter.

- **`query_billing`** -- Queries the billing and subscriptions tables (60 billing records across 3 months, 20 subscriptions with revenue, discounts, payment status). Triggers `has_financial`, adds 5 risk points, and increments the bulk access counter.

- **`web_search`** -- Builtin web search for external/competitor/market questions. Blocked after PII or financial data access.

The agent also includes a **`customer-report` skill** (`skills/customer-report/SKILL.md`) that generates structured quarterly business reviews with PII redaction rules. The skill is loaded on demand via `load_skill` when the user requests a report.

The prompt enforces **strict tool usage** -- the agent must use tools for every answer and declines out-of-scope questions rather than answering from training data.

---

## Get Started

Build the database:

```bash
python examples/tools/create_telco_db.py
```

This creates `examples/tools/data/telco.db` with 5 tables and 125 synthetic records.

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

## Example Queries to Trigger Policies

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

## How to Demo

See [demo.md](demo.md) for a timed walkthrough (15-18 min).

---

## Database

The agent queries `examples/tools/data/telco.db` — 5 tables (plans, customers, devices, subscriptions, billing) with 125 records. Rebuild with `python examples/tools/create_telco_db.py`. See the create script for the full schema.
