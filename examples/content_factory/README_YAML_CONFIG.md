# config.yaml Structure Reference <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

Annotated walkthrough of `examples/content_factory/config.yaml` and the three
sub-agent configs under `agents/`.

Four configs, eight top-level keys, one policy file. The interesting part is
`guardrails.policies` — everything else is scaffolding.

---

## Supervisor (`config.yaml`)

```yaml
spec_version: 1
name: content_factory
description: >
  Agentic content factory supervisor — ...
```

`name:` must match the directory name. `spec_version:` is always `1`.

### Executor

```yaml
executor:
  type: omnigent
  model: databricks-claude-sonnet-4-6
  config:
    harness: claude-sdk
```

Harness and model live **here**, not at the top level. There is no top-level
`harness:` or `model:` key in any config in this repo.

### OS Environment

```yaml
os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none
```

Identical in all four configs. `caller_process` + `cwd: .` is what lets the
tools resolve `backlog.md` and `artifacts/` relative to the repo root.

### Tools

```yaml
tools:
  agents:
    - blog_writer
    - editor
    - social_writer
```

Bare names only. The framework discovers `agents/<name>/config.yaml` for each
entry, registers them as callable tools, and spawns child sessions on
invocation.

**The five factory tools are not listed here.** They are auto-discovered from
`tools/python/`, and the policies below reference them by name even though they
never appear in a `tools:` block. Same for `skills/blog-style/SKILL.md` — there
is no `skills:` key; the directory is the declaration.

---

## Guardrails: Policies

Three policies on the supervisor. Two guard shipping; one guards spend.

### Custom policy: `publish_gate`

```yaml
publish_gate:
  type: function
  function:
    path: examples.content_factory.policies.publish_gate.publish_gate
    arguments:
      max_publishes_per_cycle: 3
```

`path` is a dotted import path to a **factory function** that returns the policy
callable; `arguments` are bound to that factory's signature. The policy keeps
state in `session_state` across turns and returns `state_updates`.

Three rules, in evaluation order:

| Rule | Verdict | Condition |
|---|---|---|
| R1 | **DENY** | `post_social` for a slug with no prior successful `update_backlog(status="APPROVED")` |
| R3 | **DENY** | the cycle's publish ceiling (`max_publishes_per_cycle`) is already reached |
| R2 | **ASK** | any other `publish_content` or `post_social`, reason naming the slug and artifact |

Order matters. R1 before R3 means an unapproved post at the ceiling reports the
*sequencing* violation, which is the more useful message. R3 before R2 is what
makes the ceiling a real stop rather than a differently-worded ASK — an earlier
draft of this policy had R2 first, which silently made R3 unreachable.

`read_backlog`, `update_backlog` and `save_artifact` are never gated on any
path.

### Builtin: `guarded_tools`

```yaml
guarded_tools:
  type: function
  function:
    path: omnigent.policies.builtins.risk_score.risk_score_policy
    arguments:
      threshold: 0
      guarded_tools: [publish_content, post_social]
      escalate_action: ASK
      reason: |
        Publication requires a human signature — ...
```

Note the shape: **there is no `guarded_tools` builtin policy.** `guarded_tools`
is an *argument* to `risk_score_policy`. The local name on the left is just a
label you choose.

`threshold: 0` with no `tool_points` means the session score always sits at the
threshold, so each named tool escalates on every call. Non-guarded tools score
zero points and abstain, so drafting and staging stay free.

This layer is deliberately redundant with `publish_gate`. It knows nothing about
slugs or state, so it keeps the gate standing if the custom policy is removed,
misconfigured, or evaluating on a path where its state is unavailable.

### Cost governance

```yaml
user_daily_cost_budget:
  type: function
  function:
    path: omnigent.policies.builtins.cost.user_daily_cost_budget
    arguments:
      max_cost_usd: 5.0
      ask_thresholds_usd: [0.50]
```

Per-user, per-UTC-day, so it survives `--no-session`.

### Why two shipping layers don't mean two prompts

The engine evaluates **every** policy, short-circuits only on `DENY`, and
accumulates `ASK` reasons across policies into **one** pending approval. So a
normal publish produces a single request carrying both reason lines — the
slug-specific one from `publish_gate` and the blanket one from `guarded_tools`.

---

## Prompt

The supervisor `prompt:` is a `|` literal block and carries five things worth
copying into your own supervisor:

1. **A hard delegation ban** — "never write, draft, edit or rewrite a blog or a
   social post yourself."
2. **A named roster with the harness in parentheses** so cross-harness
   delegation is visible in the transcript.
3. **A numbered 12-step workflow**, with step 7 forbidding progress past a
   `REVISE` verdict.
4. **A visibility rule** — name the agent and the harness, "do not state the
   model name."
5. **A coordinator constraint** — report what sub-agents produced; do not add
   your own critique. The editor's verdict is the verdict.

Step 12 is the gate, and the prompt says the quiet part out loud: *never treat
your own reasoning as the approval.*

---

## Sub-agents

One file per `agents/<name>/` directory, nothing else in it. 62, 60 and 59 lines
respectively.

### `agents/blog_writer/config.yaml`

```yaml
executor:
  model: databricks-gpt-5-4
  config:
    harness: codex

tools:
  builtins: [web_search]
```

The **only** agent with `tools:`, and the only one with research access. Its
prompt restricts it to the URLs in the backlog entry's `sources:` list, and
requires it to say so in the draft if a source is unreachable rather than
substituting another.

### `agents/editor/config.yaml`

Claude on `claude-sdk`. Returns `PASS` / `REVISE` / `REJECT` against the rubric
in `skills/blog-style/SKILL.md`. No tools — it reads the staged draft through
`os_env`.

### `agents/social_writer/config.yaml`

Claude on `claude-sdk`. Derives the X thread and LinkedIn post. The ordering
constraint (only from a PASSed draft) is enforced twice: editorially by its
prompt, and structurally by `publish_gate` R1.

### Sub-agent guardrails

```yaml
cost_budget:          max_cost_usd: 1.0, ask_thresholds_usd: [0.25]
max_tool_calls_per_session:  limit 250
```

The per-invocation cap catches a runaway sub-agent; the tool-call limit stops a
drafting loop. The supervisor has no tool-call limit.

---

## Not in this config

- **No cron / schedule / rrule key.** Agent YAML has no declarative recurring
  trigger. The supervisor creates the schedule at runtime via
  `sys_scheduled_task_create`, which is itself approval-gated.
- **No `tool_groups:`** — scheduled-task tools are enabled by default; disabling
  them would break continuous operation.
- **No `guardrails.labels:`** — this example gates on *state*, not on taint
  labels. See [secure_code_assistant](../secure_code_assistant/) for labels.
- **No `tools:` block on the supervisor beyond `agents:`** — the five factory
  tools are auto-discovered.
- **No `skills:` key** — `skills/blog-style/` is found by convention.

---

## Nesting summary

```
spec_version
name
description
executor
  type
  model
  config.harness
prompt
os_env
  type
  cwd
  sandbox.type
tools
  agents[]                       supervisor only
  builtins[]                     blog_writer only
guardrails
  policies
    <local name>
      type: function
      function
        path                     dotted import path to a factory
        arguments                bound to the factory signature
```

---

## Policy evaluation flow

### Flow 1: `post_social` before the blog is approved

1. Supervisor calls `post_social(slug="x", channel="linkedin")`.
2. `publish_gate` R1 finds no `APPROVED` record for `x` in `session_state`.
3. **DENY.** Engine short-circuits — `guarded_tools` never needs to weigh in.
4. The supervisor's prompt requires it to report the reason verbatim and stop.

### Flow 2: a normal publish

1. Supervisor calls `publish_content(slug="x")` after an editor `PASS`.
2. `publish_gate` R1 passes (approved), R3 passes (under ceiling), R2 → **ASK**
   with a slug-specific reason.
3. `guarded_tools` → **ASK** with the blanket reason.
4. Engine joins both into **one** pending approval.
5. On approval, the tool runs; `publish_gate` records the publish on
   `tool_result`, incrementing the cycle count.

### Flow 3: the fourth publish in one cycle

1. Three publishes have already succeeded today.
2. `publish_gate` R3 fires before R2. **DENY** — the ceiling holds until the
   next cycle.

### Why state is read on `tool_result`, not `tool_call`

The engine withholds `state_updates` when a policy returns `ASK`, so a gated
call can never record itself from `tool_call`. The policy therefore gates on
`tool_call` and does its bookkeeping on `tool_result`. Success is read
fail-closed: a result dict with no `error` counts, anything else does not.

### The two evaluation paths

Policies run on two paths, and only one carries state:

| Path | `session_state` | `conversation_id` |
|---|---|---|
| server | persisted, authoritative | always set |
| runner-local | absent, flattened to `{}` | `None` |

The runner-local path also discards any `state_updates` a policy returns. A
stateful rule that DENIED on absent state would therefore fire *permanently*
there, making an approved post impossible. `publish_gate` detects that case via
`conversation_id` — documented as `None` only in contexts with no engine — and
defers, leaving the stateful decision to the server. The coarse `guarded_tools`
brake still ASKs locally, so deferring never ships anything silently.

This is the one genuinely subtle thing in the example. If you write your own
stateful policy, handle it.
