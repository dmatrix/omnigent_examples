# Secure Code Assistant — Demo Script

## How to Demo (10-15 min)

![Demo Setup](images/secure_code_assistant_demo_setup.svg)

### Pre-demo setup

```bash
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
export $(grep OPENAI_API_KEY .env | tr -d '"')

# For the collaboration demo (Acts 4):
omnigent server start    # Terminal A (background)
omnigent host            # Terminal B (background)
# Pre-open browser to http://localhost:8000 (hidden tab)
```

---

### Act 1: The Hook (2 min) — "Agents as software"

**Say:** "You already write great agents. Claude Code, Codex, OpenAI — you wire up tools, you ship. But I have three questions. 

1. Can you **govern** your agent — not with prompt engineering, but with enforcement the model can't override? 
2. Can your teammate **attach** to your live session from their browser? 
3. Can you **swap the brain** from Claude to GPT without changing a single tool? 

Omnigent does all three. And the whole agent is a YAML file."

**Do:** Show `config.yaml` — scroll through three sections:
- `executor:` — "Two lines: which model, which harness. Swap both without touching tools."
- `tools:` — "Python functions auto-discovered from `tools/python/`. Web search as a builtin."
- `guardrails:` — "This is the new thing. Two taint labels, two deny policies, a cost budget. 

All declarative, and the model can't override it."

**Pause on `block_search_after_code`:**
> "If the session has seen proprietary source code, web search is denied. Not 'please don't search' — DENIED. The framework intercepts the call before it reaches the model's tools."

---

### Act 2: Policies — Information Flow (4 min)

**Do:** `omnigent run examples/secure_code_assistant/`

**Turn 1 — web search works (no code read yet):**

```
Search the web for Python asyncio best practices
```

Agent calls `web_search` or `search_docs`. Returns results.

**Say:** "Web search works. No proprietary code has been touched."

**Turn 2 — read proprietary source code (sets taint):**

```
Read the file examples/secure_code_assistant/tools/python/read_source.py and explain it
```

Agent calls `read_source`, returns contents. Framework silently sets `has_proprietary_code: True`.

**Say:** "I just read proprietary source code. Behind the scenes, the PolicyEngine set `has_proprietary_code` to True. That label is **monotonic** — once set, it can never be unset for this session."

**Turn 3 — web search denied:**

```
Use web_search to find how other projects implement tool decorators
```

> **DENIED:** "Web search blocked — proprietary source code is in session context. Search queries could leak implementation details, API keys, or business logic to external search engines."

**Say:** "Denied. The search query 'tool decorators' is generic — zero proprietary content. An API gateway would pass it. But Omnigent knows this *session* loaded source code two turns ago. The query is clean, but the context window is not. This is **session-scoped information flow control** — not request-level scanning."

**Say:** "And this isn't prompt engineering. The enforcement is in the framework layer. The model can't jailbreak around it because the tool call never reaches the harness."

**Turn 4 — reverse flow (write blocked after web):**

Start a new session: `omnigent run examples/secure_code_assistant/ --no-session`

```
Search the web for the latest FastAPI middleware patterns
```

Web search works. Sets `has_external_content: True`.

```
Write a new middleware file at middleware.py with what you found
```

> **DENIED:** "File write blocked — untrusted web content is in session context."

**Say:** "Two-way enforcement. Code can't leak out, and untrusted content can't be written in. Both directions, same policy engine, pure YAML."

---

### Act 3: Portability — Same Agent, Different Brain (3 min)

**Say:** "That ran on Claude Sonnet. Your team wants GPT? Same YAML, same tools, same policies."

**Do:** Exit the REPL. Re-run with OpenAI:

```bash
omnigent run examples/secure_code_assistant/ --model gpt-5.5 --harness openai-agents --no-session
```

```
Read the file examples/secure_code_assistant/config.yaml
```

Agent calls `read_source`, returns config. Taint fires.

```
Use web_search to find YAML schema validation libraries
```

> **Same DENY.** "Web search blocked — proprietary source code is in session context."

**Say:** "Same denial. The policy doesn't care which model issued the call. Claude, GPT — enforcement is in the framework, not the harness. Your compliance rules survive model migrations."

---

### Act 4: Collaboration — Session Sharing + Multi-Surface (3 min)

**Say:** "You're investigating a bug. Your teammate needs context. In Claude Code, you copy-paste the transcript into Slack. In Omnigent, they attach to your live session."

**Terminal 1:**

```bash
omnigent run examples/secure_code_assistant/
```

```
Read examples/secure_code_assistant/config.yaml and summarize the policy structure
```

Note the session ID.

**Say:** "This session has a persistent ID. My teammate can attach right now."

**Terminal 2:**

```bash
omnigent attach <session_id>
```

Full conversation history appears.

```
What labels have been set in this session so far?
```

Both terminals show the response in real time.

**Say:** "Both terminals are live. I hand off, they pick up exactly where I left off. Taint labels carry over — the policy state is part of the session, not the terminal."

**Web UI:** Switch to browser at `http://localhost:8000`. Click into the active session.

**Say:** "Same session, in the browser. On a deployed instance, this URL works from your phone. The session is the unit of continuity, not the terminal."

**Fork (if time):** `omnigent run --fork <session_id>` from Terminal 2.

**Say:** "Fork branches the conversation. Like `git branch` for agent sessions."

---

### Act 5: The Close (1 min)

**Say:** "Three pillars in twelve minutes."

- **Governance:** YAML policy engine with taint labels, monotonic state, DENY enforcement the model can't override. Session-scoped information flow control — not prompt engineering, not API gateway scanning.
- **Portability:** Same config.yaml, same Python tools, same policies. Claude, GPT. Two CLI flags, zero code changes.
- **Collaboration:** Persistent sessions. Attach, fork, access from CLI, browser, or mobile. Your work isn't trapped in one terminal.

**Say:** "Omnigent isn't replacing Claude Code or Codex. It's the governance, collaboration, and portability layer between your agents and the world. Write agents as software. Ship software as agents."

---

### Timing Summary

| Act | Duration | Pillar |
|-----|----------|--------|
| 1. The Hook | 2 min | Walk through YAML, frame the three questions |
| 2. Policies | 4 min | Taint + DENY both directions (wow moment) |
| 3. Portability | 3 min | Same agent on GPT-5.5, same DENY fires |
| 4. Collaboration | 3 min | Attach, co-drive, Web UI, fork |
| 5. Close | 1 min | Recap three pillars |
| **Total** | **13 min** | |
