# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Attribute reference for all five config files (supervisor + four sub-agents).

---

## `executor:` — The supervisor's brain

| Attribute | Value | Role |
|---|---|---|
| `model` | `claude-sonnet-4-6` | Direct Anthropic API. Override with `--model`. |
| `config.harness` | `claude-sdk` | Override with `--harness`. CLI flags only affect the supervisor — sub-agents keep their hardcoded values. |

---

## `prompt:` — The supervisor's system prompt

A `|` literal block defining:

1. **Role** — "You are a Code Project Health Inspector supervisor"
2. **Interaction** — accepts a GitHub URL inline or asks for one
3. **MLflow tracing** — automatic via `OMNIGENT_TELEMETRY_ENABLED` + `OTEL_EXPORTER_OTLP_ENDPOINT` env vars
4. **Delegation** — MUST delegate all inspection to four sub-agents; never inspects code itself
5. **Agent roster** — `structure_inspector` (Claude SDK), `test_inspector` (Codex), `dependency_inspector` (Pi), `security_inspector` (Hermes)
6. **Report** — collects findings, assigns letter grades (A–F), writes `health_report.md`

Prompts describe capabilities ("use shell tools: find, grep, wc") not tool names (`sys_os_shell`). This is what makes the same prompt work across all four harnesses.

---

## `os_env:` — Environment access

All five agents declare `type: caller_process`, `cwd: .`, `sandbox: none`. They share the same filesystem — the supervisor clones the repo and sub-agents read from the cloned path.

---

## `tools:` — Sub-agent references

```yaml
tools:
  agents:
    - structure_inspector
    - test_inspector
    - dependency_inspector
    - security_inspector
```

The framework discovers `agents/<name>/config.yaml` for each entry, registers them as callable tools, and spawns child sessions on invocation.

---

## Sub-agent configs

Each sub-agent is a self-contained agent definition in its own directory under `agents/`. They get their own model, harness, prompt, and guardrails — the only thing shared with the supervisor is the session tree and filesystem.

| Agent | Harness | Model | Inspects | Guardrails |
|---|---|---|---|---|
| `structure_inspector` | `claude-sdk` | `claude-sonnet-4-6` | README, LICENSE, .gitignore, directory organization, contributor docs | `cost_guard` ($5, ASK $1) + `tool_call_limit` (250) |
| `test_inspector` | `codex` | `gpt-5.4` | Test files, test-to-source ratio, CI config, test framework, coverage | `cost_guard` ($5, ASK $1) + `tool_call_limit` (250) |
| `dependency_inspector` | `pi` | `claude-sonnet-4-6` | Dependency manifests, pinning, lock files, dev vs prod separation | `cost_guard` ($5, ASK $1) + `tool_call_limit` (250) |
| `security_inspector` | `hermes` | `claude-sonnet-4-6` | Large files, hardcoded secrets, dangerous functions, code hygiene | `cost_guard` ($5, ASK $1) + `tool_call_limit` (250) |

To swap a sub-agent's harness, change the `executor:` block in its `config.yaml` — see [Harness Swapping](README.md#harness-swapping) in the main README.

---

## `guardrails:` — Layered cost and safety governance

### Supervisor (session-wide)

| Policy | Limit |
|---|---|
| `cost_guard` | ASK at $1.00, DENY at $5.00 |

No tool call limit on the supervisor — it only makes a handful of calls (clone + dispatch + write report).

### Sub-agents (per-invocation, all four identical)

| Policy | Limit |
|---|---|
| `cost_guard` | ASK at $1.00, DENY at $5.00 |
| `tool_call_limit` | 250 tool calls max |

The cost guard works in two phases: **ASK** at the soft threshold (approve or deny), **DENY** at the hard limit (switch models or start fresh). The tool call limit prevents runaway inspection loops. All policies are harness-agnostic — they evaluate in the Omnigent runner, not in the LLM harness.

| Scenario | What happens | Recovery |
|---|---|---|
| ASK threshold ($1.00) | Agent pauses for approval | Approve or deny |
| Hard limit ($5.00) | Further tool calls denied | `/model` to switch, or fresh session |
| Tool call limit (250) | Sub-agent tool calls denied | Fresh session, or raise `limit` in config |

---

## What's not in this config

No `tools/python/`, no labels, no taint/deny policies, no `web_search`. All capabilities come from `os_env` (shell access). See [secure_code_assistant](../secure_code_assistant/) and [telco_customer_agent](../telco_customer_agent/) for information flow control patterns.

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

---

## Session tree

```
Session: harness_portability (root)
+-- supervisor turn 1 (clone repo, dispatch)
|   +-- structure_inspector (child session, claude-sdk)
|   +-- test_inspector (child session, codex)
|   +-- dependency_inspector (child session, pi)
|   +-- security_inspector (child session, hermes)
+-- supervisor turn 2 (assemble report, write health_report.md)
```

All agents share one session ID, filesystem, and policy state. Each sub-agent has its own context window and executor — the session tree is what makes cross-harness delegation feel like one conversation.

---

## Why this works across harnesses

1. **`os_env` tools are framework-provided.** Declaring `os_env: caller_process` registers filesystem tools (`sys_os_shell`, etc.) regardless of harness. Each harness translates to its native format.
2. **Guardrails evaluate in the runner.** The harness never sees policies — it receives ALLOW/DENY/ASK verdicts from the PolicyEngine.
3. **Prompts describe capabilities, not tool names.** "Use shell tools (find, grep, wc)" works across all harnesses; naming `sys_os_shell` would break on harnesses that use different names.
