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
      max_articles_per_cycle: 3
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
`max_articles_per_cycle: 3`. The two-part condition is what gives the rule its
semantics: **finish what you started, but do not start a new one.** A slug the
cycle has already counted is never refused by R3, so no article is left
published with its social copy stranded; a new slug is refused on its first
call.

The argument is named `max_articles_per_cycle` for exactly that reason — it
counts articles, so it says so. Note what it bounds: the articles a cycle may
**start**. Because an already-counted slug is exempt, the same article can be
re-shipped inside the cycle without R3 noticing; R2 is what holds there, asking
on every shipping call. Do not read `3` as a cap on outbound actions.

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
publish is refused. And R4 is not a security boundary — the supervisor has
`os_env: caller_process` with `sandbox: none`, so it could rewrite
`backlog.md` directly. R4 raises the floor on careless optimism.

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
unattended because the $0.50 daily-cost ASK and three-articles-per-UTC-day
ceiling can stop it. Its alternative stages steps 1–11 for all entries and
publishes them one at a time.

Step 12 is the gate, and the prompt says the quiet part out loud: *never treat
your own reasoning as the approval.* Step 13 is the honesty clause on the other
side of it: `PUBLISHED` is a record of what shipped, so a denied, parked or
failed publish leaves the entry at `APPROVED`.

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

The only **sub-agent** with an explicit `tools:` block, and the only agent
configured with `web_search`. (The supervisor also has a `tools:` block, but it
contains `agents:` rather than builtins.) Its prompt restricts it to the URLs in
the backlog entry's `sources:` list, and requires it to say so in the draft if a
source is unreachable rather than substituting another.

### `agents/editor/config.yaml`

Claude on `claude-sdk`. Returns `PASS` / `REVISE` / `REJECT`. No explicit
`tools:` block — the supervisor sends it the draft and the backlog entry
directly, and its prompt forbids it from writing files. Framework-owned tool
groups are still enabled by default.

### `agents/social_writer/config.yaml`

Claude on `claude-sdk`. Derives the X thread and LinkedIn post. The ordering
constraint is enforced at two different strengths, and the difference matters:
its **prompt** requires a PASSed draft, while **`publish_gate` R1**
structurally requires a prior successful `update_backlog(status="APPROVED")`.
R1 cannot see an editor invocation or a verdict — it checks the recorded state
transition, which the supervisor only performs after a `PASS`.

### Sub-agent guardrails

```yaml
cost_budget:          max_cost_usd: 1.0, ask_thresholds_usd: [0.25]
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
