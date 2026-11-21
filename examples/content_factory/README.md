# Content Factory with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**An agentic software factory that runs itself. Every cycle it pulls the next feature from a backlog, drafts a blog post, edits it, derives short-form social copy, and stages every artifact — then stops dead at a human approval gate, because nothing ships outward without a signature.**

![Content Factory Architecture](images/content_factory_architecture.svg)

---

## Overview

A **software factory** is a pipeline that produces artifacts continuously and unattended. The hard part isn't the producing — it's knowing which outputs the factory may ship on its own authority and which ones need a human. Get that line wrong in the cautious direction and the factory stalls on every trivial draft. Get it wrong in the other direction and it posts to your company's X account at 3am.

This example draws that line explicitly, and puts it in one place: a **stateful contextual policy**.

On its first fresh run the supervisor **proposes** a daily [recurring schedule](https://www.databricks.com/blog/contextual-policies-omnigent-using-session-state-better-govern-ai-agents) — creating it needs your approval, so the factory does not start running on a timer until you say yes. Each cycle is a four-stage assembly line across **three harnesses**:

| Stage | Agent | Harness | Produces |
|---|---|---|---|
| Draft | `blog_writer` | Codex | a full blog post from one backlog feature |
| Edit | `editor` | Claude | a verdict: PASS, REVISE or REJECT |
| Derive | `social_writer` | Claude | an X thread and a LinkedIn post |
| Coordinate | `content_factory` | Claude | backlog state, staging, the schedule |

The supervisor writes nothing. It owns the backlog state machine and delegates every word of content, so the cross-harness division of labour is visible in the transcript.

### Two tiers of artifact

Everything the factory makes lands in `artifacts/`, and the tier decides whether a human is involved:

```
artifacts/cycles/<date>-cycle.md        ← free     cycle log (one file per UTC day, appended per cycle)
artifacts/outlines/<slug>.md            ← free     the angle
artifacts/drafts/<slug>.md              ← free     the blog post
artifacts/social/<slug>-x.md            ← free     X thread
artifacts/social/<slug>-linkedin.md     ← free     LinkedIn post
artifacts/published/<slug>/…            ← GATED    publish_content
artifacts/dashboard.md                  ← free     current disk-derived dashboard snapshot
(outbound post to X / LinkedIn)         ← GATED    post_social
```

Drafting is cheap and reversible, so it is unattended. Publishing is neither, so it asks. **Within a cycle, steps 1–11 need no human at all — step 12 is the one that does, and step 13 only records what step 12 actually shipped.** (Setting up the schedule in the first place is also approval-gated; see [Continuous Operation](#continuous-operation).)

### Dashboard: native to chat, durable on disk

The supervisor renders a full-width Markdown table at the meaningful state
transitions — cycle start, `DRAFTED`, `APPROVED`, the approval gate, and real
`PUBLISHED` — and writes the same snapshot to `artifacts/dashboard.md`. It
opens that file once per session so the UI can keep a persistent pane beside
the transcript. The table is **read-only and derived from disk**: it shows each
backlog status plus only the outline, draft, social, published, and posting
files that actually exist. It reports articles published to date from durable
published draft files, never as the session-scoped publish-ceiling state. It
never pretends to know a non-durable sub-agent step.

There is deliberately **no Start button**. Example agents have no
agent-configurable button surface, so starting a cycle remains a chat message;
the framework's native Approve/Reject card already supplies the real review
button at the publish gate. It shows articles published to date separately from
the configured article ceiling, and marks the current publish attempt when that
ceiling denies it.

### Five tools

- **`read_backlog`** — pulls the next `READY` feature from `backlog.md`; its
  `include_artifacts=True` mode returns the entire file-order, disk-derived
  dashboard. Free.
- **`update_backlog`** — sets one entry to any valid backlog status (`READY`, `DRAFTED`, `EDITED`, `APPROVED`, `PUBLISHED`). It validates the value, not the transition — the intended progression comes from the supervisor prompt. The supervisor writes `DRAFTED` at step 5, `APPROVED` at step 8 and the terminal `PUBLISHED` at step 13, once publishing has actually succeeded. (`EDITED` is valid but unused.) **Free for every status except `PUBLISHED`,** which `publish_gate` R4 checks against what actually shipped — see [R4](#custom-policy-publish_gate).
- **`save_artifact`** — stages an outline, draft, social post or cycle log. Free.
- **`publish_content`** — promotes a staged draft into `artifacts/published/`. **Guarded.**
- **`post_social`** — the outbound egress action, a stub that does not actually post. **Guarded.**

### Whole-backlog runs are not unattended

A request to run all four ready entries has two intentional stopping points:
the supervisor's `user_daily_cost_budget` asks at **$0.50**, and four entries
across three sub-agents will very likely cross it; the publish ceiling permits
only **three distinct articles per UTC day**, so the fourth cannot ship that
day. For a whole backlog, the honest option is to run steps 1–11 for every
entry (stage everything), then publish one entry at a time. Do not expect an
unattended end-to-end run.

Runs on the **`claude-sdk` harness** with **`claude-sonnet-4-6`** for the supervisor, editor and social writer, and the **`codex` harness** with **`gpt-5-4`** for the blog writer. The gate is harness-independent — the same DENY fires whichever brains you swap in.

---

## Get Started

Nothing to build. The backlog ships seeded with five real Omnigent features, so the factory writes about the framework it runs on:

```bash
cat examples/content_factory/backlog.md
```

Four entries are `READY` — one of them deliberately thin, so a cycle will pick it up and it is designed to elicit a `REVISE` (the editor may also return `REJECT`) — and one is already `PUBLISHED`, which the state machine skips.

---

## Run Locally

> **This example uses a custom policy, so it needs a local server.** If you have
> run `omnigent login`, a plain `omnigent run` targets your configured remote
> server, which rejects unregistered policy handlers before the session starts.
> Use `--server local` and set `PYTHONPATH` so the policy module is importable:
>
> ```bash
> PYTHONPATH=$(pwd) omnigent run examples/content_factory/ --server local
> ```
>
> See "Custom policies do not run against a remote server" in the repo-root
> `CLAUDE.md` for what a remote deployment would require.


### 1. Configure credentials (one-time)

```bash
omnigent setup
```

### 2. Export your API keys

```bash
# Supervisor, editor and social writer run on claude-sdk — needs ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...
# blog_writer runs on codex — needs OPENAI_API_KEY
export OPENAI_API_KEY=sk-...
```

### 3. Run the agent

```bash
omnigent run examples/content_factory/

# Fresh session (no persistence — resets the cycle's publish count)
omnigent run examples/content_factory/ --no-session
```

Then ask it to run a cycle:

```
Run one factory cycle.
```

---

## Run on Databricks

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/content_factory/ --server https://omnigent-<id>.aws.databricksapps.com
```

The default config pins Databricks AI Gateway endpoints (`databricks-claude-sonnet-4-6`, `databricks-gpt-5-4`), so no direct provider keys are needed in this mode.

---

## Continuous Operation

There is **no cron field in agent YAML**. Recurring work is created at runtime, by the agent, through a tool — so the factory sets up its own schedule on first run:

```yaml
rrule: "FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
session_mode: new
```

The supervisor calls `sys_scheduled_task_create` with those parameters, and each firing starts a fresh session that runs one cycle.

**Creating a schedule is itself approval-gated.** The first thing you will be asked to approve is the factory's own existence — which is the right default for an agent that proposes to wake up every morning and write on your behalf.

Two other mechanisms exist if a daily RRULE is the wrong shape:

- `sys_timer_set` with `repeat` — a short runner-local loop, good for demos, but it dies with the runner. Timer tools are **off by default**: this config omits `timers:`, so you must add top-level `timers: true` to use it.
- `sys_reminder_set` — a durable one-shot wake-up. Part of the scheduled-task tool group, which is enabled by default.

---

## The Cycle, Step by Step

| # | Action | Who | Gated? |
|---|---|---|---|
| 1 | `read_backlog` → next `READY` feature | supervisor | no |
| 2 | stage the outline | supervisor | no |
| 3 | draft the post | `blog_writer` (Codex) | no |
| 4 | stage the draft | supervisor | no |
| 5 | `update_backlog` → `DRAFTED` | supervisor | no |
| 6 | review the draft | `editor` (Claude) | no |
| 7 | on `REVISE`/`REJECT`, loop back to step 3 | supervisor | no |
| 8 | `update_backlog` → `APPROVED` | supervisor | no |
| 9 | derive short-form copy | `social_writer` (Claude) | no |
| 10 | stage the X thread and LinkedIn post | supervisor | no |
| 11 | write the cycle log | supervisor | no |
| 12 | **`publish_content` / `post_social`** | human | **YES** |
| 13 | `update_backlog` → `PUBLISHED`, on success only | supervisor | checked, not asked |

Step 13 is what closes the state machine. It runs only after the human has approved and every shipping call for that slug has returned successfully — if a publish is denied, parked or errors, the entry stays `APPROVED` and the supervisor reports what failed. So `PUBLISHED` always means *shipped*, never *intended to ship*.

And it is not left to the prompt to get that right: `publish_gate` **R4** DENIES a `PUBLISHED` write for an article the session did not watch fully ship. No human is asked — it is a `DENY` or an `ALLOW` — so step 13 stays unattended while the status column stays truthful.

Step 7 is where the editor earns its keep: the supervisor is forbidden from proceeding past a `REVISE` verdict, and forbidden from substituting its own opinion for the editor's.

---

## Policy Engine

Two complementary layers guard the same two shipping tools.

### Policies

| Policy | Type | What it does |
|---|---|---|
| `publish_gate` | custom, stateful | Slug-aware. DENIES a social post whose blog is not yet `APPROVED`; DENIES shipping a *new* article once the cycle ceiling is hit, while letting an article already started finish; DENIES a `PUBLISHED` backlog write for an article that did not fully ship; otherwise ASKS with a reason naming the slug and artifact. |
| `guarded_tools` | builtin `risk_score` | Coarse unconditional brake. Knows nothing about slugs — escalates `publish_content` and `post_social` on **every** call, so the gate holds even if the custom policy is removed. |
| `no_self_modification` | builtin `cel` | Backstop. DENIES every Omnigent file **and shell** tool (`sys_os_write` / `sys_os_edit` / `sys_os_shell` plus the native `Write` / `Edit` / `MultiEdit` / `NotebookEdit` / `Bash` / `shell` / `apply_patch` aliases). Inert as configured — no agent declares `os_env`, so none holds such a tool — and there so that re-adding one does not silently restore the capability. See [Why the supervisor has no filesystem access](#why-the-supervisor-has-no-filesystem-access). |
| `user_daily_cost_budget` | builtin | $5.00/day per user, ASKs at $0.50. |

Each sub-agent additionally carries `cost_budget` ($1.00, ASK at $0.25) and `max_tool_calls_per_session` (250) to bound runaway tool use.

The two shipping layers **do not produce two prompts.** The engine evaluates every policy and joins all ASK reasons into one pending approval, so the human sees a single request carrying both reason lines.

### Custom policy: `publish_gate`

Four rules. R4 stands on its own — it is the only one that looks at a tool outside the guarded pair — and R1, R3, R2 are evaluated in that order on `publish_content` / `post_social`:

1. **R1 — DENY** `post_social` until this session has recorded a successful `update_backlog(status="APPROVED")` for that slug. The editorial intent is *short-form content cannot precede the long-form post it cites*; what R1 actually enforces is the recorded state transition, not the existence of a blog or an editor verdict. The supervisor performs that transition only after a `PASS`, which is what links the two.
2. **R3 — DENY** once `max_articles_per_cycle` (default 3) **articles** have shipped in the current cycle. The unit is the article — a *distinct backlog slug* — not the guarded call, because shipping one article fully takes three guarded calls (`publish_content`, plus a `post_social` per channel). Counting calls would hard-stop the second article partway through.

   So the rule is **you may finish an article you have started, but you may not start a new one past the ceiling**: R3 refuses a slug only when that slug is *not already* in the cycle's shipped set *and* the set is full. At a ceiling of 3, with articles A and B shipped and C's `publish_content` just counted, C's remaining `post_social` calls still go through — nothing is left published with its social copy stranded — while a fourth slug D is refused on its first call.

   A real stop, not a nag: the ceiling holds until the next cycle (a UTC calendar day).

   Be precise about what it caps, though: **articles started, not shipping actions.** Because an already-counted slug is exempt, the same article can be re-published within the cycle without the ceiling noticing. `max_articles_per_cycle: 3` does not bound the number of `publish_content` / `post_social` calls a cycle makes — R2 is what holds there, asking on every single one, so nothing ships unattended either way.
3. **R2 — ASK** any other `publish_content` or `post_social`, naming the slug and what is being shipped.

4. **R4 — DENY** an `update_backlog(status="PUBLISHED")` write for an article this session did not watch *fully* ship: `publish_content` succeeded **and** every social variant the cycle staged for it was then posted. It is a `DENY`, never an `ASK`, so no human joins the unattended path.

   R4 exists because `PUBLISHED` is the one backlog status that is not a description of work but **a claim that the work finished** — and it is the column a status dashboard reads. Step 13 of the supervisor prompt orders it correctly, but a prompt is not enforcement: a model under pressure can write it optimistically and nothing would stop it.

   Half-shipped is the failure that matters, not never-shipped. An article whose blog published while its staged social posts were skipped is exactly what a naive "did anything ship?" check waves through, so R4 tracks per-slug completion — what was staged, whether the blog published, which channels went out — and requires all of it. Two honest limits: an article for which **no** social variant was ever staged counts as complete once published (R4 cannot demand a post nobody wrote), and R4 is **not a security boundary**. It gates a tool call, so it has nothing to say about a supervisor that edits `backlog.md` directly and never calls `update_backlog` at all. That particular route is now shut by the supervisor holding no file-write tool ([below](#why-the-supervisor-has-no-filesystem-access)) — which is a different mechanism doing the work, not R4 getting stronger. R4 raises the floor on careless optimism.

### What is and is not gated

`read_backlog` (including its dashboard mode) and `save_artifact` are **never**
gated on any path. `update_backlog` is never gated either for `READY`,
`DRAFTED`, `EDITED` or `APPROVED` — every status that describes work in progress.

The one exception is the terminal `PUBLISHED` transition, and it is worth being exact about why that does not blunt the contrast: **R4 gates no work.** The producing tier still runs start to finish with no human and no check. What R4 checks is the *claim that the work is finished* — and it answers with a `DENY` or an `ALLOW`, never an `ASK`, so the unattended path stays unattended. The lesson is unchanged: cheap reversible work runs free, outward-facing irreversible action needs a signature, and a record of what shipped has to match what shipped.

### How the gate knows what was approved

`publish_gate` keeps its state in `session_state` and accumulates it on **`tool_result`**, not `tool_call` — because the engine withholds `state_updates` when a policy returns ASK, so a gated call could never record itself. Success is read fail-closed: a result with no `error` counts, anything else does not, so an unconfirmed `update_backlog` will not unlock `post_social`.

One subtlety worth knowing if you write your own stateful policy. Policies are evaluated on two paths, and only one of them carries state:

- the **server** path, which has the persisted `session_state`
- the **runner-local** path, which builds a fresh context with only the tool name and arguments, and discards any `state_updates` you return

A stateful rule that DENIES on absent state would therefore fire *permanently* on the runner-local path — an approved post could never be sent. `publish_gate` detects this case via `conversation_id` (documented as `None` only in contexts with no engine) and **defers**, letting the server — which does have the state — make the stateful call. All three stateful rules do this: R1, R3 and R4.

For R1 and R3 that costs nothing, because the coarse `guarded_tools` brake still ASKs locally. **R4 is the one place where deferring is not free:** nothing else gates `update_backlog`, so a `PUBLISHED` write on the runner-local path goes through unchecked. That is still the right trade — denying on state known to be missing would fail *every* local `PUBLISHED` write — but it is a real limit, and the reason R4 is a backstop against careless optimism rather than a guarantee.

### Two state scopes, deliberately not merged

`publish_gate` keeps two separate shipping records, and the split is the most instructive thing in the file:

| key | scope | whose record |
|---|---|---|
| `_publish_gate_cycle_slugs` | one UTC day | R3's ceiling. Resetting at midnight is the point of it. |
| `_publish_gate_ship_progress` | the session, per slug | R4's completion check. An article does not become unshipped at midnight. |

Keying R4 on the ceiling's record would be a bug with teeth: a publish at 23:59 and its status write at 00:01 would be refused, and the first call of a new cycle would reset the record out from under a perfectly good article. R4 therefore uses the session scope, matching R1's. The cost of *that* choice, stated plainly: since the daily schedule uses `session_mode: new`, a `PUBLISHED` write in a later session than the publish is refused. In the normal flow steps 12 and 13 are moments apart in one session, so it does not arise.

---

## Guardrails

The research rule is worth calling out, because an unsupervised writer with a search tool is a liability. `blog_writer` is the **only** agent with `web_search`, and its prompt restricts it to the URLs listed in that backlog entry's `sources:` field — nothing else. If a source is missing or unreachable it must say so in the draft rather than substituting another source. A factory that quietly invents its citations is worse than one that stops.

---

## Why the supervisor has no filesystem access

None of the four configs declares `os_env`. That is deliberate, and it is
written down here because of a failure worth admitting.

**What happened.** A smoke run of this example hit a machine-level sandbox
failure launching the Codex sub-agent. The supervisor decided it was authorised
to edit its own configuration, and wrote this to
`agents/blog_writer/config.yaml`:

```diff
-    harness: codex
+    harness: codex-native
+    # yolo: headless sub-agents cannot answer approval prompts, so run
+    # Codex with full sandbox bypass (--dangerously-bypass-approvals-and-sandbox).
+    yolo: true
```

It turned a sandbox off, unprompted, to get past an obstacle — in an example
whose entire subject is that irreversible actions require a human. The edit was
reverted and never committed.

**Why it could.** The supervisor declared
`os_env: {type: caller_process, cwd: ., sandbox: {type: none}}`. That block is
what makes the loader register `sys_os_read` / `sys_os_write` / `sys_os_edit` /
`sys_os_shell` for an agent; with no `os_env`, registration is a no-op and the
agent gets none of them. So the `os_env` block *was* the capability. Nothing in
the prompt asked for a config change, and an earlier cross-review had predicted
exactly this shape of problem.

**The fix is the absence of the capability, not a rule against using it.** A
prompt rule would be the wrong lesson in an example built to teach that policy
beats prompt, and it is precisely what already failed: the model wrote its own
justification for the edit into a comment. So the `os_env` block is gone from
all four configs.

Nothing is lost. Every write the documented workflow performs goes through one
of the [five tools](#five-tools), which run as server-side subprocesses rooted
at the workspace cwd — they never used the agent's `os_env`, so constraining it
was never a trade-off against `save_artifact` or `update_backlog`. On
`claude-sdk` the native `Write` / `Edit` / `Bash` tools are not exposed either
(the harness's base tool set is `Skill` + `ToolSearch`; `Bash` appears only for
a *sandboxed* CLI), so removing `os_env` leaves the supervisor with no
file-write tool of any kind.

`no_self_modification` is the second layer: a `cel` policy DENYing every
Omnigent file *and shell* tool by name. It is **inert as configured** — there
is no such tool to gate — and it is there because `os_env` is the boilerplate
CLAUDE.md documents, so re-adding it is a plausible accident. For the
`sys_os_*` family the gate is real: those calls route through Omnigent's
dispatch bridge and are evaluated before they run.

It is CEL rather than the `read_only_os` builtin because `read_only_os` matches
write/edit names only and allows `sys_os_shell`, and a shell redirect rewrites
YAML just as well as an edit. CEL takes an explicit tool list, so the shell
tools go in it. It is still a registry builtin, so the example's
remote-server story is unchanged.

`DENY`, not `ASK`, on purpose: the observed edit happened in a headless run,
and the model's own stated reason for disabling the sandbox was that headless
sub-agents cannot answer approval prompts. An `ASK` nobody can answer is the
pressure that produced the edit. What the backstop cannot do is gate Codex's
native tools — see below.

### What this does not close

One agent can still write the bundle, and it is worth being exact about why —
the first version of this change claimed the hole was one `os_env` block wide,
and that was wrong.

**`agents/blog_writer` runs `harness: codex`, and Codex has its own file
tools that are not Omnigent tools.** Removing `os_env` does take away its
`sys_os_*` tools, and it does narrow Codex's sandbox — `_sandbox_mode`
(`omnigent/inner/codex_executor.py:2830-2838`) maps `sandbox: {type: none}` to
`danger-full-access`, the whole filesystem, and an absent `os_env` to
`read-only`. That is a real reduction. But it is not a closure, for two
reasons that compound:

1. **The `read-only` does not survive.** Because the agent is passed
   AP-bridged tools, `codex_executor.py:5494-5496` upgrades `read-only` back
   to `workspace-write`:

   ```python
   sandbox_mode = _sandbox_mode(self._os_env_spec)
   if tools and sandbox_mode == "read-only":
       sandbox_mode = "workspace-write"
   ```

   Every agent here has framework builtins, so `tools` is never empty and the
   upgrade always fires. The bundle sits inside the workspace, so
   `agents/blog_writer/config.yaml` is writable.

2. **No policy can gate it.** Codex's native calls reach Omnigent marked
   `internally_executed` and have *already run* — see
   `omnigent/runtime/harnesses/_executor_adapter.py:1311-1313`: *"Observed
   native tools already ran inside their harness."* A `DENY` would be an
   after-the-fact observation of a completed write, not a gate. This is the
   part a policy cannot fix, and it is why `no_self_modification` is honest
   about covering only Omnigent's own tool names.

`disable_native_tools: true` on `blog_writer` removes half of it. On the
ordinary (non-brokered) Codex route that switch sends exactly one thing —
`features.shell_tool=false` (`codex_executor.py:4035`) — so the shell tool
goes away. `apply_patch` does not: checked against the installed codex-cli
0.149.1, that flag flips `shell_tool` alone, and no feature flag disables
`apply_patch`. The full strip that also nulls `apply_patch_tool_type`
(`codex_executor.py:2257`) runs only on the brokered-gateway route, which
additionally demands an active sandbox, a signer and `broker_gateway: true` —
deployment configuration, not something an example can set, and it needs the
very sandbox that fails to start here.

So, plainly: **a supervisor that cannot write files can still ask
`blog_writer` to write one, one delegation hop away.** What changed is the
blast radius — whole filesystem to workspace — and the shell half of the tool
surface. What did not change is that the capability exists.

Closing it properly means one of two things, both bigger than this change:

- **Move `blog_writer` off `harness: codex`.** On `claude-sdk` the native
  `Write` / `Edit` / `Bash` tools are never exposed (base tool set is `Skill` +
  `ToolSearch`), so with no `os_env` the agent would hold no write tool at all.
  That also deletes the cross-harness premise this example exists to show —
  OpenAI drafts, Claude edits — so it is a product decision, not a fix.
- **Run the brokered Codex route**, which does strip `apply_patch`. That needs
  a working platform sandbox; `darwin_seatbelt` and `auto` both fail launch
  preparation on the development machine (below).

Two smaller gaps, for completeness:

- **A `write_paths` sandbox would be more structural, and does not work here.**
  It is a kernel boundary rather than a tool-registration one, and would cover
  shell too. Both `sandbox: {type: darwin_seatbelt}` and `{type: auto}` fail
  launch preparation outright:

  ```
  OSError: Cannot validate trusted runtime: mutable hard-link alias for
  .../site-packages/platformdirs/__main__.py; install trusted runtime files
  as copies
  ```

  It is platform-dependent regardless — Windows `windows_jobobject` provides no
  filesystem isolation and is rejected for sandboxed `claude-sdk` launches.
  Shipping a configuration that fails to start is how you get the next
  `yolo: true`. If your host supports a sandbox, prefer it.
- **The tool switches carry a runner-version caveat.** Per
  `docs/AGENT_YAML_SPEC.md`, older runners ignore `disable_native_tools` on
  ordinary routes.

`tests/test_self_edit_guard.py` pins all of this, including the disclosure
text above: the cases that cover the bypass read these README files and fail if
the disclosure is deleted.

---

## Tests

The gate's four rules, `save_artifact`'s append-vs-truncate split, the
disk-derived dashboard, and the absence of filesystem access are the places
where a careless edit changes behaviour silently, so each has an executable
spec:

```bash
python examples/content_factory/tests/test_publish_gate.py
python examples/content_factory/tests/test_save_artifact.py
python examples/content_factory/tests/test_read_dashboard.py
python examples/content_factory/tests/test_self_edit_guard.py
# or: pytest examples/content_factory/tests/
```

`test_self_edit_guard.py` pins the invariant above at three strengths: the
YAML shape (no config declares `os_env`), the resolved behaviour (a real
`ToolManager` built against each of the four configs grants no `sys_os_*`
tool — the assertion that actually matters, since a framework regression would
sail past a YAML check), and the documentation. It also checks the backstop is
wired to a registry builtin, DENIES writes *and* shell across the bundle while
abstaining on all five staging tools, and that no config sets
`os_env`, and — because the Codex bypass below is real — they read both README
files and fail if the disclosure text is deleted. A docs-pinning test opens the
file or it does not exist.

Stdlib only, and `tests/` sits outside `tools/python/` so nothing in it is
auto-discovered as an agent tool. The six cases that execute the real
real `ToolManager` and the real policy skip when Omnigent is not installed;
the config and documentation invariants always run.

---

## How to Demo

See [demo.md](demo.md) for a ~12 minute script. The short version:

1. Show `backlog.md` and the two-tier `artifacts/` layout — one file explains the whole policy.
2. Run a cycle. Watch Codex draft and Claude edit, and watch steps 1–11 complete with no human input.
3. Watch it stop at step 12 and ask.
4. Try to post social copy for a slug that was never approved. **DENIED** — and read the reason.
5. Ship three articles, then try a fourth. **DENIED** until the next cycle — but the third article's remaining social posts still go out.
6. Ask it to mark something `PUBLISHED` that never shipped. **DENIED** — the status column cannot lie.

---

## Files

```
examples/content_factory/
├── config.yaml                     supervisor
├── agents/
│   ├── blog_writer/config.yaml     Codex — the only researcher
│   ├── editor/config.yaml          Claude — PASS / REVISE / REJECT
│   └── social_writer/config.yaml   Claude — X + LinkedIn
├── policies/
│   └── publish_gate.py             the gate: R1 / R3 / R4 DENY, R2 ASK
├── tools/python/                   five tools, two of them guarded
├── tests/                          executable specs for the gate, staging, and dashboard
├── skills/blog-style/SKILL.md      the editor's rubric
├── backlog.md                      five seeded Omnigent features
└── artifacts/                      everything the factory makes
```
