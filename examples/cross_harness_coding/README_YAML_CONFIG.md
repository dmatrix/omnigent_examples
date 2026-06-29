# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Detailed breakdown of every attribute in `config.yaml`, its role, scope, and nesting.

---

## Top-level metadata (lines 1-6)

| Attribute | Value | Role |
|---|---|---|
| `spec_version` | `1` | Schema version of the Omnigent agent YAML spec. Tells the framework which parser to use. |
| `name` | `cross_harness_coding` | Unique identifier for this agent. Used in session logs, CLI output, and the `omnigent run` resolver. |
| `description` | *(multiline string)* | Human-readable summary. Shown in `omnigent list` and the Web UI agent picker. The `>` folding style collapses newlines into spaces. |

---

## `executor:` — The supervisor's brain

This block tells the framework which LLM provider and model to use for the **supervisor agent** (the top-level agent that the user talks to).

| Attribute | Value | Role |
|---|---|---|
| `type` | `omnigent` | The executor type. `omnigent` means the framework manages the agent loop (tool dispatch, session state, policy evaluation). |
| `model` | `claude-sonnet-4-6` | Which model to call. Can be overridden at the CLI with `--model`. |
| `config.harness` | `claude-sdk` | Which SDK/protocol adapter to use for API calls. `claude-sdk` = Anthropic's native API. Can be overridden with `--harness`. |

**Scope:** This executor only governs the supervisor. Each sub-agent has its own `executor:` block.

---

## `prompt:` — The supervisor's system prompt

A `|` literal block (preserves newlines). This is the system message sent to the supervisor model on every turn. It defines:

1. **Role** — "You are a coding supervisor"
2. **Hard constraint** — "You MUST delegate all work — never write or review code yourself"
3. **Agent roster** — Names and capabilities of `impl_worker` and `review_worker`
4. **Workflow** — The sequential implement -> review -> revise loop
5. **Transparency rule** — "Always tell the user which agent is working"

The supervisor's prompt is the only place the orchestration logic lives. There's no code — the LLM follows these instructions to decide when to call which sub-agent tool.

---

## `os_env:` — The supervisor's environment access

Grants the supervisor access to the host operating system (shell, filesystem).

| Attribute | Value | Role |
|---|---|---|
| `type` | `caller_process` | Inherit the environment of the process that launched `omnigent run`. The agent sees the same filesystem, env vars, and CWD as your terminal. |
| `cwd` | `.` | Working directory. `.` = wherever you ran `omnigent run` from (typically the repo root). |
| `sandbox.type` | `none` | No sandboxing — the agent can read/write anywhere the calling process can. Other options include `docker` or `firecracker` for isolation. |

**Scope:** This `os_env` is the supervisor's own. Each sub-agent declares its own `os_env` independently (they happen to be identical here, so all three share the same filesystem view).

---

## `tools:` — Sub-agent declarations

The `tools:` block declares what tools the supervisor can call. In this config, there are no Python tools or builtins — only two **sub-agents**, each declared as a tool of `type: agent`.

When the supervisor's LLM decides to call `impl_worker(...)` or `review_worker(...)`, the framework spawns a child agent session, passes the argument as the task, and returns the sub-agent's final response as the tool result.

---

### `tools.impl_worker:` — The implementation sub-agent

| Attribute | Path | Role |
|---|---|---|
| `type` | `impl_worker.type` | `agent` — this tool is a sub-agent, not a Python function or builtin. |
| `prompt` | `impl_worker.prompt` | System prompt for the implementation agent. Defines its role (coder), output directory (`omnigent_generated_code/`), and rules (write tests, run them, report results). |
| `executor.type` | `impl_worker.executor.type` | `omnigent` — same executor type as the supervisor. |
| `executor.model` | `impl_worker.executor.model` | `gpt-5.4` — this sub-agent runs on OpenAI, not Anthropic. This is the cross-harness part. |
| `executor.config.harness` | `impl_worker.executor.config.harness` | `codex` — uses the Codex CLI harness (requires `codex` binary on PATH). |
| `os_env` | `impl_worker.os_env` | Same as supervisor — `caller_process`, `cwd: .`, no sandbox. Shares the same filesystem so it can write files the reviewer can read. |

**Key point:** The impl_worker's `executor` is completely independent from the supervisor's. Different model, different harness, different provider. The framework handles the protocol translation.

---

### `tools.review_worker:` — The review sub-agent

| Attribute | Path | Role |
|---|---|---|
| `type` | `review_worker.type` | `agent` — sub-agent tool. |
| `prompt` | `review_worker.prompt` | System prompt for the reviewer. Reads from `omnigent_generated_code/`, evaluates on four dimensions (correctness, style, security, performance), returns a structured verdict (PASS/REVISE/REJECT). |
| `executor.type` | `review_worker.executor.type` | `omnigent` |
| `executor.model` | `review_worker.executor.model` | `claude-sonnet-4-6` — same model as the supervisor but running as a separate agent session. |
| `executor.config.harness` | `review_worker.executor.config.harness` | `claude-sdk` — same harness as the supervisor. |
| `os_env` | `review_worker.os_env` | Same filesystem access — reads the files that `impl_worker` wrote. |

---

## What's NOT in this config

Compared to the telco and secure_code_assistant examples, this config has **no `guardrails:` block** — no labels, no policies. That's intentional: this example focuses purely on composition (cross-harness delegation), not governance. It also has no `tools.builtins:` (no web_search) and no `tools/python/` directory — both sub-agents use shell access only via `os_env`.

---

## Nesting summary

```
config.yaml
+-- spec_version          # schema version
+-- name                  # agent identifier
+-- description           # human-readable summary
+-- executor              # SUPERVISOR's LLM config
|   +-- type
|   +-- model
|   +-- config.harness
+-- prompt                # SUPERVISOR's system prompt
+-- os_env                # SUPERVISOR's filesystem access
|   +-- type
|   +-- cwd
|   +-- sandbox.type
+-- tools                 # SUPERVISOR's callable tools
    +-- impl_worker       # sub-agent tool #1
    |   +-- type: agent
    |   +-- prompt        # IMPL's system prompt
    |   +-- executor      # IMPL's LLM config (different harness!)
    |   +-- os_env        # IMPL's filesystem access
    +-- review_worker     # sub-agent tool #2
        +-- type: agent
        +-- prompt        # REVIEWER's system prompt
        +-- executor      # REVIEWER's LLM config
        +-- os_env        # REVIEWER's filesystem access
```

Each sub-agent is a fully self-contained agent definition nested inside the parent's `tools:` block. They get their own model, harness, prompt, and environment — the only thing they share with the supervisor is the session tree.

---

## What is the session tree?

The **session tree** is the hierarchical session structure that ties the supervisor and its sub-agents together:

```
Session: cross_harness_coding (root)
+-- supervisor turn 1
|   +-- impl_worker (child session)   <-- spawned as tool call
|   +-- review_worker (child session) <-- spawned as tool call
+-- supervisor turn 2
|   +-- impl_worker (child session)   <-- revision pass
...
```

**Shared across the tree:**

- **Session identity** — one persistent session ID for the whole conversation (used by `omnigent attach`, session logs, Web UI)
- **Filesystem** — all agents see the same CWD, so impl_worker can write files and review_worker can read them
- **Policy state** — if this config had guardrails, taint labels set by a sub-agent would propagate up to the session level (relevant for telco/secure_code examples, not this one)
- **Conversation history** — the supervisor's transcript includes sub-agent tool calls and their results

**Not shared:**

- **Context window** — each sub-agent has its own context window with its own system prompt; the reviewer doesn't see the implementer's full conversation, only what the supervisor passes as the tool call argument
- **Executor** — each agent talks to its own LLM provider independently

The session tree is what makes cross-harness delegation feel like one conversation to the user, even though three different LLM sessions are involved under the hood.
