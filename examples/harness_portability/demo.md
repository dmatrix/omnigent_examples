# Harness Portability — Demo Script

## How to Demo (8-9 min)

### Act 1: The YAML (1.5 min) — "One supervisor, four inspectors, four harnesses"

**Show** `config.yaml`. Point out:

**Say:** "This is the supervisor — Claude SDK. It references four sub-agents in its `tools:` block. It doesn't inspect anything itself — it clones the repo, dispatches to four inspectors, and assembles the report."

**Show** `agents/test_inspector/config.yaml`.

**Say:** "Each inspector is its own config. This one runs on Codex. The structure inspector runs on Claude, the dependency inspector on Pi, the security inspector on Hermes. Four harnesses, one session tree. To swap any inspector's harness, change one line."

---

### Act 2: Run It (3 min) — "Inspect a real repo"

**Run:** `omnigent run examples/harness_portability/ --no-session`

**Prompt:**
```
Inspect https://github.com/pallets/flask
```

**Watch:** The supervisor clones Flask, then dispatches four inspectors. You'll see each inspector working on its category — structure, tests, dependencies, security — each on a different harness.

**Say:** "The supervisor cloned the repo and dispatched four inspectors. Each one runs on a different LLM — Claude analyzes structure, GPT analyzes tests, Pi checks dependencies, Hermes scans for security issues. Same prompt pattern, same tools, different brains."

---

### Act 3: The Report (1 min) — "Four inspectors, one report"

**Show** `health_report.md`.

**Say:** "The supervisor collected findings from all four inspectors and assembled them into one report with letter grades per category and an overall score. The inspectors ran on four different harnesses, but the output is a single coherent artifact."

---

### Act 4: The Swap (2 min) — "Change one line, different brain"

**Edit** `agents/test_inspector/config.yaml` — change `harness: codex` to `harness: claude-sdk` and `model: gpt-5.4` to `model: claude-sonnet-4-6`.

**Re-run:** `omnigent run examples/harness_portability/ --no-session`

**Same prompt:** `Inspect https://github.com/pallets/flask`

**Say:** "Same supervisor. Same prompt. Same guardrails. I swapped the test inspector from Codex to Claude — one line. The report covers the same four categories with the same structure. The workflow is defined in the config, not in the harness."

---

### Act 5: The Guardrails (1.5 min) — "Layered governance across harnesses"

**Show** the `guardrails:` blocks in both `config.yaml` and one sub-agent config.

**Say:** "Two layers of governance. The supervisor has a $5 session-wide cost cap. Each sub-agent has its own $5 cost cap and a 250 tool-call limit — so no single inspector can run away. The PolicyEngine runs in the Omnigent runner, not in the harness. These policies fire identically on Claude, GPT, Pi, and Hermes."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 1.5 min | Supervisor + sub-agent configs, four harness assignments |
| 2. Run It | 3 min | Inspect a real repo, watch cross-harness delegation |
| 3. The Report | 1 min | Assembled health report with grades from all inspectors |
| 4. The Swap | 2 min | Change one sub-agent's harness, same result |
| 5. Guardrails | 1.5 min | Layered cost governance across harnesses |
| **Total** | **9 min** | |
