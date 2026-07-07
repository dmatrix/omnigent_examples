# Omnigent Built-in Policies Reference

All available policies under `omnigent.policies.builtins.*`. Each policy is declared in a `config.yaml` guardrails block:

```yaml
guardrails:
  policies:
    my_policy:
      type: function
      function:
        path: omnigent.policies.builtins.<module>.<policy>
        arguments:
          key: value
```

Source: [`omnigent/policies/builtins/`](https://github.com/dmatrix/omnigent/tree/main/omnigent/policies/builtins)

---

## Cost

| Policy | Arguments | Description |
|---|---|---|
| `cost.cost_budget` | `max_cost_usd: float`, `ask_thresholds_usd: list[float]`, `expensive_models: list[str]` | Gates a session on cumulative LLM spend (USD). DENYs at hard limit, ASKs at soft thresholds. |
| `cost.user_daily_cost_budget` | `max_cost_usd: float` **(required)**, `ask_thresholds_usd: list[float]`, `expensive_models: list[str]` | Per-user per-UTC-day spend cap across all their sessions. Same gating logic as `cost_budget` but scoped to user + day. |
| `cost.subagent_cost_budget` | `max_cost_usd: float`, `ask_thresholds_usd: list[float]`, `expensive_models: list[str]` | Scoped to a sub-agent's own subtree spend only. Identical logic to `cost_budget` but tracks the child conversation subtree. |

---

## Safety

| Policy | Arguments | Description |
|---|---|---|
| `safety.max_tool_calls_per_session` | `limit: int = 100` | Denies tool calls once the session exceeds a maximum count across all turns. Uses session state to persist the counter. |
| `safety.ask_on_os_tools` | *(none)* | Asks for user approval before any file or shell tool call. Covers Omnigent `sys_os_*`, Claude Code native tools (Bash/Read/Write/Edit/Glob/Grep), Cursor Shell, Pi, Hermes, Goose, and opencode tools. |
| `safety.block_skills` | `blocked: list[str]` | Denies skill loading for specific skill names. Intercepts `load_skill`/`read_skill_file` and native Skill tool calls. |
| `safety.enforce_sandbox` | `sandbox_type: str = "linux_bwrap"`, `allow_network: bool = True`, `write_paths: list[str]`, `read_paths: list[str]`, `env_passthrough: list[str]` | Forces a sandbox configuration on every agent start. Intercepts the synthetic `__agent_start` tool call and overrides sandbox config. |
| `safety.deny_pii_in_llm_request` | `pii_types: list[str]` (ssn, credit_card, email, phone), `action: str = "DENY"` (DENY or ASK) | Scans system prompt preview and user messages for PII patterns. Returns configured action on match. |

---

## Google Workspace

| Policy | Arguments | Description |
|---|---|---|
| `google.gdrive_policy` | `read_all: bool = True`, `read_files: list[str]`, `allow_create: bool = False`, `write_files: list[str]`, `comment_files: list[str]`, `confidential_files: list[str]`, `write_down_action: str = "DENY"`, `tool_prefixes: list[str]`, `deny_reason: str` | Controls Google Drive/Docs/Sheets/Slides access. Restricts reads to allowlist, writes to created files + allowlist. Optionally enforces Bell-LaPadula "no write-down" via confidential-file compartment. |
| `google.gmail_policy` | `allow_read: bool = True`, `allow_send: bool = False`, `allow_drafts: bool = True`, `allow_modify: bool = False`, `tool_prefixes: list[str]`, `deny_reason: str` | Controls Gmail access. Defaults allow read + drafts but block send and message modification. Draft edits restricted to drafts created in the current session. |
| `google.gcalendar_policy` | `allow_read: bool = True`, `allow_create_events: bool = False`, `allow_modify_events: bool = False`, `tool_prefixes: list[str]`, `deny_reason: str` | Controls Google Calendar access. Defaults to read-only. Blocks creating, updating, and deleting events. |

---

## GitHub

| Policy | Arguments | Description |
|---|---|---|
| `github.github_policy` | `read_all: bool = True`, `read_repos: list[str]`, `write_repos: list[str]`, `write_branches: list[str]`, `mcp_tool_prefixes: list[str]`, `shell_tools: list[str]`, `deny_reason: str` | Controls GitHub access across MCP tools (official per-op server, HTTP-proxy wrapper) and `git`/`gh` shell commands. Restricts reads to `read_repos` and writes to `write_repos` + optional `write_branches`. |

---

## Working Directory

| Policy | Arguments | Description |
|---|---|---|
| `working_dir.block_working_dir_changes` | `block_cd: bool = True`, `block_worktree: bool = True`, `allowed_dirs: list[str]`, `action: str = "deny"`, `shell_tools: list[str]` | Gates shell commands that switch working directory (`cd`/`chdir`/`pushd`/`popd`, `git -C`) or create git worktrees (`git worktree add/move/remove`). Optionally allows `cd` into specific directories. |

---

## Risk Score

| Policy | Arguments | Description |
|---|---|---|
| `risk_score.risk_score_policy` | `threshold: int = 50`, `tool_points: dict[str, int]`, `sensitive_labels: dict[str, int]`, `guarded_tools: list[str]`, `escalate_action: str = "ASK"`, `initial_scores_by_actor: dict[str, int]`, `state_key: str = "risk_score"`, `label_keys: list[str]`, `reason: str` | Accrues a session risk score from tool calls and sensitive result labels. Escalates guarded tools to ASK/DENY once the score crosses the threshold. |

---

## Routing

> Requires server-side `llm:` config block. Fails open when absent.

| Policy | Arguments | Description |
|---|---|---|
| `routing.deny_trivial_to_expensive_model` | `expensive_models: list[str]` **(required)**, `classification_prompt: str` | Classifies user message as TRIVIAL or COMPLEX using server-level LLM. Denies trivial tasks from using expensive models. |
| `routing.intent_gate` | *(none)* | Records the user's first message as authoritative session intent. Gates every subsequent tool call against that intent. Denies OFF_TASK calls. |

---

## Context

> Requires server-side `llm:` config block. Fails open when absent.

| Policy | Arguments | Description |
|---|---|---|
| `context.detect_task_switch` | `min_turns: int = 1`, `history_window: int = 10`, `action: str = "ASK"`, `classification_prompt: str` | Detects when user switches to an unrelated task using server-level LLM. Maintains rolling window of recent messages and asks/denies task switches with recommendation to start a fresh session. |

---

## Generic / Programmable

| Policy | Arguments | Description |
|---|---|---|
| `cel.cel_policy` | `expression: str` **(required)**, `reason: str = "Denied by policy."` | Evaluates a CEL (Common Expression Language) expression against the full `PolicyEvent`. Expression receives the event as `event` and must return a map with `result` (ALLOW/DENY/ASK) and optional `reason`. |
| `prompt.prompt_policy` | `prompt: str` **(required)**, `reason: str` | LLM-backed classifier policy. Sends event payload + author instructions to server-side LLM, parses JSON verdict. Requires server `llm:` config block. |

---

## Summary

**20 built-in policies** across **10 modules**:

| Module | Count | Policies |
|---|---|---|
| `cost` | 3 | `cost_budget`, `user_daily_cost_budget`, `subagent_cost_budget` |
| `safety` | 5 | `max_tool_calls_per_session`, `ask_on_os_tools`, `block_skills`, `enforce_sandbox`, `deny_pii_in_llm_request` |
| `google` | 3 | `gdrive_policy`, `gmail_policy`, `gcalendar_policy` |
| `github` | 1 | `github_policy` |
| `working_dir` | 1 | `block_working_dir_changes` |
| `risk_score` | 1 | `risk_score_policy` |
| `routing` | 2 | `deny_trivial_to_expensive_model`, `intent_gate` |
| `context` | 1 | `detect_task_switch` |
| `cel` | 1 | `cel_policy` |
| `prompt` | 1 | `prompt_policy` |

### Notes

- **Factory vs callable**: Most policies are factories (take arguments to produce a policy callable). Only `ask_on_os_tools` and `intent_gate` are direct callables with no parameters.
- **Async policies**: `deny_trivial_to_expensive_model`, `intent_gate`, `prompt_policy`, and `detect_task_switch` are async.
- **LLM-dependent**: Routing, context, and prompt policies require a server-side `llm:` config block and fail open when absent.
- **MCP-agnostic**: Google, GitHub, and risk-score policies auto-match tool names by stripping server prefixes (default `mcp__*__` or `google__`/`github__`), so they work with any MCP server variant.

### Used in this repo

| Example | Policies |
|---|---|
| [Secure Code Assistant](../examples/secure_code_assistant/) | `cost.cost_budget` + taint/deny (information flow) |
| [Telco Customer Agent](../examples/telco_customer_agent/) | Taint/deny (PII/financial labels) + `cost.cost_budget` + `safety.deny_pii_in_llm_request` + `risk_score.risk_score_policy` + custom `bulk_access_guard` |
| [Cross-Harness Coding](../examples/cross_harness_coding/) | `cost.cost_budget` (per-invocation) + `cost.user_daily_cost_budget` (daily) |
| [Harness Portability](../examples/harness_portability/) | `cost.cost_budget` (supervisor + per-sub-agent) + `safety.max_tool_calls_per_session` (per-sub-agent) |
