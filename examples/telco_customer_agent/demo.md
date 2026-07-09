# Telco Customer Agent — Demo Script

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
