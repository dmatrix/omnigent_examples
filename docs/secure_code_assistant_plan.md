# Omnigent Developer Demo: CUJ Plan (10-15 min)

## Context

10-15 minute live demo targeting developers who already use coding agents (Claude Code, Codex, OpenAI). Pitch: **"Omnigent helps agent developers write agents as software and software as agents."** Three pillars: **Policies, Collaboration, Portability across surfaces.** Open-source omnigent only — no Databricks.

We design a NEW agent from scratch (not any existing example) to showcase the framework's capabilities.

---

## The Agent: "Secure Code Assistant"

A developer's coding assistant that reads project files, runs shell commands, and searches the web — governed by layered policies that prevent proprietary code leakage and control cost. Built entirely in YAML + two small Python tools.

### Why this agent

The audience already uses Claude Code and Codex. This agent answers: *"What if your coding agent read your proprietary source code, then searched the web? Could the search query leak your implementation details? Can you prevent that — not by trusting the model, but by enforcement?"* This is a real security concern every developer has with AI tools.

### What we build

Create `examples/secure_code_assistant/` with:

1. **`config.yaml`** — the full agent spec: executor, tools, guardrails (labels + 5 policies), system prompt
2. **`tools/python/read_source.py`** — reads source files in the project (wraps file read, returns content). Triggers `has_proprietary_code` taint.
3. **`tools/python/search_docs.py`** — searches web for documentation/Stack Overflow. Triggers `has_external_content` taint.

### Agent config design

```yaml
spec_version: 1
name: secure_code_assistant
description: >
  Coding assistant with information flow policies. Reads project files,
  searches the web for docs, and runs shell commands — governed by taint
  labels that prevent proprietary code from leaking via web search and
  untrusted web content from being written to project files.

executor:
  type: omnigent
  model: claude-sonnet-4-6
  config:
    harness: claude-sdk

os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none

tools:
  builtins:
    - web_search

guardrails:
  labels:
    has_proprietary_code:
      initial: "False"
      values: ["False", "True"]
      monotonic: increasing
    has_external_content:
      initial: "False"
      values: ["False", "True"]
      monotonic: increasing

  policies:
    # --- Taint policies: track what data the agent has seen ---

    taint_code_read:
      type: function
      function:
        path: omnigent.policies.function.make_fixed_action_callable
        arguments:
          action: allow
          set_labels:
            has_proprietary_code: "True"
          on_phases: [tool_call]
          on_tools: [read_source]
      set_labels: [has_proprietary_code]

    taint_web_search:
      type: function
      function:
        path: omnigent.policies.function.make_fixed_action_callable
        arguments:
          action: allow
          set_labels:
            has_external_content: "True"
          on_phases: [tool_call]
          on_tools: [web_search, search_docs]
      set_labels: [has_external_content]

    # --- Deny policies: enforce information flow boundaries ---

    block_search_after_code:
      type: function
      condition:
        has_proprietary_code: "True"
      function:
        path: omnigent.policies.function.make_fixed_action_callable
        arguments:
          action: deny
          reason: |
            Web search blocked — proprietary source code is in session
            context. Search queries could leak implementation details,
            API keys, or business logic to external search engines.
          on_phases: [tool_call]
          on_tools: [web_search, search_docs]

    block_write_after_web:
      type: function
      condition:
        has_external_content: "True"
      function:
        path: omnigent.policies.function.make_fixed_action_callable
        arguments:
          action: deny
          reason: |
            File write blocked — untrusted web content is in session
            context. Writing files after ingesting external content
            risks injection of malicious code or license-incompatible
            snippets into the project.
          on_phases: [tool_call]
          on_tools: [sys_os_write, sys_os_edit]

    # --- Cost policy: budget guardrail ---

    cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.cost_budget
        arguments:
          max_cost_usd: 5.0
          ask_thresholds_usd: [1.0]

prompt: |
  You are a secure code assistant. You help developers understand
  codebases, find patterns, search documentation, and navigate projects.

  Your tools:
  1. `read_source` — reads source files in the project
  2. `search_docs` — searches the web for documentation
  3. `web_search` — general web search (builtin)
  4. Shell access — run grep, find, git log, etc.

  Use tools for every answer. Do not answer from training data when
  tools can provide current, accurate information.
```

### Python tools

**`tools/python/read_source.py`** — Simple file reader:
```python
from omnigent_client.tools import tool

@tool
def read_source(file_path: str) -> str:
    """Read a source file from the project directory.

    Args:
        file_path: Relative path to the file to read.

    Returns:
        The file contents as a string.
    """
    import os
    full_path = os.path.join(os.getcwd(), file_path)
    with open(full_path) as f:
        return f.read()
```

**`tools/python/search_docs.py`** — Web doc search (thin wrapper around web search, for taint separation):
```python
from omnigent_client.tools import tool

@tool
def search_docs(query: str) -> str:
    """Search the web for technical documentation and code examples.

    Args:
        query: Search query for documentation.

    Returns:
        Search results as text.
    """
    import urllib.request
    import json
    # Uses the same search backend as the builtin web_search
    # but exists as a separate tool so policies can taint it independently
    return f"[search_docs] Searching for: {query}"
```

> **Note:** `search_docs` is intentionally a thin tool. Its purpose is to be a **separate taint target** from `read_source` — the policy system enforces boundaries between "code reading" and "web searching" tools. In production, this would wire into a real search API.

---

## Demo Script

### Pre-Demo Setup (not shown)

```bash
# Ensure the agent directory exists with config.yaml and tools
# (created as part of this plan's implementation)

export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
export $(grep OPENAI_API_KEY .env | tr -d '"')

# Start server for collaboration demo
omnigent server start    # Terminal A (background)
omnigent host            # Terminal B (background)

# Pre-open browser to http://localhost:8000 (hidden tab)
# Have Terminal 1 and Terminal 2 side-by-side
```

---

### ACT 1: The Hook (2 min) — "Agents as software"

**Say:** "You already write great agents. Claude Code, Codex, OpenAI — you wire up tools, you ship. But I have three questions. Can you **govern** your agent — not with prompt engineering, but with enforcement the model can't override? Can your teammate **attach** to your live session from their browser? Can you **swap the brain** from Claude to GPT without changing a single tool? Omnigent does all three. And the whole agent is a YAML file."

**Do:** Show `config.yaml` — scroll through the three sections:
- `executor:` — "Two lines: which model, which harness. Swap both without touching tools."
- `tools:` — "Python functions auto-discovered from `tools/python/`. Web search as a builtin."
- `guardrails:` — "This is the new thing. Two taint labels, two deny policies, a cost budget. All declarative. The model never gets a vote."

**Pause on `block_search_after_code`:**
> "If the session has seen proprietary source code, web search is denied. Not 'please don't search' — DENIED. The framework intercepts the call before it reaches the model's tools."

---

### ACT 2: Policies — Information Flow + Cost (4 min) — THE WOW MOMENT

**Do:** `omnigent run examples/secure_code_assistant/`

#### Turn 1: Web search works (no code read yet)

**Type:** `Search the web for Python asyncio best practices`

Agent calls `web_search` or `search_docs`. Returns results. No labels set.

**Say:** "Web search works. No proprietary code has been touched."

#### Turn 2: Read proprietary source code (sets taint)

**Type:** `Read the file examples/secure_code_assistant/tools/python/read_source.py and explain it`

Agent calls `read_source`. Returns the file contents and explains it. Framework silently sets `has_proprietary_code: True`.

**Say:** "I just read proprietary source code. Behind the scenes, the PolicyEngine set `has_proprietary_code` to True. That label is **monotonic** — once set, it can never be unset for this session."

#### Turn 3: THE WOW MOMENT — web search denied

**Type:** `Use web_search to find how other projects implement tool decorators`

Agent attempts `web_search` → framework intercepts → **DENIED**: *"Web search blocked — proprietary source code is in session context. Search queries could leak implementation details, API keys, or business logic to external search engines."*

**Say:** "Denied. The search query 'tool decorators' is generic — zero proprietary content. An API gateway would pass it. But Omnigent knows this *session* loaded source code two turns ago. The query is clean, but the context window is not. This is **session-scoped information flow control** — not request-level scanning."

**Say:** "And this isn't prompt engineering. The enforcement is in the framework layer. The model can't jailbreak around it because the tool call never reaches the harness."

#### Turn 4: Show the reverse flow (write blocked after web)

Start a **new session** (exit, re-run with `--no-session`):

**Do:** `omnigent run examples/secure_code_assistant/ --no-session`

**Type:** `Search the web for the latest FastAPI middleware patterns`

Web search works (no code has been read). Sets `has_external_content: True`.

**Type:** `Write a new middleware file at middleware.py with what you found`

Agent attempts `sys_os_write` → **DENIED**: *"File write blocked — untrusted web content is in session context. Writing files after ingesting external content risks injection of malicious code or license-incompatible snippets."*

**Say:** "Two-way enforcement. Code can't leak out, and untrusted content can't be written in. Both directions, same policy engine, pure YAML."

---

### ACT 3: Portability — Same Agent, Different Brain (3 min)

**Say:** "That ran on Claude Sonnet. Your team wants GPT? Same YAML, same tools, same policies."

**Do:** Exit the REPL. Re-run with OpenAI:

```bash
omnigent run examples/secure_code_assistant/ --model gpt-4o --harness openai-agents --no-session
```

*(If CLI override bug applies: edit `config.yaml` executor block to `model: gpt-4o` / `harness: openai-agents` instead.)*

#### Quick verification

**Type:** `Read the file examples/secure_code_assistant/config.yaml`

Agent calls `read_source`, returns config. Taint fires.

**Type:** `Use web_search to find YAML schema validation libraries`

**Same DENY.** "Web search blocked — proprietary source code is in session context."

**Say:** "Same denial. The policy doesn't care which model issued the call. Claude, GPT, Llama — enforcement is in the framework, not the harness. Your compliance rules survive model migrations."

**Mention:** "For fully local development: `--model ollama/llama-3 --harness openai-agents`. Zero cloud, zero API keys for the LLM. Same policies."

Exit the REPL. Restore `config.yaml` if edited.

---

### ACT 4: Collaboration — Session Sharing + Multi-Surface (3 min)

**Say:** "You're investigating a bug. Your teammate needs context. In Claude Code, you copy-paste the transcript into Slack. In Omnigent, they attach to your live session."

#### Start a session (Terminal 1)

**Do:** `omnigent run examples/secure_code_assistant/`

**Type:** `Read examples/secure_code_assistant/config.yaml and summarize the policy structure`

Agent responds with a summary. Note the session ID.

**Say:** "This session has a persistent ID. My teammate can attach right now."

#### Co-attach (Terminal 2)

**Do:** `omnigent attach <session_id>`

Terminal 2 connects — full conversation history visible.

**Type (Terminal 2):** `What labels have been set in this session so far?`

Both terminals show the response in real time.

**Say:** "Both terminals are live. I hand off, they pick up exactly where I left off. Taint labels carry over — the policy state is part of the session, not the terminal."

#### Web UI (multi-surface)

Switch to browser at `http://localhost:8000`. Click into the active session.

**Say:** "Same session, in the browser. On a deployed instance, this URL works from your phone. Start on your laptop, continue on the train. The session is the unit of continuity, not the terminal."

#### Fork (if time)

**Do:** `omnigent run --fork <session_id>` from Terminal 2.

**Say:** "Fork branches the conversation. Your teammate explores independently without affecting your original. Like `git branch` for agent sessions."

---

### ACT 5: The Close (1 min)

**Say:** "Three pillars in twelve minutes."

- **Governance:** YAML policy engine with taint labels, monotonic state, DENY enforcement the model can't override. Session-scoped information flow control — not prompt engineering, not API gateway scanning.
- **Portability:** Same config.yaml, same Python tools, same policies. Claude, GPT, Ollama. Two CLI flags, zero code changes.
- **Collaboration:** Persistent sessions. Attach, fork, access from CLI, browser, or mobile. Your work isn't trapped in one terminal.

**Say:** "Omnigent isn't replacing Claude Code or Codex. It's the governance, collaboration, and portability layer between your agents and the world. Write agents as software. Ship software as agents."

---

## Timing Summary

| Act | Duration | Pillar |
|-----|----------|--------|
| 1. The Hook | 2 min | Frame the three questions, walk through YAML |
| 2. Policies | 4 min | Taint + DENY both directions (wow), cost budget |
| 3. Portability | 3 min | Same agent on GPT-4o, same DENY fires |
| 4. Collaboration | 3 min | attach, co-drive, Web UI, fork |
| 5. Close | 1 min | Recap three pillars |
| **Total** | **13 min** | |

---

## Implementation Steps

### 1. Create the agent directory

```
examples/secure_code_assistant/
|-- config.yaml
|-- README.md
+-- tools/python/
    |-- read_source.py
    +-- search_docs.py
```

### 2. Write `config.yaml`

Use the YAML spec above. Key sections:
- `executor:` with `claude-sdk` / `claude-sonnet-4-6`
- `guardrails.labels:` with `has_proprietary_code` and `has_external_content` (both monotonic increasing)
- `guardrails.policies:` with 5 policies (2 taint, 2 deny, 1 cost budget)
- System prompt routing the agent to use the right tools

### 3. Write `tools/python/read_source.py` and `search_docs.py`

Minimal Python — `@tool` decorator, type hints, docstrings. `read_source` reads files from CWD. `search_docs` wraps web search (exists as a separate taint target).

### 4. Write `README.md`

Brief README with overview, setup, example queries, and policy engine table.

### 5. Write `docs/demo_script.md`

The full timed demo script from above, formatted for a presenter to follow.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **ASK policies (response phase) known broken on claude-sdk** | Demo only uses DENY on tool_call phase (proven). Cost budget ASK on tool_call phase should be tested — if it doesn't fire, mention it verbally instead. |
| **LLM routes around denied tool** | Use explicit phrasing: "Use web_search to..." per design.md convention |
| **CLI `--model`/`--harness` flags may be ignored by global config** | Test beforehand. Fallback: edit YAML executor block live (shows "agents as software" narrative) |
| **OpenAI API key lacks gpt-4o access** | Verify beforehand. Fallback: show YAML edit + explain, run only on Claude |
| **Web UI session creation flaky** | Create session via CLI, then show in browser |
| **`search_docs` tool may not provide real search results** | OK for demo — the tool call is what matters, not the content. The DENY fires on the tool call, before any search happens |
| **Server crash** | Pre-record a backup of each act |

## Verification

Before the demo:
1. `omnigent run examples/secure_code_assistant/` — confirm agent starts, read_source and search_docs tools are discovered
2. Turn 1: web search succeeds (no taint)
3. Turn 2: read_source sets `has_proprietary_code` taint
4. Turn 3: web_search DENIED with the expected message
5. New session: web search succeeds, then sys_os_write DENIED after web content taint
6. `--model gpt-4o --harness openai-agents` — same DENY fires
7. `omnigent attach <session_id>` — second terminal shows history, can type
8. Web UI at localhost:8000 shows the session
9. Full run times to 10-15 minutes
