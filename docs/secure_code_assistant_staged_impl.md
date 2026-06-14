# Secure Code Assistant: Staged Implementation Plan

## Context

The demo plan at `docs/secure_code_assistant_plan.md` specifies a new agent for a 10-15 min developer demo showcasing Omnigent's policy engine. The agent demonstrates **session-scoped information flow control**: once proprietary code is read, web search is denied (preventing data leakage); once web content is ingested, file writes are denied (preventing injection). The telco_customer_agent provides the structural template — same policy machinery, same YAML patterns.

## Files to Create

```
examples/secure_code_assistant/
|-- config.yaml
|-- README.md
+-- tools/python/
    |-- read_source.py
    +-- search_docs.py
```

## Files to Update

- `README.md` — add row to "All Examples" table (line ~301) and entry to "Project Structure" tree (line ~335)
- `CLAUDE.md` — add entry to "Directory Structure" section (line ~74)

---

## Stage 1: Bare Agent + Tools (no policies)

Create the directory bundle with a working agent before adding any guardrails.

**Create `examples/secure_code_assistant/tools/python/read_source.py`**
- Follow the tool pattern from `examples/greeter/tools/python/greet.py`: module docstring, `from __future__ import annotations`, `from omnigent_client.tools import tool`, `@tool` decorator, `:param`/`:returns:` docstring
- Use `os.getcwd()` not `__file__` (per CLAUDE.md known issue about temp paths)
- Implementation from plan doc lines 152-169

**Create `examples/secure_code_assistant/tools/python/search_docs.py`**
- Thin stub: `return f"[search_docs] Searching for: {query}"`
- Exists as a separate taint target, not a real search backend
- Implementation from plan doc lines 172-190

**Create `examples/secure_code_assistant/config.yaml`**
- Copy executor/os_env structure from `examples/telco_customer_agent/config.yaml` lines 1-19
- Use `model: claude-sonnet-4-6`, `harness: claude-sdk` (not databricks-prefixed)
- Add `tools: builtins: [web_search]`
- Add the system prompt from plan doc lines 135-147
- **No `guardrails:` section yet**

**Verify:**
1. `omnigent run examples/secure_code_assistant/` — agent starts
2. `Read the file examples/secure_code_assistant/config.yaml` — read_source works
3. `Search for Python asyncio best practices` — web_search works
4. `Run ls -la` — shell access works

---

## Stage 2: Labels + Taint Policies

Add the two monotonic labels and the two taint policies. Everything still allowed, but labels accumulate silently.

**Update `config.yaml`** — add `guardrails:` section with:
- `labels:` — `has_proprietary_code` and `has_external_content` (both initial `"False"`, values `["False", "True"]`, monotonic `increasing`)
- `policies:` — `taint_code_read` (sets `has_proprietary_code` on `read_source`) and `taint_web_search` (sets `has_external_content` on `web_search, search_docs`)
- Pattern: `omnigent.policies.function.make_fixed_action_callable` with `action: allow`, `set_labels`, `on_phases: [tool_call]`, `on_tools: [...]`
- Each policy needs top-level `set_labels: [label_name]` (framework convention from telco config)

**Verify:**
1. Fresh session — read a file, then search. Both work. Labels are being tracked but nothing is blocked.

---

## Stage 3: Block Search After Code (the wow moment)

Add `block_search_after_code` — the core demo policy.

**Update `config.yaml`** — add to `policies:`:
- `condition: { has_proprietary_code: "True" }`
- `action: deny`, `on_phases: [tool_call]`, `on_tools: [web_search, search_docs]`
- Reason text from plan doc lines 102-106

**Verify (the 3-turn demo flow):**
1. `Search the web for Python asyncio best practices` — works (no code read yet)
2. `Read the file examples/secure_code_assistant/tools/python/read_source.py and explain it` — works, sets taint
3. `Use web_search to find how other projects implement tool decorators` — **DENIED**

---

## Stage 4: Block Write After Web (reverse flow)

Add `block_write_after_web` — completes bidirectional control.

**Update `config.yaml`** — add to `policies:`:
- `condition: { has_external_content: "True" }`
- `action: deny`, `on_phases: [tool_call]`, `on_tools: [sys_os_write, sys_os_edit]`
- Reason text from plan doc lines 117-123

**Verify (fresh session):**
1. `Search the web for the latest FastAPI middleware patterns` — works, sets taint
2. `Write a new middleware file at middleware.py with what you found` — **DENIED**

**Cross-verify:** In a separate session, read code then try file write — should still work (only `has_proprietary_code` is set, not `has_external_content`).

---

## Stage 5: Cost Budget Guardrail

Add `cost_guard` policy.

**Update `config.yaml`** — add to `policies:`:
- `omnigent.policies.builtins.cost.cost_budget` with `max_cost_usd: 5.0`, `ask_thresholds_usd: [1.0]`
- Known risk: ASK threshold may not fire on claude-sdk (CLAUDE.md known issue). The $5 hard cap still works.

**Verify:** Run several queries. If the $1 ASK fires, approve and continue. If it doesn't, note as known limitation.

---

## Stage 6: README + Repo Integration

**Create `examples/secure_code_assistant/README.md`**
- Follow telco README structure: Overview, Get Started (no setup needed), Run Locally, Example Queries (organized by scenario: clean session / after code read / after web search), Policy Engine (labels table + policies table), Tools table
- No "Run on Databricks" section (open-source only demo)

**Update `README.md`**
- Add row to "All Examples" table (~line 301): `| **Secure Code Assistant** | examples/secure_code_assistant/ | Information flow control — blocks web search after code read, blocks file writes after web search |`
- Add entry to "Project Structure" tree (~line 335) between `rag_mlflow_docs/` and `telco_customer_agent/`

**Update `CLAUDE.md`**
- Add `secure_code_assistant/` entry to "Directory Structure" section (~line 74)

**Verify:** All links resolve. Policy table matches final config.yaml. Example queries match what was verified in stages 3-4.

---

## End-to-End Verification (after all stages)

Run through the plan doc's verification checklist (lines 423-432):
1. Agent starts, tools are discovered
2. Web search succeeds with no taint
3. `read_source` sets `has_proprietary_code` taint
4. `web_search` DENIED with expected message
5. New session: web search succeeds, then `sys_os_write` DENIED after web taint
6. `--model gpt-4o --harness openai-agents` — same DENY fires (portability)
7. `omnigent attach <session_id>` — second terminal shows history
8. Web UI at localhost:8000 shows the session
