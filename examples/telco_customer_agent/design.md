# Telco Customer Data Agent with PII/Financial Policy Labels

Implemented  here: https://github.com/dmatrix/omnigent_examples (A private repo)

## Why Omnigent Is the Right Framework for This

An agent that touches customer PII, financial records, and credit data cannot rely on the LLM to self-regulate. We discovered this when building a RAG with Omnigent: GPT-5.5 ignores every prompt instruction to refuse answering, even when the tool explicitly returns "no relevant documents found," for our use case RAG example. Prompt engineering is not a compliance strategy.

Omnigent solves this by adding a **policy enforcement layer between the harness and the user**. The `PolicyEngine` intercepts tool calls (on the runner) and input/output (on the server) before they reach or leave the session. Function-type policies on tool_call and tool_result phases run on the runner; label and prompt policies on request and response phases run server-side. Either way, the LLM never gets a vote on whether a policy is enforced.

### What the framework layer adds over bare harnesses

| Capability | Claude Code / Codex alone | Omnigent framework |
|---|---|---|
| **Session-scoped labels** | No — no concept of taint tracking across tool calls | Yes — labels like `has_pii` persist for the entire session and cannot be unset (monotonic) |
| **Conditional tool gating** | No — permissions are static (allow/deny per tool globally) | Yes — "allow `web_search` unless `has_pii` is true" is a one-line YAML policy |
| **Output-phase interception** | AI Gateway filters input and output per-request (prompt injection, toxicity, PII redaction) but stateless — cannot condition on what the agent did in previous turns | Yes — policies inspect output conditioned on accumulated session labels (e.g., "require approval because agent has both PII and financial data") and can DENY or ASK |
| **Human approval flows (ASK)** | No — no framework-level pause-and-approve mechanism | Yes — policy returns ASK, execution pauses, human reviews, then continues or rejects |
| **Information flow control** | No — the LLM decides what to share | Yes — "if agent has both PII and financial data, output requires human review" is declarative YAML |
| **Harness portability** | N/A — locked to one LLM | Yes — same policies work on `claude-sdk`, `openai-agents`, or `codex` because enforcement is in the runner, not the harness |
| **Rate limiting per turn** | AI Gateway rate-limits by clock time (RPM) but can't distinguish agent turns — 50 fast tool calls in 3 seconds stays within RPM limits | Yes — a stateful policy counts tool calls per turn (one user message → agent response cycle), DENIES after a configurable limit (e.g., 15), and the framework automatically resets the counter when the next turn starts. Caps the blast radius of runaway loops or prompt injection within a single interaction |
| **On-demand skills** | No — everything in the system prompt upfront | Yes — `load_skill` loads instructions only when needed, reducing token overhead |

### How it works in this example

1. Agent calls `query_customers` → runner's PolicyEngine sets `has_pii: true` (taint policy)
2. Agent tries `web_search` → runner checks labels, sees `has_pii: true`, returns DENY before the harness ever sees the request
3. Agent calls `query_billing` → runner sets `has_financial: true`
4. Agent generates output → runner checks labels, sees both `has_pii` and `has_financial` are true, returns ASK — execution pauses for human approval
5. Human approves or rejects → runner forwards or blocks the output

The harness (claude-sdk, openai-agents, codex) runs step 1 and 3 — it executes the LLM calls. The framework runs steps 2, 4, and 5 — it enforces governance. The harness also has policy callback hooks at LLM request/response boundaries (injected by the server adapter), but the harness owns no policy state, no labels, and no PolicyEngine — it just executes callbacks that the framework provides. The design doc (`POLICIES.md`) states: "No changes to the Executor contract, Tool API, or existing stores." The separation is clear: **the harness executes, the framework governs.**

### Operational benefits of the Omnigent layer for this use case

**1. Model swap without rewriting policies.** A telco compliance team writes policies once in YAML. The engineering team can switch from `databricks-claude-sonnet-4-6` to `databricks-gpt-5-5` or `databricks-kimi-k2-6` without touching a single policy. The guardrails are decoupled from the model. With bare harnesses, every model switch means re-validating whether the new model follows the prompt instructions.

**2. Tool sandboxing at the kernel level.** On Linux, Omnigent runs every `sys_os_shell` and `sys_os_write` call inside a Landlock + seccomp sandbox. The agent physically cannot write outside the project directory or call forbidden syscalls (ptrace, mount, reboot). Claude Code has a bash sandbox but it's opt-in and not kernel-enforced. For a telco agent with access to billing data, kernel-level isolation means a prompt injection attack cannot exfiltrate data via shell commands — the OS blocks it, not the LLM.

**3. Multi-harness orchestration.** The framework architecture supports sub-agents with different harnesses — each sub-agent has its own `ExecutorConfig` and can specify a different model and harness. For example, a supervisor on `claude-sdk` could dispatch to a sub-agent on `openai-agents`. The Nessie example (`examples/nessie/`) demonstrates multi-agent orchestration with `claude_code` and `codex` sub-agents. Note: in v1, sub-agents start with labels from their own spec, not inherited from the parent. Cross-session label propagation is planned for a future release.

**4. Durable session state across turns.** Labels persist in a SQL table (`conversation_labels`), not in the LLM's context window. A user can close the browser, come back an hour later, and the `has_pii: true` label is still there — the agent is still restricted. Bare harnesses lose all state when the context window resets.

**5. Observability per policy.** Policy decisions (ALLOW, DENY, ASK) flow through structured `PolicyResult` objects carrying action, reason, and label state. The runner logs policy exceptions and denial reasons via Python logging, and the server publishes SSE events on DENY/ASK actions. This provides more auditability than prompt-based guardrails (where the model self-reports its own compliance), though the current implementation uses standard logging — not a dedicated compliance audit system or MLflow trace integration.

**6. Fail-closed error handling.** If a policy's classifier LLM times out or throws an exception, the framework defaults to DENY — not ALLOW. Both the server-side `_dispatch_policy()` and the runner-side `_evaluate_policies()` catch exceptions and convert them to DENY verdicts. One nuance: policies declared as classifier-only (`action: [allow]` with no DENY in their action list) fail to ALLOW on error — this honors the author's "this policy never blocks" intent. For all other policies, failure = DENY. The `ask_timeout` (default 30 seconds, set in `DEFAULT_ASK_TIMEOUT`) ensures a stuck approval flow fails closed rather than hanging indefinitely.

**7. Declarative governance as code.** Policy configuration is YAML — it lives in version control and goes through PR review. A non-engineer can read `action: deny`, `match_tools: [web_search]`, and `reason: "Web search blocked — customer PII is in session context"` and understand what the guardrail does and when it fires. However, `function`-type policies reference a Python callable handler (e.g., `handler: myorg.policies.rate_limit`), so auditing the implementation logic of those policies requires reading Python code. `label`-type policies (like the ones in this telco example) are fully declarative in YAML with no Python code needed. `prompt`-type policies embed the classifier prompt inline in YAML — also fully auditable without Python.

### Why not just use Databricks AI Gateway for Policy/Governance?

AI Gateway and Omnigent policies sit at different layers in the stack and solve fundamentally different problems. They are complementary, not competing.

#### Where each layer sits

```
User
  ↓
Omnigent Runner              ← SESSION-SCOPED (stateful across turns)
  │  policies, labels,            "This session has seen PII — block web search"
  │  skills, sub-agents           "PII + financial data — require human approval"
  ↓
Harness (claude-sdk / openai-agents / codex)
  ↓
Databricks AI Gateway           ← REQUEST-SCOPED (stateless per API call)
  │  rate limits, content          "This request contains an SSN — redact it"
  │  filters, PII detection        "This user exceeded 100 RPM — throttle"
  ↓
Model API (Claude / GPT / Kimi)
```

#### The core difference: stateless vs stateful

**AI Gateway is stateless per-request.** It sees each API call in isolation. It can detect PII in a single request, rate-limit by RPM, filter toxic content, and log everything. But it has no concept of a "session." It doesn't know that the request at 14:32 is related to the request at 14:31. Each request is evaluated independently with zero memory of previous requests.

**Omnigent policies are stateful per-session.** They track what the agent has done across multiple turns and tool calls via monotonic labels that persist in a SQL table (`conversation_labels`). Policies gate future actions based on the accumulated state of the entire session — not just the current request.

#### What AI Gateway CAN do

- Detect PII in a single request or response text (regex, NER) and block or redact it
- Rate limit by requests per minute/hour per user or endpoint
- Filter toxic, harmful, or off-topic content in a single message
- Log every request for audit and cost tracking
- Route between model endpoints with fallback
- Track token usage and cost per API call

#### What AI Gateway CANNOT do

AI Gateway has no concept of a "session" or "conversation." It cannot:

- Track that the agent read customer PII 3 turns ago and restrict subsequent tool calls
- Correlate that the agent has accumulated both PII and financial data across 5 separate tool calls and require human approval before output
- Carry security restrictions across model switches (Claude → GPT mid-session)
- Conditionally allow a tool based on what happened earlier — gateway rules are static, not state-dependent
- Rate limit per logical agent turn (gateway counts by time window, not by turn boundary)
- Pause execution mid-session, wait for human approval, and resume or reject

#### The Turn 2 scenario: why this matters

```
Turn 1: User asks "List all customers in California"
  → Agent calls query_customers()
  → AI Gateway: sees a normal API call, passes it through ✓
  → Omnigent: sets has_pii=true on the session ✓

Turn 2: User asks "Search the web for T-Mobile pricing"
  → Agent tries to call web_search("T-Mobile pricing")
  → AI Gateway: sees a clean request — the query "T-Mobile pricing"
    contains ZERO PII. No SSN, no email, no phone number.
    AI Gateway passes it through. ✓ (from Gateway's perspective, correct)
  → Omnigent: checks session labels, sees has_pii=true from Turn 1,
    DENIES web_search before it ever reaches the gateway. ✓
    WHY: the agent's LLM context now contains customer names, emails,
    and phone numbers from Turn 1. Even though THIS request is clean,
    the agent might leak PII in follow-up search queries or include
    customer details in the search context window.

Turn 3: User asks "Generate a billing report for our enterprise customers"
  → Agent generates output with customer names + revenue numbers
  → AI Gateway: COULD detect PII in the output and redact names/emails.
    But the user explicitly asked for a customer report — redacting the
    customer names makes the report useless. Gateway's per-request PII
    filter is too blunt for this use case.
  → Omnigent: checks labels, sees has_pii=true AND has_financial=true,
    returns ASK — execution pauses. Human reviews the complete output
    in context and approves (this is an authorized report) or rejects
    (this output contains data that shouldn't leave the session). ✓
```

**Turn 2 is the critical difference.** The web search query "T-Mobile pricing" is completely clean — AI Gateway has no reason to block it. But Omnigent knows that 30 seconds ago, this same session loaded customer names, phone numbers, and SSN last-4 digits. The session-scoped label catches what the request-scoped gateway cannot.

**Turn 3 is the nuance.** AI Gateway's PII redaction is binary — it either blocks/redacts or doesn't. It can't distinguish "this is an authorized report the user asked for" from "the agent is leaking data." Omnigent's ASK flow puts a human in the loop to make that judgment call.

#### Capability comparison

| Capability | AI Gateway | Omnigent Policies |
|---|---|---|
| Scope | Per-request (stateless) | Per-session (stateful) |
| PII detection in text | Yes (regex, NER) | No (not its job) |
| Rate limiting | Yes (RPM, per-user) | Yes (per-turn, per-tool) |
| "Agent saw PII → block web search" | No (no session memory) | Yes (label tracking) |
| "PII + financial → require approval" | No (can't correlate across requests) | Yes (multi-label conditions) |
| Pause for human approval (ASK) | No (pass-through proxy) | Yes (first-class flow) |
| Cross-model label propagation | No (per-endpoint) | Yes (labels carry across harnesses) |
| Conditional tool gating by session state | No (rules are static) | Yes (labels are dynamic) |
| Fail-closed on policy error | N/A | Yes (timeout/exception → DENY) |

#### Use both

The right architecture uses AI Gateway AND Omnigent policies together:

- **AI Gateway** is the **last line of defense** at the API boundary — catches PII that slips through, enforces rate limits, logs everything for audit
- **Omnigent policies** are the **first line of defense** at the agent session level — tracks information flow, gates tool access based on accumulated state, requires human approval for sensitive outputs

Neither alone is sufficient. AI Gateway can't enforce session-scoped information flow. Omnigent policies can't scan output text for regex PII patterns. Together they provide defense in depth.

## Architecture

![Telco Customer Agent Architecture](images/telco_customer_agent_architecture.svg)

## File Structure

```
examples/telco_customer_agent/
├── config.yaml                      # Agent + labels + policies
├── tools/python/
│   ├── query_customers.py           # @tool: query customers + devices
│   ├── query_billing.py             # @tool: query billing + subscriptions
│   └── query_plans.py               # @tool: query available plans
└── skills/
    └── customer-report/
        └── SKILL.md                 # On-demand report template

examples/tools/
├── create_telco_db.py               # Setup script
└── data/
    └── telco.db                     # Pre-built SQLite DB
```

## Database Schema

### plans (5 records — mirrors real Verizon/T-Mobile tiers)

| Column | Type | Example |
|---|---|---|
| plan_id | TEXT | PLAN-ES, PLAN-EI, PLAN-EM, PLAN-EB, PLAN-BZ |
| plan_name | TEXT | Essentials Saver, Essentials, Experience More, Experience Beyond, Business Unlimited |
| monthly_rate | INTEGER | 55, 65, 90, 105, 200 |
| data_limit_gb | INTEGER | 50, 50, -1 (unlimited), -1, -1 |
| hotspot_gb | INTEGER | 0, 0, 60, -1 (unlimited), -1 |
| international | TEXT | none, none, 5gb_intl, 15gb_intl, unlimited |
| streaming_perks | TEXT | none, none, "netflix_ads,apple_tv", "netflix,hulu,apple_tv", none |
| price_guarantee_years | INTEGER | 0, 0, 5, 5, 3 |

### customers (20 records)

| Column | Type | Example | PII? |
|---|---|---|---|
| customer_id | TEXT | CUST-1001 | No |
| name | TEXT | Sarah Chen | Yes |
| email | TEXT | sarah.chen@gmail.com | Yes |
| phone_number | TEXT | (415) 555-0142 | Yes |
| ssn_last4 | TEXT | 4829 | Yes |
| address_state | TEXT | California | No |
| account_type | TEXT | individual, family, business | No |
| credit_class | TEXT | A, B, C, D | Sensitive |
| account_status | TEXT | active, suspended, past_due, churned | No |
| signup_date | TEXT | 2022-03-15 | No |
| auto_pay | TEXT | true, false | No |

### devices (20 records — one per subscription)

| Column | Type | Example | PII? |
|---|---|---|---|
| device_id | TEXT | DEV-4001 | No |
| subscription_id | TEXT | SUB-2001 | No |
| make | TEXT | Apple, Samsung, Google | No |
| model | TEXT | iPhone 16 Pro Max, Galaxy S25 Ultra, Pixel 9 Pro | No |
| imei | TEXT | 353456789012345 | Yes |
| installment_monthly | INTEGER | 0, 25, 30, 36, 42 | Financial |
| installment_remaining | INTEGER | 0, 8, 18, 24 | Financial |
| installment_total | INTEGER | 0, 900, 1100, 1200, 1500 | Financial |
| insurance_plan | TEXT | none, basic_protect, total_protect | No |
| insurance_monthly | INTEGER | 0, 15, 18 | Financial |

### subscriptions (20 records — one per customer)

| Column | Type | Example | Financial? |
|---|---|---|---|
| subscription_id | TEXT | SUB-2001 | No |
| customer_id | TEXT | CUST-1001 | No |
| plan_id | TEXT | PLAN-EB | No |
| line_type | TEXT | primary, additional, tablet, watch | No |
| monthly_rate | INTEGER | 105 | Yes |
| contract_type | TEXT | postpaid, prepaid | No |
| contract_months | INTEGER | 12, 24, 36 | No |
| contract_start | TEXT | 2023-06-15 | No |
| contract_end | TEXT | 2025-06-15 | No |
| auto_renew | TEXT | true, false | No |
| discount_pct | INTEGER | 0, 10, 15, 20 | Yes |
| promo_code | TEXT | LOYAL20, SWITCH15, MILITARY, null | Yes |
| ported_from | TEXT | t-mobile, att, verizon, null | Sensitive |

### billing (60 records — 3 months per customer)

| Column | Type | Example | Financial? |
|---|---|---|---|
| billing_id | TEXT | BILL-5001 | No |
| customer_id | TEXT | CUST-1001 | No |
| month | TEXT | 2025-04 | No |
| plan_charge | INTEGER | 105 | Yes |
| device_installment | INTEGER | 36 | Yes |
| insurance | INTEGER | 18 | Yes |
| overage_charges | INTEGER | 0, 12, 25 | Yes |
| international_charges | INTEGER | 0, 8, 15, 45 | Yes |
| taxes_and_fees | INTEGER | 9 | Yes |
| autopay_discount | INTEGER | -10, 0 | Yes |
| promo_discount | INTEGER | -21, 0 | Yes |
| total_due | INTEGER | 137 | Yes |
| payment_status | TEXT | current, past_due_30, past_due_60, collections | Yes |
| late_fee | INTEGER | 0, 15, 25 | Yes |

## Tools

### query_customers (queries customers + devices tables)

- `@tool` function, takes `sql_query: str`
- Can JOIN customers with devices via subscription_id
- Triggers `has_pii` label (names, emails, phone numbers, SSN, IMEI)
- Lazy imports, `os.getcwd()` for DB path

### query_billing (queries billing + subscriptions tables)

- `@tool` function, takes `sql_query: str`
- Can JOIN billing with subscriptions via customer_id
- Triggers `has_financial` label (revenue, discounts, payment status, installments)

### query_plans (queries plans table)

- `@tool` function, takes `sql_query: str`
- Public pricing data — does NOT trigger any labels
- Safe to use before or after any other query

## Policy Labels

```yaml
labels:
  has_pii: "false"
  has_financial: "false"
  has_credit: "false"
  used_web: "false"

label_schema:
  has_pii:
    values: ["false", "true"]
    monotonic: max
  has_financial:
    values: ["false", "true"]
    monotonic: max
  has_credit:
    values: ["false", "true"]
    monotonic: max
  used_web:
    values: ["false", "true"]
    monotonic: max
```

## Policies (8 total)

```yaml
policies:
  # === Taint policies (tag what the agent has seen) ===

  taint_pii:
    type: label
    on: [tool_call]
    match_tools: [query_customers]
    action: allow
    set_labels:
      has_pii: "true"

  taint_financial:
    type: label
    on: [tool_call]
    match_tools: [query_billing]
    action: allow
    set_labels:
      has_financial: "true"

  taint_credit:
    type: label
    on: [tool_call]
    condition: {}
    match_tools: [query_customers]
    action: allow
    set_labels:
      has_credit: "true"

  taint_web:
    type: label
    on: [tool_call]
    match_tools: [web_search]
    action: allow
    set_labels:
      used_web: "true"

  # === Enforcement policies (block based on labels) ===

  block_web_after_pii:
    type: label
    on: [tool_call]
    condition:
      has_pii: "true"
    match_tools: [web_search]
    action: deny
    reason: |
      Web search blocked — customer PII (names, emails, phone numbers, SSN)
      is in session context. Search queries could leak identity data.

  block_web_after_financial:
    type: label
    on: [tool_call]
    condition:
      has_financial: "true"
    match_tools: [web_search]
    action: deny
    reason: |
      Web search blocked — financial data (billing, revenue, discounts,
      payment status) is in session context.

  approve_pii_financial_output:
    type: label
    on: [output]
    condition:
      has_pii: "true"
      has_financial: "true"
    action: ask
    reason: |
      Output contains both customer PII and financial data.
      Human review required before this information leaves the session.

  approve_credit_output:
    type: label
    on: [output]
    condition:
      has_credit: "true"
    action: ask
    reason: |
      Output contains credit classification or collections data.
      This is regulated under FDCPA. Human review required.
```

## Skill: customer-report/SKILL.md

```markdown
---
name: customer-report
description: Generate a structured telco customer report with PII redaction guidelines.
---

When asked to produce a customer report:
1. State which data sources were queried (customers, billing, subscriptions, devices)
2. Summarize by plan tier (how many customers per tier, average revenue)
3. Highlight churn risk: customers with past_due status, auto_renew=false, or contract ending within 90 days
4. Device breakdown: top devices by make/model, installment payment totals
5. Revenue metrics: total MRR, average revenue per user (ARPU), discount impact
6. Redaction rules: replace full email with "s***@gmail.com", show only last 4 of phone number, never show SSN
7. Flag any customers ported from competitors (business intelligence)
8. End with recommended actions (retention outreach, upgrade opportunities)
```

## Test Scenarios

```bash
python examples/tools/create_telco_db.py
omnigent run examples/telco_customer_agent/
```

```
# SAFE: public plan data (no labels triggered)
What plans are available and what do they cost?
Compare the Experience More and Experience Beyond plans

# PII query (sets has_pii=true)
List all customers in California with their phone numbers
Show me customers whose contracts expire in the next 90 days
Who has auto-renew turned off?

# DENIED: web after PII
Search the web for T-Mobile's current pricing
→ BLOCKED: "Web search blocked — customer PII is in session context."

# Financial query (sets has_financial=true)
What's our total monthly revenue across all plans?
Which customers have overage charges this month?
Show me all past-due accounts with amounts owed
What discount codes are we giving out and to whom?

# ASK: output with PII + financial
Generate a churn risk report with customer names and payment history
→ PAUSED: "Output contains both PII and financial data. Human review required."

# ASK: credit data output
Show me customers with credit class D and their payment history
→ PAUSED: "Output contains credit/collections data. Regulated under FDCPA."

# Combined with skill
Use the customer-report skill to produce a quarterly business review

# Safe after PII (plan data is always available)
What plan does our most expensive customer have?
How many customers are on the Business Unlimited plan?
```

## Staged Implementation Plan

Build and test incrementally. Each stage adds one capability and is tested before moving to the next. If a stage fails, fix it before proceeding — don't stack untested features.

### Stage 1: Database + single tool (no policies, no skills)

**Build:**
- `examples/tools/create_telco_db.py` — creates `telco.db` with all 5 tables
- `examples/telco_customer_agent/config.yaml` — minimal config with `databricks-gpt-5-5`, `openai-agents`, NO policies, NO labels, NO skills
- `examples/telco_customer_agent/tools/python/query_plans.py` — single @tool, queries plans table only

**Test:**
```bash
python examples/tools/create_telco_db.py
omnigent run examples/telco_customer_agent/
```
```
What plans are available and what do they cost?
Compare the Experience More and Experience Beyond plans
```

**Validates:** auto-discovery works, SQLite reads from CWD, basic agent responds using tool output.

---

### Stage 2: Add PII tool (still no policies)

**Build:**
- `examples/telco_customer_agent/tools/python/query_customers.py` — @tool, queries customers + devices tables

**Test:**
```
List all customers in California with their phone numbers
Show me customers whose contracts expire in the next 90 days
Who has auto-renew turned off?
```

**Validates:** second auto-discovered tool works, agent routes between `query_plans` and `query_customers` via prompt.

---

### Stage 3: Add financial tool (still no policies)

**Build:**
- `examples/telco_customer_agent/tools/python/query_billing.py` — @tool, queries billing + subscriptions tables

**Test:**
```
What's our total monthly revenue across all plans?
Which customers have overage charges this month?
Show me all past-due accounts with amounts owed
```

**Validates:** three tools work together, agent routes correctly, all tables queryable.

---

### Stage 4: Add web_search builtin (still no policies)

**Build:**
- Add `tools.builtins: [web_search]` to config.yaml

**Test:**
```
Search the web for T-Mobile's current pricing
What plans are available? (should use query_plans, not web)
```

**Validates:** builtin tool coexists with custom tools, agent routes web questions to web_search and data questions to query tools.

---

### Stage 5: Add taint labels (no enforcement yet)

**Build:**
- Add `labels:` and `label_schema:` to config.yaml (has_pii, has_financial, has_credit, used_web — all start false, monotonic max)
- Add 4 taint policies: `taint_pii`, `taint_financial`, `taint_credit`, `taint_web` — all `action: allow` with `set_labels`

**Test:**
```
List all customers in California
```
Then check runner logs for label state — `has_pii` should be `true`.

```
What's our total revenue?
```
Check logs — `has_financial` should also be `true` now.

**Validates:** labels are being set by taint policies. No enforcement yet — all tools still work. This is the "tagging" layer only.

---

### Stage 6: Add DENY policies (enforcement)

**Build:**
- Add `block_web_after_pii` policy — DENY web_search when has_pii=true
- Add `block_web_after_financial` policy — DENY web_search when has_financial=true

**Test:**

**Scenario A: PII taint → web search denied**
```
Turn 1:  What devices does customer CUST-1001 have?
         → agent calls query_customers → taint_pii fires → has_pii = true ✓

Turn 2:  Use web_search to find the latest iPhone trade-in deals from T-Mobile and Verizon
         → agent tries web_search → block_web_after_pii fires → DENIED ✗
```

**Scenario B: Financial taint → web search denied**
```
Turn 1:  Show me the billing summary for CUST-1003 for the last 3 months
         → agent calls query_billing → taint_financial fires → has_financial = true ✓

Turn 2:  Use web_search to find how T-Mobile pricing compares to our plans
         → agent tries web_search → block_web_after_financial fires → DENIED ✗
```

**Scenario C: Web search works until tainted (contrast — best demo)**
```
Turn 1:  What are Verizon's current unlimited plan prices?
         → agent calls web_search → taint_web fires → used_web = true, no denial ✓

Turn 2:  Now show me CUST-1002's billing history
         → agent calls query_billing → taint_financial fires → has_financial = true ✓

Turn 3:  Use web_search to find average churn rates in telecom
         → agent tries web_search → block_web_after_financial fires → DENIED ✗
```

> **Note:** Use explicit "Use web_search to..." phrasing in denial turns. Ambiguous prompts like "What are the latest iPhone deals?" may cause the LLM to route around the tool (answering from training data or using `query_plans` instead), which means the DENY policy never fires. The policy enforces at the tool-call layer — if the LLM never attempts the call, there's nothing to deny.

**Validates:** DENY enforcement works. The agent can use web_search before touching data, but not after. Scenario C is the most compelling demo — it shows web search succeeding in turn 1, then getting blocked after sensitive data enters the session. The order matters because labels are monotonic.

---

### Stage 7: Add ASK policies (human approval)

**Build:**
- Add `approve_pii_financial_output` policy — ASK on output when has_pii AND has_financial
- Add `approve_credit_output` policy — ASK on output when has_credit

**Test:**

**Scenario A: PII + financial → output paused for approval**
```
Turn 1:  List all customers in California
         → agent calls query_customers → taint_pii fires → has_pii = true ✓

Turn 2:  What's our total monthly revenue?
         → agent calls query_billing → taint_financial fires → has_financial = true ✓

Turn 3:  Generate a billing report for enterprise customers
         → agent produces output → approve_pii_financial_output fires
         → PAUSED: "Output contains both PII and financial data. Human review required."
         → Human approves → output delivered ✓
         → Human rejects → output blocked ✗
```

**Scenario B: Credit data → output paused for approval**
```
Turn 1:  Show me customers with credit class D and their payment history
         → agent calls query_customers → taint_pii + taint_credit fire
         → has_pii = true, has_credit = true ✓

Turn 2:  Which of those customers are in collections?
         → agent calls query_billing → taint_financial fires → has_financial = true ✓
         → agent produces output → approve_credit_output fires
         → PAUSED: "Output contains credit/collections data. Regulated under FDCPA."
```

**Scenario C: PII alone does NOT trigger ASK (contrast)**
```
Turn 1:  List all customers in California with their phone numbers
         → agent calls query_customers → has_pii = true ✓

Turn 2:  How many of those are on the Experience Beyond plan?
         → agent calls query_plans (no new labels) ✓
         → agent produces output → approve_pii_financial_output does NOT fire
           (condition requires BOTH has_pii AND has_financial) → output delivered normally ✓
```

> **Note:** ASK policies fire on `[output]`, not `[tool_call]`. The pause happens when the agent tries to send its response to the user, not when it calls a tool. This means the agent completes all its reasoning and tool calls first — the human reviews the final assembled answer.

**Validates:** ASK flow works — execution pauses, user approves or rejects, agent continues or stops. Scenario C confirms that PII alone is not enough to trigger the combined PII+financial approval gate — both labels must be true.

---

### Stage 8: Add the skill

**Build:**
- `examples/telco_customer_agent/skills/customer-report/SKILL.md` — on-demand report template with redaction rules

**Test:**
```
Use the customer-report skill to produce a quarterly business review
```

**Validates:** skill loads on demand via `load_skill`, agent follows the structured report template.

---

### Stage 9: Update prompt for strict tool usage

**Build:**
- Update the agent prompt to enforce "MUST use tools, FORBIDDEN from training data" (same pattern as FEMA agent)

**Test:**
```
# In-scope — should use tools
What plans do we offer?

# Out-of-scope — should decline
What's the weather in San Francisco?
```

**Validates:** agent only answers from tools, declines unrelated questions.

---

### Stage 10: README and documentation

**Build:**
- Add to examples table in README
- Add architecture diagram reference
- Add test queries
- Update CLAUDE.md

---

## Stage Dependencies

```
Stage 1 (DB + plans tool)
  ↓
Stage 2 (+ customers tool)
  ↓
Stage 3 (+ billing tool)
  ↓
Stage 4 (+ web_search builtin)
  ↓
Stage 5 (+ taint labels — tagging only)
  ↓
Stage 6 (+ DENY policies — enforcement)
  ↓
Stage 7 (+ ASK policies — human approval)
  ↓
Stage 8 (+ skill)
  ↓
Stage 9 (+ strict prompt)
  ↓
Stage 10 (docs)
```

Each stage is independently testable. If Stage 6 (DENY) fails, you still have a working 3-tool agent from Stage 4. If Stage 7 (ASK) fails, DENY enforcement from Stage 6 still works. The skill and strict prompt are additive — they enhance but don't break the core functionality.

## Testing with OpenAI Models

The telco agent config defaults to `claude-sonnet-4-6` with `claude-sdk`, but you can test every stage with OpenAI models using CLI overrides:

### Prerequisites (one-time)

```bash
# Export OpenAI API key from .env
export $(grep OPENAI_API_KEY .env | tr -d '"')
```

### The override pattern

Same `config.yaml`, different model — override at the command line:

```bash
omnigent run examples/telco_customer_agent/ --model gpt-4o --harness openai-agents
```

- `--model gpt-4o` — overrides `executor.model` in config.yaml
- `--harness openai-agents` — overrides `executor.config.harness`

### Per-stage test commands

The command is the same for every stage — what changes is the tools and policies present in `config.yaml` at each stage:

```bash
omnigent run examples/telco_customer_agent/ --model gpt-4o --harness openai-agents
```

**Stage 1** (plans tool only):
```
What plans are available and what do they cost?
Compare the Experience More and Experience Beyond plans
```

**Stage 2** (+ customers tool):
```
List all customers in California with their phone numbers
Show me customers whose contracts expire in the next 90 days
```

**Stage 3** (+ billing tool):
```
What's our total monthly revenue across all plans?
Which customers have overage charges this month?
Show me all past-due accounts with amounts owed
```

**Stage 4** (+ web_search builtin):
```
Search the web for T-Mobile's current pricing
How do our plans compare to T-Mobile's current unlimited plans? Show our pricing first, then search for theirs.
What plans are available?   ← should route to query_plans, not web_search
```

### Tested OpenAI models

| Model | Flag | Notes |
|---|---|---|
| `gpt-4o` | `--model gpt-4o` | Recommended — accurate SQL, good tool routing |
| `gpt-4.1-mini` | `--model gpt-4.1-mini` | Budget option — occasional SQL column name errors |
| `gpt-5.4` | `--model gpt-5.4` | Latest — untested with telco agent |

## Verification Checklist (cumulative)

After all stages:

1. Plan queries work freely — no labels triggered
2. Customer queries set `has_pii` and `has_credit` labels
3. Billing queries set `has_financial` label
4. Web search works before any data access
5. Web search DENIED after customer or billing data access
6. Output with PII + financial triggers ASK for human approval
7. Output with credit data triggers separate ASK
8. Skill loads on demand and produces structured report
9. Labels visible in runner logs
10. All policies work regardless of harness (claude-sdk, openai-agents)

## README Update

- Add to examples table
- Add "Why Omnigent?" section with the policy label explanation
- Link to this plan for the full data model
