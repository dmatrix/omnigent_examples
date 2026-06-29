# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Detailed breakdown of every attribute in `config.yaml`, its role, scope, and nesting.

---

## Top-level metadata (lines 1-7)

| Attribute | Value | Role |
|---|---|---|
| `spec_version` | `1` | Schema version of the Omnigent agent YAML spec. Tells the framework which parser to use. |
| `name` | `secure_code_assistant` | Unique identifier for this agent. Used in session logs, CLI output, and the `omnigent run` resolver. |
| `description` | *(multiline string)* | Human-readable summary. Shown in `omnigent list` and the Web UI agent picker. The `>` folding style collapses newlines into spaces. |

---

## `executor:` — The agent's brain

Tells the framework which LLM provider and model to use.

| Attribute | Value | Role |
|---|---|---|
| `type` | `omnigent` | The executor type. `omnigent` means the framework manages the agent loop (tool dispatch, session state, policy evaluation). |
| `model` | `claude-sonnet-4-6` | Which model to call. Can be overridden at the CLI with `--model`. |
| `config.harness` | `claude-sdk` | Which SDK/protocol adapter to use for API calls. `claude-sdk` = Anthropic's native API. Can be overridden with `--harness`. |

---

## `os_env:` — Environment access

Grants the agent access to the host operating system (shell, filesystem). This is critical for this agent — it needs shell access for grep, find, git log, and file writes.

| Attribute | Value | Role |
|---|---|---|
| `type` | `caller_process` | Inherit the environment of the process that launched `omnigent run`. The agent sees the same filesystem, env vars, and CWD as your terminal. |
| `cwd` | `.` | Working directory. `.` = wherever you ran `omnigent run` from (typically the repo root). |
| `sandbox.type` | `none` | No sandboxing — the agent can read/write anywhere the calling process can. Other options include `docker` or `firecracker` for isolation. |

The `os_env` block makes the framework's built-in shell tools available: `sys_os_write` (write files), `sys_os_edit` (edit files), and general shell execution. These are the tools that the `block_write_after_web` policy targets — it denies `sys_os_write` and `sys_os_edit` after web content has been ingested.

---

## `tools:` — What's declared in config.yaml

The only tool explicitly declared in the YAML is a single builtin:

```yaml
tools:
  builtins:
    - web_search
```

| Tool | Role |
|---|---|
| `web_search` | Framework-provided web search. Listed here to make it available to the agent and targetable by policies. |

### Tools NOT in config.yaml (provided by the framework)

The agent has access to additional tools that don't appear in the YAML. These are important for understanding the policies, which reference tools like `read_source` and `sys_os_write` that you won't find declared in `config.yaml`.

**Auto-discovered Python tools** — Any `.py` file in `tools/python/` with an `@tool`-decorated function is automatically registered at load time. This agent has two:

| File | Tool function | Why it matters |
|---|---|---|
| `tools/python/read_source.py` | `read_source` | Referenced by the `taint_code_read` policy (`on_tools: [read_source]`) |
| `tools/python/search_docs.py` | `search_docs` | Referenced by the `taint_web_search` and `block_search_after_code` policies |

**Implicit shell tools** — Because `os_env` is declared with `sandbox: none`, the framework provides built-in filesystem tools:

| Tool | Why it matters |
|---|---|
| `sys_os_write` | Referenced by the `block_write_after_web` policy (`on_tools: [sys_os_write, sys_os_edit]`) |
| `sys_os_edit` | Also referenced by `block_write_after_web` |
| *(shell execution)* | General shell commands (grep, find, git log). Not targeted by any policy. |

**Key takeaway:** The policies in `guardrails:` reference tool names (`read_source`, `search_docs`, `sys_os_write`, `sys_os_edit`) that are never declared in the `tools:` block. This works because the framework resolves tool names at runtime — auto-discovered tools and implicit shell tools are registered alongside explicitly declared tools. The policy engine can target any of them.

---

## `guardrails:` — Session-scoped governance

This is the core of the example. The guardrails block implements **bidirectional information flow control**: code can't leak out (via web search), and untrusted content can't be written in (via file writes).

### `guardrails.labels:` — Session state tracking

```yaml
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
```

Labels are **session-scoped variables** that track what the agent has seen or done. Each label has:

| Attribute | Role |
|---|---|
| `initial` | Starting value when a new session begins. Both start as `"False"`. |
| `values` | Ordered list of allowed values. The ordering matters for `monotonic`. |
| `monotonic: increasing` | The label can only move forward in the `values` list — from `"False"` to `"True"`, never back. Once set, it cannot be unset for the rest of the session. |

| Label | What it tracks |
|---|---|
| `has_proprietary_code` | The agent has read project source code via `read_source` |
| `has_external_content` | The agent has ingested web content via `web_search` or `search_docs` |

**Why two labels instead of one?** They represent two different taint domains. Reading code doesn't mean the agent has seen web content, and vice versa. The policies enforce flow control in **both directions** — each label gates a different set of tools. This creates a lattice where the order of operations determines what's allowed:

- Read code first, then search -> search blocked (code can't leak out)
- Search first, then write -> write blocked (untrusted content can't be written in)
- Read code first, then write -> write allowed (no external content, so no injection risk)
- Search first, then read code -> both search and write now blocked

---

### `guardrails.policies:` — Rules evaluated on every tool call

#### Taint policies — Tag session state on tool access

| Policy | Fires on | Sets | Notes |
|---|---|---|---|
| `taint_code_read` | `read_source` | `has_proprietary_code: "True"` | Single tool target |
| `taint_web_search` | `web_search`, `search_docs` | `has_external_content: "True"` | Two tool targets — both represent external content ingestion |

Both are `action: allow` with label side-effects — the tool call proceeds, but the session state is updated.

**Note on `taint_web_search`:** This policy targets two tools (`on_tools: [web_search, search_docs]`). Both represent the same taint domain (external content), so they share a label. The `on_tools` list is how you express "any of these tools triggers the same label."

#### Deny policies — Enforce information flow boundaries

```yaml
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
```

| Attribute | Role |
|---|---|
| `condition` | **Pre-condition**: this policy only activates when `has_proprietary_code` is `"True"`. If the label is still `"False"`, the policy is skipped entirely. |
| `action: deny` | The tool call is blocked. The framework returns the `reason` message to the model instead of executing the tool. |
| `reason` | Human-readable explanation returned to the LLM (and shown to the user) when the tool call is denied. |
| `on_phases: [tool_call]` | Intercept during the tool_call phase, before execution. |
| `on_tools` | Which tools to block. `block_search_after_code` blocks both `web_search` and `search_docs`. |

| Policy | Condition | Blocks | Direction |
|---|---|---|---|
| `block_search_after_code` | `has_proprietary_code = True` | `web_search`, `search_docs` | Code can't leak **out** |
| `block_write_after_web` | `has_external_content = True` | `sys_os_write`, `sys_os_edit` | Untrusted content can't be written **in** |

**Bidirectional flow control:** These two deny policies create a two-way barrier. The first prevents data exfiltration (code leaking via search queries). The second prevents data injection (web content being written into project files). Together they enforce an information flow lattice where each direction is independently gated.

**Note on `block_write_after_web`:** This policy targets `sys_os_write` and `sys_os_edit` — the implicit shell tools provided by `os_env`. These tool names are framework-defined (not user-defined), so you need to know the framework's naming convention to target them in policies.

#### Cost policy — Budget guardrail

```yaml
cost_guard:
  type: function
  function:
    path: omnigent.policies.builtins.cost.cost_budget
    arguments:
      max_cost_usd: 1.0
      ask_thresholds_usd: [0.05]
```

| Attribute | Role |
|---|---|
| `function.path` | `omnigent.policies.builtins.cost.cost_budget` — a different policy factory than the taint/deny policies. This is a built-in cost tracker, not a fixed-action callable. |
| `max_cost_usd` | Hard cap: the session is terminated if cumulative LLM cost exceeds $1. |
| `ask_thresholds_usd` | `[0.05]` — pause and ask the user for approval when cost crosses $0.05. |

This policy has no `condition` and no `on_tools` — it evaluates on every turn regardless of which tool is called. It's a different category of guardrail: resource governance rather than information flow.

---

## `prompt:` — The agent's system prompt

A `|` literal block (preserves newlines). Shorter than the telco agent's prompt because this agent doesn't need a database schema. Key directives:

1. **Role** — "You are a secure code assistant"
2. **Tool roster** — Four tools: `read_source`, `search_docs`, `web_search`, shell access
3. **Tool-first** — "Use tools for every answer. Do not answer from training data when tools can provide current, accurate information."

The prompt does not mention the policies — the agent doesn't need to know about them. The PolicyEngine enforces the rules regardless of what the prompt says. This is a key design principle: governance is in the framework, not in the prompt.

---

## What's NOT in this config

- **No sub-agents** — this is a single-agent config. All tools are Python functions, builtins, or implicit shell tools.
- **No `tools/python/` listing in YAML** — Python tools are auto-discovered from the `tools/python/` directory; they don't need to be declared in config.yaml.
- **No response-phase policies** — all policies fire on `tool_call` phase (before execution). Response-phase policies (which evaluate the model's output) are not used here.

---

## Nesting summary

```
config.yaml
+-- spec_version                  # schema version
+-- name                          # agent identifier
+-- description                   # human-readable summary
+-- executor                      # LLM config
|   +-- type
|   +-- model
|   +-- config.harness
+-- os_env                        # filesystem/shell access
|   +-- type                      #   (also provides sys_os_write, sys_os_edit)
|   +-- cwd
|   +-- sandbox.type
+-- tools                         # callable tools
|   +-- builtins
|       +-- web_search
+-- guardrails                    # session-scoped governance
|   +-- labels                    # session state variables
|   |   +-- has_proprietary_code  #   code taint (monotonic)
|   |   +-- has_external_content  #   web content taint (monotonic)
|   +-- policies                  # rules evaluated on every tool call
|       +-- taint_code_read       #   ALLOW read_source, set has_proprietary_code
|       +-- taint_web_search      #   ALLOW web_search/search_docs, set has_external_content
|       +-- block_search_after_code    # DENY web_search/search_docs if has_proprietary_code
|       +-- block_write_after_web      # DENY sys_os_write/sys_os_edit if has_external_content
|       +-- cost_guard            #   budget cap: $1 max, $0.05 ASK threshold
+-- prompt                        # system prompt (role + tool roster)
```

---

## Policy evaluation flow

This agent has **bidirectional** flow control. Here are both directions:

### Direction 1: Code can't leak out

```
Agent calls web_search (after having read source code)
        |
        v
Phase: tool_call
        |
        v
1. taint_web_search fires      --> ALLOW, set has_external_content = True
2. block_search_after_code?    --> check has_proprietary_code label
   - if True  --> DENY (return reason to model, tool never executes)
   - if False --> skip
        |
        v
All policies passed? --> tool executes
```

### Direction 2: Untrusted content can't be written in

```
Agent calls sys_os_write (after having searched the web)
        |
        v
Phase: tool_call
        |
        v
1. block_write_after_web?      --> check has_external_content label
   - if True  --> DENY (return reason to model, tool never executes)
   - if False --> skip
        |
        v
All policies passed? --> tool executes
```

### Combined: both taints active

If the agent has both read code AND searched the web (both labels set), then:
- `web_search` and `search_docs` are blocked (code can't leak)
- `sys_os_write` and `sys_os_edit` are blocked (web content can't be injected)
- `read_source` still works (reading more code is fine)
- Shell commands (grep, find, git log) still work (read-only, no policy targets them)

The agent can still answer questions — it just can't search or write files.
