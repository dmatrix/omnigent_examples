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

> **⚠️ Out of date with the configs.** This section documents the state in which
> **no** agent declared `os_env`. Two now do: `blog_writer` and `editor` both
> carry `os_env: {type: caller_process, cwd: ., sandbox: {type: none}}`, so both
> are granted `sys_os_read` / `sys_os_write` / `sys_os_edit` / `sys_os_shell`,
> and `blog_writer`'s Codex sandbox is back to `danger-full-access`. The
> supervisor and `social_writer` still declare none.
>
> Everything below is accurate **for the supervisor and `social_writer`**, and
> accurate as history for the other two. The claims that `no_self_modification`
> is inert and that the Codex sandbox is narrowed do not currently hold for
> `blog_writer` or `editor`. Resolve by removing the two blocks or rewriting
> this section around the narrower claim.

**Originally absent from all four configs, on purpose.** Every config used to
carry this block:

```yaml
# what all four configs used to declare -- now none of them do
os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none
```

It was removed because a real run of this example used `sys_os_edit` to rewrite
`agents/blog_writer/config.yaml` — switching it to `harness: codex-native` with
`yolo: true` — after a machine-level sandbox failure launching Codex. It turned
a sandbox off to clear an obstacle, in an example about human approval for
irreversible actions.

`os_env` *is* the capability. The loader registers `sys_os_read` /
`sys_os_write` / `sys_os_edit` / `sys_os_shell` for an agent only when the spec
declares the block, and skips registration entirely when it does not
(`ToolManager._register_os_env_tools`). On `claude-sdk` the native `Write` /
`Edit` / `Bash` tools are never exposed either — the harness's base set is
`Skill` + `ToolSearch`, with `Bash` added only for a *sandboxed* CLI. So the
supervisor, `editor` and `social_writer` now hold no file tool of any kind.
`tests/test_self_edit_guard.py` asserts that against a real `ToolManager`, not
just against the YAML.

It was not needed. `cwd: .` is not what lets the six tools resolve
`backlog.md` and `artifacts/` — they run as server-side subprocesses and
resolve paths from `os.getcwd()`, the workspace root, independent of any
agent's `os_env`. Removing the block costs the example nothing; verified by
running all five.

#### `blog_writer` is a partial exception, and the honest version matters

Removing `os_env` from `blog_writer` takes away its `sys_os_*` tools like
everywhere else, but it does **not** leave it unable to write. It runs
`harness: codex`, and Codex's own `apply_patch` is not an Omnigent tool:

| | Codex sandbox it gets |
|---|---|
| `os_env` with `sandbox: {type: none}` (the old config) | `danger-full-access` — the entire filesystem |
| no `os_env` (now) | `read-only`, **upgraded to `workspace-write`** |

The upgrade is unconditional in practice: `codex_executor.py:5494-5496` turns
`read-only` into `workspace-write` whenever the agent is passed any AP-bridged
tool, and framework builtins guarantee that. The bundle lives in the workspace,
so `agents/blog_writer/config.yaml` stays writable. And no policy can intervene
— native Codex calls arrive marked `internally_executed`, already executed
(`_executor_adapter.py:1311-1313`).

```yaml
# agents/blog_writer/config.yaml — narrows it, does not close it
executor:
  config:
    harness: codex
    disable_native_tools: true
```

`disable_native_tools: true` sends exactly `features.shell_tool=false` on the
ordinary Codex route (`codex_executor.py:4035`), which removes the shell tool.
It does not remove `apply_patch`: against codex-cli 0.149.1 that flag flips
`shell_tool` alone, and no feature flag disables `apply_patch`. The full strip
that nulls `apply_patch_tool_type` runs only on the brokered-gateway route,
which needs a signer, `broker_gateway: true` and an active sandbox.

So the supervisor still has a one-hop route to a bundle write, via a sub-agent.
What this change bought is a smaller blast radius and one less tool, not a
closure. Closing it means moving `blog_writer` off `harness: codex` — which
deletes the cross-harness premise of the example — or running the brokered
route. See [README.md](README.md#what-this-does-not-close).

Why not a constrained sandbox? `os_env.sandbox` accepts a `write_paths`
allowlist, a kernel-level boundary that would cover shell too. Both
`type: darwin_seatbelt` and `type: auto` fail launch preparation on the
development machine (`Cannot validate trusted runtime: mutable hard-link
alias…`), and `windows_jobobject` provides no filesystem isolation and is
rejected for sandboxed `claude-sdk` launches. A config that will not start is
how you get the next `yolo: true`. If your host supports a sandbox, prefer it.

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

`read_backlog(include_artifacts=True)` is the read-only dashboard mode. It uses
the same parser as normal backlog reads, then inventories `artifacts/` for every
slug. Its JSON snapshot has `entries` (file-order `slug`, `title`, `status`, and
artifact booleans/lists), `published_article_count`, optional
`article_ceiling`, and `utc_date`. The publication total is all-time durable
disk state, not the session-scoped R3 ceiling state, so it is never rendered as
a fraction of that ceiling.

`save_artifact(kind="dashboard", slug="dashboard", content=...)` writes the
current Markdown snapshot to `artifacts/dashboard.md`. It overwrites just like
outline, draft, and social artifacts; the existing return contract remains
exactly `{path, bytes, kind}`, and `bytes` remains the post-call file size.

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
      max_articles_per_cycle: 5
```

`path` is a dotted import path to a **factory function** that returns the policy
callable; `arguments` are bound to that factory's signature. The policy keeps
state in `session_state` across turns and returns `state_updates`.

Four rules. R1, R3 and R2 are evaluated in that order on the two guarded
shipping tools; R4 stands alone on `update_backlog`:

| Rule | Verdict | Condition |
|---|---|---|
| R1 | **DENY** | `post_social` for a slug with no prior successful `update_backlog(status="APPROVED")` |
| R3 | **DENY** | this slug is **not already** among the articles shipped this cycle **and** the cycle's article ceiling (`max_articles_per_cycle`) is already reached |
| R2 | **ASK** | any other `publish_content` or `post_social`, reason naming the slug and artifact |
| R4 | **DENY** | `update_backlog(status="PUBLISHED")` for a slug this session did not watch *fully* ship — `publish_content` succeeded **and** every staged social variant was posted |

R4 is the odd one out and deliberately so: it is the only rule that looks at a
tool outside the guarded pair, so it lives in its own early branch rather than
threaded through the R1 → R3 → R2 chain. It cannot affect those three, and it
does not gate `update_backlog` for `READY`, `DRAFTED`, `EDITED` or `APPROVED`.

R3 counts **articles** — distinct backlog slugs — not guarded calls. One article
ships in three guarded calls (`publish_content` plus a `post_social` per
channel), so a call-based count would stop the second article mid-flight at
`max_articles_per_cycle: 5`. The two-part condition is what gives the rule its
semantics: **finish what you started, but do not start a new one.** A slug the
cycle has already counted is never refused by R3, so no article is left
published with its social copy stranded; a new slug is refused on its first
call.

The argument is named `max_articles_per_cycle` for exactly that reason — it
counts articles, so it says so. Note what it bounds: the articles a cycle may
**start**. Because an already-counted slug is exempt, the same article can be
re-shipped inside the cycle without R3 noticing; R2 is what holds there, asking
on every shipping call. Do not read `5` as a cap on outbound actions.

Order matters. R1 before R3 means an unapproved post at the ceiling reports the
*sequencing* violation, which is the more useful message. R3 before R2 is what
makes the ceiling a real stop rather than a differently-worded ASK — an earlier
draft of this policy had R2 first, which silently made R3 unreachable.

`read_backlog` (including dashboard mode) and `save_artifact` are never gated
on any path, and neither is
`update_backlog` for any status that describes work in progress. The terminal
`PUBLISHED` status is the one checked call — R4 above — because that one is not
a description of work but a claim the work finished, and it is the column a
status dashboard reads. R4 answers `DENY` or `ALLOW`, never `ASK`, so the
producing tier stays unattended end to end.

### Why R4 reads a different record from R3

The policy keeps **two** shipping records under separate scopes, and merging
them would be a bug:

| key | scope | whose record |
|---|---|---|
| `_publish_gate_cycle_slugs` | one UTC day | R3's ceiling — resetting at midnight is the point |
| `_publish_gate_ship_progress` | the session, per slug | R4's completeness check |

If R4 read the ceiling's record it would DENY a legitimate `PUBLISHED` write
whenever the publish and the status write straddled UTC midnight, and the first
call of a new cycle would reset that record out from under a perfectly good
article. R4 therefore uses the session scope, which matches R1's: in the normal
flow steps 12 and 13 happen moments apart in one session.

The cost of that choice, stated plainly: the daily schedule uses
`session_mode: new`, so a `PUBLISHED` write in a *later* session than the
publish is refused. And R4 is not a security boundary: it gates a tool call, so it says
nothing about a supervisor that rewrites `backlog.md` directly instead of
calling `update_backlog`. That route is now shut by the supervisor holding no
file-write tool (see [OS Environment](#os-environment)) — a different mechanism,
not a stronger R4. R4 raises the floor on careless optimism.

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

### Builtin: `no_self_modification`

```yaml
no_self_modification:
  type: function
  function:
    path: omnigent.policies.builtins.cel.cel_policy
    arguments:
      expression: >-
        event.type == "tool_call" && event.data.name in [
        "sys_os_write", "sys_os_edit", "sys_os_shell",
        "Write", "Edit", "MultiEdit", "NotebookEdit", "Bash",
        "write", "edit", "bash", "shell", "apply_patch"]
        ? {"result": "DENY"} : null
      reason: >-
        The supervisor may not write files or run shell. ...
```

A backstop for the absent [`os_env`](#os-environment), not the mechanism. It
DENIES the listed tools and abstains on everything else — so all five staging
tools, sub-agent dispatch and every read stay untouched.

**It is inert for the `sys_os_*` family, and powerless over the rest.** Those
two halves need separating, because the tool list is wider than the protection:

- `sys_os_write` / `sys_os_edit` / `sys_os_shell` — the supervisor and
  `social_writer` declare no `os_env`, so neither is granted these and the
  policy has nothing to act on for them. `blog_writer` and `editor` *do* declare
  `os_env`, so for those two the DENY is live rather than inert. `os_env` is the
  boilerplate CLAUDE.md documents for filesystem access, so re-adding the block
  is a plausible accident — which is exactly what makes this policy worth
  keeping, and what makes that accident non-silent. For these names the gate is
  genuine (see below).
- `shell` / `apply_patch` — `blog_writer` **does** hold Codex's native
  `apply_patch`. Naming it here cannot stop it; see below. It is listed so a
  reader does not have to infer the omission.

**Why CEL and not `read_only_os`.** The first version of this used
`omnigent.policies.builtins.orchestration.read_only_os`, which matches
write/edit names only and ALLOWS `sys_os_shell` (`orchestration.py:671`). A
shell redirect rewrites YAML just as well as an edit, and `read_only_os` takes
no parameter to extend its tool set. CEL takes an explicit list, so the shell
tools are in it. CEL is also a registry builtin, so this does not change the
example's remote-server story.

**Where the gate is real, and where it is not.** `sys_os_*` calls route
through Omnigent's dispatch bridge and are evaluated BEFORE they run, so a
`DENY` there prevents the write. Codex's native `shell` / `apply_patch` on
`agents/blog_writer` are a different matter: they arrive marked
`internally_executed` and have already executed
(`_executor_adapter.py:1311-1313`), so naming them in the expression documents
intent but cannot stop them. Capability removal is the only lever there, and it
is partial. See [OS Environment](#os-environment).

**`DENY`, not `ASK`.** The self-edit it exists to prevent happened in a
headless run, and the model's own written justification for disabling the
sandbox was that headless sub-agents cannot answer approval prompts. An `ASK`
nobody can answer is the pressure that produced the edit.

Placement: `read_backlog` finds `article_ceiling` by descending
`guardrails` → `policies` → `publish_gate` → `function` → `arguments` by
indentation, so a sibling policy added before or after `publish_gate` no longer
affects it. That was not true when this policy was added — the parser scanned
the file as an ordered line sequence — and `test_read_dashboard.py` now pins
the order-insensitivity directly.

### Cost governance

```yaml
user_daily_cost_budget:
  type: function
  function:
    path: omnigent.policies.builtins.cost.user_daily_cost_budget
    arguments:
      max_cost_usd: 25.00
      ask_thresholds_usd: [5.50, 10.50, 15.50, 20.50]
```

Per-user, per-UTC-day, so it survives `--no-session`.

### Why two shipping layers don't mean two prompts

The engine evaluates **every** policy, short-circuits only on `DENY`, and
accumulates `ASK` reasons across policies into **one** pending approval. So a
normal publish produces a single request carrying both reason lines — the
slug-specific one from `publish_gate` and the blanket one from `guarded_tools`.

---

## Prompt

The supervisor `prompt:` is a `|` literal block and carries six things worth
copying into your own supervisor:

1. **A hard delegation ban** — "never write, draft, edit or rewrite a blog or a
   social post yourself."
2. **A named roster with the harness in parentheses** so cross-harness
   delegation is visible in the transcript.
3. **A numbered 13-step workflow**, with step 7 forbidding progress past a
   `REVISE` verdict and step 13 writing the terminal `PUBLISHED` status only
   after a human approval *and* a successful publish.
4. **A visibility rule** — name the agent and the harness, "do not state the
   model name."
5. **A disk-derived dashboard rule** — render only from a fresh
   `read_backlog(include_artifacts=True)` call at meaningful state transitions,
   persist that table,
   and open it once per session with `ui_open_file`.
6. **A coordinator constraint** — report what sub-agents produced; do not add
   your own critique. The editor's verdict is the verdict.

The prompt also states two UX limits up front: no agent-configurable Start
button exists, so a run begins with chat; and a whole-backlog run is not
unattended because the $5.50 daily-cost ASK (then every $5) and five-articles-per-UTC-day
ceiling can stop it. Its alternative stages steps 1–11 for all entries and
publishes them one at a time.

Step 12 is the gate, and the prompt says the quiet part out loud: *never treat
your own reasoning as the approval.* Step 13 is the honesty clause on the other
side of it: `PUBLISHED` is a record of what shipped, so a denied, parked or
failed publish leaves the entry at `APPROVED`.

---

## Sub-agents

One file per `agents/<name>/` directory, nothing else in it. None declares
[`os_env`](#os-environment).

### `agents/blog_writer/config.yaml`

```yaml
executor:
  model: databricks-gpt-5-4
  config:
    harness: codex

tools:
  builtins: [web_search]
```

The only **sub-agent** with an explicit `tools:` block, and the only agent
configured with `web_search`. (The supervisor also has a `tools:` block, but it
contains `agents:` rather than builtins.) Its prompt restricts it to the URLs in
the backlog entry's `sources:` list, and requires it to say so in the draft if a
source is unreachable rather than substituting another.

### `agents/editor/config.yaml`

Claude on `claude-sdk`. Returns `PASS` / `REVISE` / `REJECT`. No explicit
`tools:` block — the supervisor sends it the draft and the backlog entry
directly. Its prompt forbids it from writing files, and with no
[`os_env`](#os-environment) it also cannot — closing *this* delegation route
around the supervisor's own lack of filesystem access. It does not close them
all: `blog_writer` still holds Codex's native `apply_patch`
([above](#blog_writer-is-a-partial-exception-and-the-honest-version-matters)).
Framework-owned tool groups are still enabled by default.

### `agents/social_writer/config.yaml`

Claude on `claude-sdk`. Derives the X thread and LinkedIn post. The ordering
constraint is enforced at two different strengths, and the difference matters:
its **prompt** requires a PASSed draft, while **`publish_gate` R1**
structurally requires a prior successful `update_backlog(status="APPROVED")`.
R1 cannot see an editor invocation or a verdict — it checks the recorded state
transition, which the supervisor only performs after a `PASS`.

### Sub-agent guardrails

```yaml
cost_budget:          max_cost_usd: 25.00, ask_thresholds_usd: [6.25, 11.25, 16.25, 21.25]
                      (social_writer steps from 7.50; every value must be < max_cost_usd)
max_tool_calls_per_session:  limit 250
```

The per-invocation cap catches a runaway sub-agent; the tool-call limit bounds
runaway tool use. The supervisor has no tool-call limit.

---

## Not in this config

- **No cron / schedule / rrule key.** Agent YAML has no declarative recurring
  trigger. The supervisor creates the schedule at runtime via
  `sys_scheduled_task_create`, which is itself approval-gated.
- **No `tool_groups:`** — scheduled-task tools are enabled by default; disabling
  them would break continuous operation.
- **No `guardrails.labels:`** — this example gates on *state*, not on taint
  labels. See [secure_code_assistant](../secure_code_assistant/) for labels.
- **No `tools:` block on the supervisor beyond `agents:`** — the six factory
  tools are auto-discovered.
- **`skills:` declared on `blog_writer`** — it lists `blog-style` explicitly.
- **No `os_env` on the supervisor or `social_writer`** — and that is the point,
  not an omission. `blog_writer` and `editor` currently do declare one; see
  [OS Environment](#os-environment).

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
(os_env on blog_writer+editor    — see OS Environment)
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
5. On approval, the tool runs; `publish_gate` records the slug against the
   current cycle on `tool_result`. The first guarded call for a slug adds it to
   the cycle's shipped set; that article's later calls find it already there and
   add nothing, which is what makes the set size an article count.
6. Once `publish_content` and every `post_social` for the slug have succeeded,
   the supervisor's step 13 sets the entry to `PUBLISHED`. R4 checks that claim
   against `_publish_gate_ship_progress` and **ALLOW**s it, because the session
   watched the whole thing ship. The write does **not** disturb R1's
   approved-slug record — `PUBLISHED` neither removes an `APPROVED` entry nor
   creates one.

### Flow 3: the fourth article in one cycle

1. Three distinct slugs have already shipped today.
2. The supervisor calls `publish_content(slug="d")` for a fourth slug.
3. `publish_gate` R3 sees that `d` is not in the cycle's shipped set and the set
   is full, and fires before R2. **DENY** — the ceiling holds until the next
   cycle.

Compare the call that is *not* refused: a `post_social` for one of those three
slugs is at the same ceiling, but its slug is already in the set, so R3 skips it
and R2 **ASK**s as usual. The in-flight article finishes; the fourth never
starts.

### Flow 4: a `PUBLISHED` claim for a half-shipped article

1. `publish_content(slug="e")` succeeds; the staged `e-x.md` and
   `e-linkedin.md` posts are never posted.
2. The supervisor calls `update_backlog(slug="e", status="PUBLISHED")`.
3. R4 reads `_publish_gate_ship_progress["e"]`: `published` is true, but both
   staged channels are outstanding.
4. **DENY**, naming the outstanding posts. The entry stays `APPROVED`.

Had the cycle staged only a LinkedIn variant and posted it, the same write would
be **ALLOW**ed — completeness is measured against what was staged, not against a
fixed list of channels.

### Why state is read on `tool_result`, not `tool_call`

The engine withholds `state_updates` when a policy returns `ASK`, so a gated
call can never record itself from `tool_call`. The policy therefore gates on
`tool_call` and does its bookkeeping on `tool_result`. Success is read
fail-closed: a result dict with no `error` counts, anything else does not.

Three tools feed that bookkeeping, and one of them is a tool the policy never
gates: `save_artifact`. Watching its results is how R4 learns which social
variants a cycle staged, and therefore which posts an article owes before it can
call itself published. Observing a tool is not gating it.

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
