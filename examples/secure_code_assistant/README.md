# Secure Code Assistant with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**Coding assistant with session-scoped information flow control — blocks web search after code read, blocks file writes after web search.**

![Secure Code Assistant Architecture](images/secure_code_assistant_architecture.svg)

---

## Overview

Coding assistant with session-scoped information flow control. The PolicyEngine enforces DENY decisions at the framework layer — the LLM never sees the denied tool call. Same policies fire on Claude or GPT because enforcement lives in the runner, not the harness.

The agent has two custom tools and one builtin:

- **`read_source`** -- Reads source files from the project directory. Triggers the `has_proprietary_code` label.

- **`search_docs`** -- Searches the web for technical documentation (thin stub for taint separation). Triggers the `has_external_content` label.

- **`web_search`** -- Builtin web search. Triggers the `has_external_content` label. Blocked after proprietary code access.

- **Shell access** -- Run grep, find, git log, etc. via the OS environment.

The policy engine enforces two key boundaries:

1. **Code can't leak out** -- Once proprietary source code is read, web search is denied (search queries could leak implementation details to external search engines).
2. **Untrusted content can't be written in** -- Once web content is ingested, file writes are denied (preventing injection of malicious code or license-incompatible snippets).

Labels are **monotonic** -- once set, they cannot be unset for the session. This is session-scoped information flow control, not request-level scanning.

A **cost budget** guardrail caps total spend at $1 with a $0.05 approval threshold.

---

## Get Started

No database setup needed. The agent reads source files from the current working directory.

---

## Run on Databricks

Override the model to route through Databricks AI Gateway:

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/secure_code_assistant/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

The CLI opens an interactive REPL. A Web UI is also available at the Databricks Apps URL.

---

## Run Locally

The default config uses `claude-sonnet-4-6` via direct Anthropic API. No Databricks dependency.

### 1. Configure credentials (one-time)

```bash
omnigent setup
```

### 2. Export your API key

```bash
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
```

### 3. Run the agent

```bash
# Default: Claude Sonnet via claude-sdk
omnigent run examples/secure_code_assistant/

# Fresh session (no persistence)
omnigent run examples/secure_code_assistant/ --no-session

# Override model and harness
omnigent run examples/secure_code_assistant/ --model gpt-5.5 --harness openai-agents
```

---

## Example Queries

**Clean session — web search works:**
```
Search the web for Python asyncio best practices
```

**Read source code (sets taint):**
```
Read the file examples/secure_code_assistant/tools/python/read_source.py and explain it
```

**Web search denied after code read:**
```
Use web_search to find how other projects implement tool decorators
→ DENIED: "Web search blocked — proprietary source code is in session context."
```

**Reverse flow — start a new session:**
```
Search the web for the latest FastAPI middleware patterns
→ Works (sets has_external_content)

Write a new middleware file at middleware.py with what you found
→ DENIED: "File write blocked — untrusted web content is in session context."
```

**Cross-verify — code read doesn't block writes:**
```
Read the file examples/secure_code_assistant/config.yaml
→ Works (sets has_proprietary_code only)

Write a summary to notes.txt
→ Works (has_external_content is not set)
```

---

## Policy Engine

The agent's `config.yaml` defines session-scoped guardrails:

### Labels

| Label | Triggered by | Monotonic |
|---|---|---|
| `has_proprietary_code` | `read_source` | Yes (once set, cannot be unset) |
| `has_external_content` | `web_search`, `search_docs` | Yes |

### Policies

| Policy | Condition | Action | Reason |
|---|---|---|---|
| `taint_code_read` | *(always)* | ALLOW `read_source`, set label | Track proprietary code access |
| `taint_web_search` | *(always)* | ALLOW `web_search`/`search_docs`, set label | Track external content ingestion |
| `block_search_after_code` | `has_proprietary_code = True` | DENY `web_search`, `search_docs` | Prevent code leakage via search queries |
| `block_write_after_web` | `has_external_content = True` | DENY `sys_os_write`, `sys_os_edit` | Prevent injection of untrusted web content |
| `cost_guard` | *(always)* | Budget: $1 max, $0.05 ASK | Cap session cost |

---

## Tools

| Tool | Source | Description |
|---|---|---|
| `read_source` | `tools/python/read_source.py` | Reads a source file from the project directory |
| `search_docs` | `tools/python/search_docs.py` | Stub web doc search (taint target) |
| `web_search` | Builtin | General web search |

---

## How to Demo

See [demo.md](demo.md) for a timed walkthrough (10-15 min).
