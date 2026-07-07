# Plan: Extend Telco Customer Agent with Advanced Policies

## Context

The telco_customer_agent currently has 5 policies — 3 taint labels (`has_pii`, `has_financial`, `used_web`) and 2 web blockers. These demonstrate information flow control but don't show cost governance, PII redaction, stateful risk scoring, or custom policy authoring — capabilities that Omnigent has built-in but no example exercises. The telco agent is the natural home for these because it already handles real PII (SSNs, emails, phones) and financial data (billing, charges).

**Goal:** Add 3 builtin policies + 1 custom Python policy to the existing telco agent config. Keep it simple — a developer should read the diff and immediately understand what each policy does and why Omnigent's policy system matters.

---

## What to Add (4 policies)

### 1. `cost_budget` (builtin) — Session cost cap
- Path: `omnigent.policies.builtins.cost.cost_budget`
- Config: `max_cost_usd: 5.0`, `ask_thresholds_usd: [1.00]`
- **Why:** The telco agent has no cost control today. Every other example has it.

### 2. `deny_pii_in_llm_request` (builtin) — PII leak prevention
- Path: `omnigent.policies.builtins.safety.deny_pii_in_llm_request`
- Config: `pii_types: [ssn, email, phone]`, `action: ASK`
- **Why:** `query_customers` returns SSN last-4, emails, phone numbers. This policy scans outgoing LLM messages for PII patterns and flags them before they reach the model. Framework-level enforcement vs. the current prompt-level "please redact" approach in the customer-report skill.

### 3. `risk_score_policy` (builtin) — Stateful risk accumulation
- Path: `omnigent.policies.builtins.risk_score.risk_score_policy`
- Config: `threshold: 10`, `tool_points: {query_customers: 3, query_billing: 5, query_plans: 1}`, `guarded_tools: [query_customers, query_billing]`, `escalate_action: ASK`, `reason: "Risk score exceeded — multiple sensitive data accesses in this session."`
- **Why:** Querying one customer's plan is low risk. Querying 5 customers' billing in a row is high risk. This policy accumulates a score across turns and ASKs for approval when the threshold is crossed. Shows *stateful* governance that no static rule can express.

### 4. Custom policy: `bulk_access_guard` (new Python file)
- A simple factory-pattern policy (~20 lines) that tracks how many distinct customers have been queried in a session. ASKs for approval when the count exceeds a configurable limit (default: 3).
- **Why:** This is the "write your own policy" example. It demonstrates the function signature, factory pattern, session state, and POLICY_REGISTRY — everything a developer needs to write org-specific rules. The use case is real: preventing bulk data exfiltration by flagging when an agent accesses too many customer records.

---

## Files to Modify

### 1. `examples/telco_customer_agent/config.yaml`
- Add 4 new policies to the existing `guardrails.policies` block
- The custom policy references a local module path

### 2. New file: `examples/telco_customer_agent/policies/bulk_access_guard.py`
- ~30 lines: factory function + `POLICY_REGISTRY` export
- Tracks customer IDs seen via `session_state`, ASKs when count > limit

### 3. `examples/telco_customer_agent/README.md`
- Add a "Guardrails" section documenting all 9 policies (5 existing + 4 new)
- Add a "Custom Policy" subsection showing how `bulk_access_guard` works
- Add example queries that trigger each new policy

### 4. `docs/policy.md`
- Update the "Used in this repo" table — telco entry currently says `cost.cost_budget + PII/financial label policies` but it doesn't have `cost_budget` yet. Update to reflect all 9 policies: taint/deny (existing) + `cost.cost_budget` + `safety.deny_pii_in_llm_request` + `risk_score.risk_score_policy` + custom `bulk_access_guard`

---

## Implementation Order

1. Write `policies/bulk_access_guard.py` (custom policy)
2. Update `config.yaml` with 4 new policies
3. Update README.md with guardrails documentation
4. Update `docs/policy.md`

---

## Verification

```bash
# Run the agent
omnigent run examples/telco_customer_agent/ --no-session

# Test cost_budget: run queries until $1.00 ASK threshold fires
# Test deny_pii_in_llm_request: "Show me customer C001's full details"
#   → agent queries customer, PII scan should flag SSN/email/phone
# Test risk_score_policy: query billing for 3+ customers in a row
#   → risk score accumulates, ASK fires at threshold
# Test bulk_access_guard: query 4+ distinct customers
#   → "You've accessed 4 customer records. Continue?"
```
