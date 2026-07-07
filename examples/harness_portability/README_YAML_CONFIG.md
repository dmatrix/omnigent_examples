# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Detailed breakdown of every attribute across all five config files (supervisor + four sub-agents), their roles, scope, and nesting.

---

## Top-level metadata (lines 1-6)

| Attribute | Value | Role |
|---|---|---|
| `spec_version` | `1` | Schema version of the Omnigent agent YAML spec. Tells the framework which parser to use. |
| `name` | `harness_portability` | Unique identifier for the supervisor agent. Used in session logs, CLI output, and the `omnigent run` resolver. |
| `description` | *(multiline string)* | Human-readable summary shown in `omnigent list` and the Web UI. The `>` folding style collapses newlines into spaces. |

---

## `executor:` — The supervisor's brain

This block tells the framework which LLM provider and model to use for the **supervisor agent** (the top-level agent that the user talks to).

| Attribute | Value | Role |
|---|---|---|
| `type` | `omnigent` | The executor type. `omnigent` means the framework manages the agent loop (tool dispatch, session state, policy evaluation). |
| `model` | `claude-sonnet-4-6` | Which model to call. Uses the direct Anthropic API — no Databricks dependency. Can be overridden at the CLI with `--model`. |
| `config.harness` | `claude-sdk` | Which SDK/protocol adapter to use for API calls. `claude-sdk` = Anthropic's native API. Can be overridden with `--harness`. |

**Scope:** This executor only governs the supervisor. Each sub-agent has its own `executor:` block with its own harness and model. CLI `--model`/`--harness` flags override only the top-level agent — sub-agents keep their hardcoded values.

---

## `prompt:` — The supervisor's system prompt

A `|` literal block (preserves newlines). This is the system message sent to the supervisor model on every turn. It defines:

1. **Role** — "You are a Code Project Health Inspector supervisor"
2. **Interaction model** — If the user provides a GitHub URL in their message, proceed directly. Otherwise, ask: "Enter the public GitHub URL to inspect:"
3. **MLflow tracing** — Silently invokes `/setup-mlflow-tracing-claude` and `/setup-mlflow-tracing-codex` on session start to enable tracing for supported harnesses.
4. **Delegation** — The supervisor MUST delegate all inspection work to four sub-agents. It does not analyze the repo itself — it clones, dispatches, and assembles the report.
4. **Agent roster** — Names, categories, and harnesses of the four sub-agents:
   - `structure_inspector` — Project Structure & Documentation (Claude SDK)
   - `test_inspector` — Test Coverage & CI (Codex / OpenAI)
   - `dependency_inspector` — Dependency Health (Pi)
   - `security_inspector` — Code Quality & Security (Hermes)
5. **Report assembly** — Collect findings from all four sub-agents, assign letter grades (A/B/C/D/F) per category, compute an overall score, write `health_report.md`, and print the full report in conversation.
6. **Transparency rule** — "Always tell the user which sub-agent is working on each category and which harness it runs on"

**Why the prompt describes capabilities, not tool names:** Each harness exposes filesystem tools differently (`sys_os_shell` in Omnigent, `Bash` in Claude Code, shell execution in Codex). The prompt says "use shell tools (find, grep, wc, cat, head, git log)" rather than naming specific tools. This is what makes the same prompt work unchanged across all four harnesses — both in the supervisor and in every sub-agent.

---

## `os_env:` — Environment access

Grants the agent access to the host operating system (shell, filesystem).

| Attribute | Value | Role |
|---|---|---|
| `type` | `caller_process` | Inherit the shell environment of the process that launched `omnigent run` — same filesystem, env vars, and CWD. |
| `cwd` | `.` | Working directory. `.` = wherever you ran `omnigent run` from (typically the repo root). |
| `sandbox.type` | `none` | No sandboxing — the agent can read/write anywhere the calling process can. Needed for `git clone` to a temp directory. |

**Scope:** All five agents (supervisor + four sub-agents) declare the same `os_env` block. They share the same filesystem view. The supervisor clones the repo and the sub-agents read from the cloned path.

---

## `tools:` — Sub-agent references

The `tools:` block declares what the supervisor can call. It references four sub-agents by name — each lives in its own directory under `agents/`.

```yaml
tools:
  agents:
    - structure_inspector
    - test_inspector
    - dependency_inspector
    - security_inspector
```

The framework discovers `agents/<name>/config.yaml` for each entry, registers them as callable tools, and spawns child sessions when the supervisor invokes them. This is the same pattern used in [cross_harness_coding](../cross_harness_coding/).

**Key difference from cross_harness_coding:** That example uses two sub-agents on two harnesses. This example uses four sub-agents on four different harnesses — one per inspection category.

---

## Sub-agent configs

Each sub-agent is a fully self-contained agent definition in its own directory under `agents/`. They get their own model, harness, prompt, and guardrails — the only thing they share with the supervisor is the session tree and filesystem.

### `agents/structure_inspector/config.yaml` — Project Structure & Documentation

| Attribute | Value | Role |
|---|---|---|
| `name` | `structure_inspector` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `executor.model` | `claude-sonnet-4-6` | Runs on Claude via direct Anthropic API. |
| `executor.config.harness` | `claude-sdk` | Same harness as the supervisor. |
| `prompt` | *(literal block)* | Inspects README, LICENSE, .gitignore, directory organization, contributor docs. |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as all other agents. |
| `guardrails.policies.cost_guard` | `cost_budget`, $5.00 max, $1.00 ASK | Per-invocation cost cap. |
| `guardrails.policies.tool_call_limit` | `max_tool_calls_per_session`, limit 250 | Per-invocation tool call cap. |

### `agents/test_inspector/config.yaml` — Test Coverage & CI

| Attribute | Value | Role |
|---|---|---|
| `name` | `test_inspector` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `executor.model` | `gpt-5.4` | Runs on OpenAI via direct API. **Different provider** from the supervisor. |
| `executor.config.harness` | `codex` | Uses the Codex CLI harness (requires `codex` binary on PATH). |
| `prompt` | *(literal block)* | Inspects test files, test-to-source ratio, CI config, test framework, coverage config. |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as all other agents. |
| `guardrails.policies.cost_guard` | `cost_budget`, $5.00 max, $1.00 ASK | Per-invocation cost cap. |
| `guardrails.policies.tool_call_limit` | `max_tool_calls_per_session`, limit 250 | Per-invocation tool call cap. |

### `agents/dependency_inspector/config.yaml` — Dependency Health

| Attribute | Value | Role |
|---|---|---|
| `name` | `dependency_inspector` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `executor.model` | `claude-sonnet-4-6` | Runs on Claude via the Pi harness. |
| `executor.config.harness` | `pi` | Uses the Pi CLI harness (requires `@earendil-works/pi-coding-agent`). |
| `prompt` | *(literal block)* | Inspects dependency manifests, pinning practices, lock files, dev vs production separation. |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as all other agents. |
| `guardrails.policies.cost_guard` | `cost_budget`, $5.00 max, $1.00 ASK | Per-invocation cost cap. |
| `guardrails.policies.tool_call_limit` | `max_tool_calls_per_session`, limit 250 | Per-invocation tool call cap. |

### `agents/security_inspector/config.yaml` — Code Quality & Security

| Attribute | Value | Role |
|---|---|---|
| `name` | `security_inspector` | Must match the name in the parent's `tools.agents` list. |
| `description` | *(multiline)* | Human-readable summary shown to the supervisor LLM as the tool description. |
| `executor.model` | `claude-sonnet-4-6` | Runs on Claude via the Hermes harness. |
| `executor.config.harness` | `hermes` | Uses the Hermes CLI harness. |
| `prompt` | *(literal block)* | Scans for large files, hardcoded secrets, dangerous functions, code hygiene markers, security config. |
| `os_env` | `caller_process`, `cwd: .`, `sandbox: none` | Same filesystem access as all other agents. |
| `guardrails.policies.cost_guard` | `cost_budget`, $5.00 max, $1.00 ASK | Per-invocation cost cap. |
| `guardrails.policies.tool_call_limit` | `max_tool_calls_per_session`, limit 250 | Per-invocation tool call cap. |

---

## `guardrails:` — Layered cost and safety governance

This config uses **layered governance** — the supervisor has session-wide policies, and each sub-agent has its own per-invocation cost cap. No labels, no taint, no deny policies.

### Supervisor guardrails (session-wide)

The supervisor has one policy: a cost budget.

```yaml
guardrails:
  policies:
    cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.cost_budget
        arguments:
          max_cost_usd: 5.0
          ask_thresholds_usd: [1.00]
```

| Policy | Function | Role |
|---|---|---|
| `cost_guard` | `cost_budget` | Session-wide cost governance — ASKs for approval at $1.00 (soft checkpoint), DENYs further tool calls at $5.00 (hard limit). The session stays alive — switch to a cheaper model or start a fresh session to continue. Tracks cumulative LLM spend across the supervisor and all sub-agent calls. |

The supervisor has no tool call limit — it only makes a handful of calls (clone, dispatch four sub-agents, write report). Tool call limits live on the sub-agents where the heavy shell work happens.

### Sub-agent guardrails (per-invocation)

Each sub-agent has two policies: a cost budget and a tool call limit.

```yaml
guardrails:
  policies:
    cost_guard:
      type: function
      function:
        path: omnigent.policies.builtins.cost.cost_budget
        arguments:
          max_cost_usd: 5.0
          ask_thresholds_usd: [1.00]
    tool_call_limit:
      type: function
      function:
        path: omnigent.policies.builtins.safety.max_tool_calls_per_session
        arguments:
          limit: 250
```

| Policy | Function | Role |
|---|---|---|
| `cost_guard` | `cost_budget` | Per-invocation cost governance — ASKs for approval at $1.00, DENYs further tool calls at $5.00. Prevents any one inspection from running away. |
| `tool_call_limit` | `max_tool_calls_per_session` | Per-invocation rate limit — denies tool calls once the sub-agent exceeds 250 calls. Prevents runaway shell loops during inspection. |

**Why two levels?** The per-invocation `cost_guard` ($5.00) on each sub-agent catches runaway inspections early. The session-wide `cost_guard` ($5.00) on the supervisor provides the overall ceiling. Both DENY further tool calls at the hard limit — the session stays alive but you need to switch models or start fresh to continue. The `tool_call_limit` (250) on each sub-agent adds a hard cap on shell activity — the supervisor doesn't need one because it only makes a handful of calls. This is the same layered pattern used in [cross_harness_coding](../cross_harness_coding/).

---

## Swapping a sub-agent's harness

To change which harness a sub-agent uses, edit one line in its `config.yaml`:

```yaml
# agents/test_inspector/config.yaml — change from Codex to Claude SDK
executor:
  type: omnigent
  model: claude-sonnet-4-6      # was: gpt-5.4
  config:
    harness: claude-sdk          # was: codex
```

The sub-agent's prompt, `os_env`, and guardrails stay identical. Only the `executor:` block changes — same pattern as the top-level harness swap, just applied to a child agent.

**Note:** CLI `--model`/`--harness` flags only override the top-level agent (the supervisor). To swap a sub-agent's harness, you must edit its `config.yaml` directly. This is a framework constraint, not a config choice.

---

## What's NOT in this config

Compared to the other examples in this repo, this config is intentionally focused:

- **No `tools/python/` directory** — zero custom tool code in the entire example. All capabilities come from `os_env`.
- **No labels** — no taint tracking or session state beyond the sub-agent tool call counters.
- **No taint/deny policies** — no information flow control. See [secure_code_assistant](../secure_code_assistant/) and [telco_customer_agent](../telco_customer_agent/) for those patterns.
- **No `web_search` or other builtins** — just shell tools from `os_env`.

What it **does** have that the previous single-agent version did not:

- **Sub-agents** — four specialist agents, each on a different harness, following the same composition pattern as [cross_harness_coding](../cross_harness_coding/).
- **`tools:` block** — `agents:` list referencing all four sub-agents.
- **Layered guardrails** — session-wide cost + tool call limit on the supervisor, per-invocation cost on each sub-agent.

---

## Nesting summary

```
harness_portability/
+-- config.yaml                        # SUPERVISOR config (harness: claude-sdk)
|   +-- spec_version
|   +-- name
|   +-- description
|   +-- executor                       # SUPERVISOR's LLM config
|   |   +-- type
|   |   +-- model                      # claude-sonnet-4-6
|   |   +-- config.harness             # claude-sdk
|   +-- prompt                         # asks for URL (or detects inline)
|   +-- os_env                         # filesystem access
|   |   +-- type
|   |   +-- cwd
|   |   +-- sandbox.type
|   +-- tools                          # sub-agent references
|   |   +-- agents: [structure_inspector, test_inspector,
|   |                 dependency_inspector, security_inspector]
|   +-- guardrails                     # session-scoped governance
|       +-- policies
|           +-- cost_guard             # cost budget: $5.00 max, $1.00 ASK
+-- agents/
    +-- structure_inspector/
    |   +-- config.yaml                # harness: claude-sdk
    |       +-- guardrails
    |           +-- cost_guard         # per-invocation: $5.00 max, $1.00 ASK
    |           +-- tool_call_limit    # per-invocation: 250 calls max
    +-- test_inspector/
    |   +-- config.yaml                # harness: codex (gpt-5.4)
    |       +-- guardrails
    |           +-- cost_guard         # per-invocation: $5.00 max, $1.00 ASK
    |           +-- tool_call_limit    # per-invocation: 250 calls max
    +-- dependency_inspector/
    |   +-- config.yaml                # harness: pi
    |       +-- guardrails
    |           +-- cost_guard         # per-invocation: $5.00 max, $1.00 ASK
    |           +-- tool_call_limit    # per-invocation: 250 calls max
    +-- security_inspector/
        +-- config.yaml                # harness: hermes
            +-- guardrails
                +-- cost_guard         # per-invocation: $5.00 max, $1.00 ASK
                +-- tool_call_limit    # per-invocation: 250 calls max
```

Five files. Four harnesses. One session tree. Zero custom tool code.

---

## What is the session tree?

The **session tree** is the hierarchical session structure that ties the supervisor and its sub-agents together:

```
Session: harness_portability (root)
+-- supervisor turn 1 (clone repo, dispatch)
|   +-- structure_inspector (child session, claude-sdk)
|   +-- test_inspector (child session, codex)
|   +-- dependency_inspector (child session, pi)
|   +-- security_inspector (child session, hermes)
+-- supervisor turn 2 (assemble report, write health_report.md)
```

**Shared across the tree:**

- **Session identity** — one session ID for the whole conversation (`omnigent attach`, logs, Web UI)
- **Filesystem** — all agents see the same CWD, so the supervisor clones the repo and sub-agents read from the cloned path
- **Policy state** — the supervisor's `cost_guard` tracks cumulative cost across all sub-agent calls; each sub-agent's `tool_call_limit` counts tool calls within its own invocation
- **Conversation history** — the supervisor's transcript includes sub-agent calls and results

**Not shared:**

- **Context window** — each sub-agent has its own context and system prompt; it only sees what the supervisor passes as the tool call argument
- **Executor** — each agent talks to its own LLM provider independently (Claude, OpenAI, Pi, Hermes)

The session tree is what makes cross-harness delegation feel like one conversation, even though five different LLM sessions across four harnesses are involved.

---

## Why this config works across harnesses

Three design choices make this multi-agent architecture work with four different harnesses:

1. **`os_env` tools are provided by the framework, not the harness.** When any config declares `os_env: caller_process`, the Omnigent runner registers filesystem tools (`sys_os_shell`, `sys_os_read`, `sys_os_write`, `sys_os_edit`) regardless of which harness is active. Each harness translates these into its native tool format — but the agent author never sees the difference. All four sub-agents use the same `os_env` block.

2. **Guardrails evaluate in the runner, not in the harness.** The `cost_guard` and `tool_call_limit` policies run in the Omnigent PolicyEngine, which sits between the runner and the harness. The harness never sees the policies — it just receives ALLOW/DENY/ASK verdicts. This is why the same guardrails fire identically whether the sub-agent runs on Claude SDK, Codex, Pi, or Hermes.

3. **Each prompt describes capabilities, not tool names.** Instead of referencing `sys_os_shell` or `Bash`, every prompt says "use shell tools (find, grep, wc, cat, head)." Each harness maps these capability descriptions to its own tool implementations. A prompt that names specific tools would break on harnesses that use different tool names.

This is what harness portability means at scale: not just one agent swapping harnesses, but an entire multi-agent architecture where each participant uses a different harness — and the config, prompts, and policies work unchanged across all of them.
