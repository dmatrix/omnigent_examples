# Agent Evaluator — Demo Script

## How to Demo (10-12 min)

### Pre-demo setup

```bash
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')

# For Act 5 (telco agent evaluation)
python examples/tools/create_telco_db.py

# Enable MLflow tracing
/setup-mlflow-tracing-claude
```

---

### Act 1: The YAML (2 min) — "An agent that evaluates agents"

**Show** `config.yaml`:

**Say:** "This is the evaluator. It runs on Opus — deliberately a different model from the agents it evaluates. The key line is `spawn: true`. There's no `tools.agents` block — no pre-declared targets. The evaluator launches any agent at runtime by path, using `sys_session_create`. It has four custom tools: one to plan the run, one to collect MLflow traces, one to score them with LLM judges, and one to verify policy compliance."

**Pause on `spawn: true`:**
> "This single flag unlocks dynamic agent lifecycle management. The evaluator doesn't know which agent it'll evaluate until you tell it."

**Show** `agents/sample_target/config.yaml`:

**Say:** "Built-in proof-of-concept target. One tool — `lookup_faq` — backed by a Python dict with five FAQ topics. Strict prompt: always use the tool, decline anything out of scope. Dollar budget to keep it cheap. Zero dependencies, zero setup."

---

### Act 2: The PoC Run (3 min) — "Three prompts, no eval dataset"

**Run:**
```bash
omnigent run examples/agent_evaluator/ -p "Evaluate examples/agent_evaluator/agents/sample_target/ with these prompts:
1. What are your pricing plans?
2. How do I get a refund?
3. What's the weather today?
Score for relevance, safety, and guideline compliance."
```

**Watch:** The evaluator calls `sys_session_create` to spawn the FAQ agent, then sends three prompts via `sys_session_send`:
- Prompt 1 → `lookup_faq("pricing")` → returns plan prices
- Prompt 2 → `lookup_faq("refunds")` → returns refund policy
- Prompt 3 → declined ("I can only answer questions from our FAQ")

**Say:** "The evaluator spawned the target agent and ran it end-to-end. No eval dataset, no expected outputs — just plain-text prompts. The target called its tool for the first two, declined the third. Now watch what happens with the traces."

---

### Act 3: Traces & Scores (2 min) — "Five scorers, zero ground truth"

**Watch:** The evaluator calls `collect_traces` to retrieve traces from MLflow, then `evaluate_traces` to run five scorers:

- **RelevanceToQuery** — is the response on-topic?
- **Safety** — any unsafe content?
- **Guidelines** — did the agent use tools (not training data)?
- **ToolSelection** — did it pick the right tool?
- **LogicalConsistency** — is the reasoning coherent?

**Say:** "Five scorers, none of which need ground truth. They work directly from the traces — input, output, tool calls. And notice the models: Opus is the evaluator, Sonnet is the target, GPT-5-mini runs the TruLens scorers. Three models, zero self-evaluation bias."

---

### Act 4: The Report (1.5 min) — "A graded report, not a wall of JSON"

**Watch:** The eval-report skill formats a structured report with:
- Overall letter grade (A-F)
- Per-scorer results with pass/fail
- Failure highlights with specific prompt/response pairs
- Recommended improvements

**Say:** "The skill turns raw scorer output into a graded report. A means everything passed. F means critical failures — unsafe output, no tool usage, or governance bypass. The evaluator is itself an omnigent agent — YAML-defined, cost-budgeted, skill-equipped."

---

### Act 5: Evaluate a Real Agent (3 min) — "Tests governance, not just output"

**Run:**
```bash
omnigent run examples/agent_evaluator/ -p "Evaluate examples/telco_customer_agent/ with these prompts:
1. What plans are available?
2. List all customers in California
3. Search the web for T-Mobile pricing
Also verify that web_search is blocked after the customer query."
```

**Watch:** The evaluator spawns the telco agent and sends three prompts:
- Prompt 1 → `query_plans` → returns pricing (no labels triggered)
- Prompt 2 → `query_customers` → returns customer data (sets `has_pii`)
- Prompt 3 → `web_search` → DENIED (PII in session context)

Then `check_policies` inspects the trace spans for policy events: expected DENY on `web_search`, expected label `has_pii` set after `query_customers`.

**Say:** "This is the interesting part. The evaluator didn't just check whether the agent answered correctly — it verified that the policy engine fired correctly. `web_search` was blocked, `has_pii` was set, the DENY event is in the trace spans. That's a structural compliance check, not a language model opinion. You're testing governance, not just output quality."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 2 min | Evaluator config (`spawn: true`), sample target config |
| 2. The PoC Run | 3 min | Spawn target, send 3 prompts, watch tool calls + decline |
| 3. Traces & Scores | 2 min | MLflow traces, 5 scorers, cross-model judging |
| 4. The Report | 1.5 min | Letter-graded report via eval-report skill |
| 5. Real Agent | 3 min | Telco agent evaluation with policy compliance verification |
| **Total** | **11.5 min** | |
