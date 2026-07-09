# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Attribute-level walkthrough of `config.yaml` — covers auto-discovery, implicit tools, guardrail labels, and the policy evaluation flow.

---

## `executor:` — The agent's brain

| Attribute | Value | Notes |
|---|---|---|
| `model` | `claude-sonnet-4-6` | Override at CLI with `--model`. |
| `config.harness` | `claude-sdk` | Override with `--harness`. |

---

## `os_env:` — Environment access

Declares `caller_process` with `sandbox: none` — the agent inherits the launching shell's filesystem and env vars. This makes the framework's built-in shell tools available: `sys_os_write`, `sys_os_edit`, and general shell execution. The `block_write_after_web` policy targets `sys_os_write` and `sys_os_edit`.

---

## `tools:` — What's declared in config.yaml

The only tool explicitly declared is a single builtin:

```yaml
tools:
  builtins:
    - web_search
```

### Tools NOT in config.yaml (provided by the framework)

The policies reference tools like `read_source` and `sys_os_write` that you won't find in the `tools:` block. They come from two sources:

**Auto-discovered Python tools** — Any `.py` file in `tools/python/` with an `@tool`-decorated function is registered at load time:

| File | Tool function | Referenced by |
|---|---|---|
| `tools/python/read_source.py` | `read_source` | `taint_code_read` policy |
| `tools/python/search_docs.py` | `search_docs` | `taint_web_search` and `block_search_after_code` policies |

**Implicit shell tools** — Because `os_env` is declared, the framework provides:

| Tool | Referenced by |
|---|---|
| `sys_os_write` | `block_write_after_web` policy |
| `sys_os_edit` | `block_write_after_web` policy |

The policy engine resolves tool names at runtime — auto-discovered and implicit tools are registered alongside explicit builtins.

---

## `guardrails:` — Session-scoped governance

Implements **bidirectional information flow control**: code can't leak out (via web search), and untrusted content can't be written in (via file writes).

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

| Label | What it tracks |
|---|---|
| `has_proprietary_code` | Agent has read project source code via `read_source` |
| `has_external_content` | Agent has ingested web content via `web_search` or `search_docs` |

`monotonic: increasing` means the label can only move from `"False"` to `"True"`, never back. Once set, it persists for the session.

**Why two labels?** They represent two taint domains. The policies enforce flow control in **both directions** — each label gates a different set of tools:

- Read code first, then search → search blocked (code can't leak out)
- Search first, then write → write blocked (untrusted content can't be written in)
- Read code first, then write → write allowed (no external content, so no injection risk)
- Search first, then read code → both search and write now blocked

### Taint policies — Tag session state on tool access

| Policy | Fires on | Sets | Action |
|---|---|---|---|
| `taint_code_read` | `read_source` | `has_proprietary_code: "True"` | ALLOW (side-effect only) |
| `taint_web_search` | `web_search`, `search_docs` | `has_external_content: "True"` | ALLOW (side-effect only) |

`taint_web_search` targets two tools because both represent external content ingestion.

### Deny policies — Enforce information flow boundaries

| Policy | Condition | Blocks | Direction |
|---|---|---|---|
| `block_search_after_code` | `has_proprietary_code = True` | `web_search`, `search_docs` | Code can't leak **out** |
| `block_write_after_web` | `has_external_content = True` | `sys_os_write`, `sys_os_edit` | Untrusted content can't be written **in** |

The `condition` field is a pre-check: if the label is still `"False"`, the policy is skipped entirely. When it fires, the framework returns the `reason` string to the model — the tool never executes.

### Cost policy

```yaml
cost_guard:
  type: function
  function:
    path: omnigent.policies.builtins.cost.cost_budget
    arguments:
      max_cost_usd: 1.0
      ask_thresholds_usd: [0.05]
```

No `condition` or `on_tools` — evaluates on every turn. Hard cap at $1, ASK at $0.05.

---

## `prompt:`

Defines role, tool roster (4 tools), and a tool-first directive. Does not mention policies — the PolicyEngine enforces rules regardless of what the prompt says.

**Not in this config:** No sub-agents (single-agent config), no `tools/python/` listing in YAML (auto-discovered), no response-phase policies.

---

## Nesting summary

```
config.yaml
+-- spec_version
+-- name
+-- description
+-- executor
|   +-- type, model, config.harness
+-- os_env
|   +-- type, cwd, sandbox.type
+-- tools
|   +-- builtins: [web_search]
+-- guardrails
|   +-- labels
|   |   +-- has_proprietary_code  (monotonic)
|   |   +-- has_external_content  (monotonic)
|   +-- policies
|       +-- taint_code_read       ALLOW read_source, set has_proprietary_code
|       +-- taint_web_search      ALLOW web_search/search_docs, set has_external_content
|       +-- block_search_after_code    DENY web_search/search_docs if has_proprietary_code
|       +-- block_write_after_web      DENY sys_os_write/sys_os_edit if has_external_content
|       +-- cost_guard            $1 max, $0.05 ASK
+-- prompt
```

---

## Policy evaluation flow

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

If both labels are set:
- `web_search` and `search_docs` blocked (code can't leak)
- `sys_os_write` and `sys_os_edit` blocked (web content can't be injected)
- `read_source` still works
- Shell commands (grep, find, git log) still work (no policy targets them)
