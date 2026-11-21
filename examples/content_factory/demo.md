# Content Factory — Walkthrough

A guided tour of this example. By the end you will have run a full production
cycle, watched the factory stage five content artifacts plus a dashboard snapshot without asking you anything, and
then watched it refuse to publish without your signature.

Read [README.md](README.md) first if you want the architecture. This file is the
hands-on path.

---

## Before you start

```bash
# Supervisor, editor and social writer run on claude-sdk
export ANTHROPIC_API_KEY=sk-ant-...
# blog_writer runs on codex
export OPENAI_API_KEY=sk-...

omnigent run examples/content_factory/
```

Nothing to build and no database to create. The example ships with its input
queue already filled in.

---

## Part 1 — Understand the input: `backlog.md`

Everything the factory does starts here, so it is worth five minutes before you
run anything.

```bash
cat examples/content_factory/backlog.md
```

### What it is

A plain-Markdown work queue of **blog topics**. One `##` section per topic:

```markdown
## contextual-policies
- status: READY
- title: How Omnigent's Contextual Policies Gate Data, Not Just Tools
- summary: Omnigent policies can evaluate runtime context and return ALLOW,
  ASK, or DENY decisions. This lets an agent distinguish safe work from
  actions that require a human decision.
- sources:
  - https://github.com/dmatrix/omnigent
```

| field | purpose |
|---|---|
| `## <slug>` | the entry's ID. Every artifact this topic produces is named after it. |
| `status` | where the topic is in the pipeline. The factory reads and writes this. |
| `title` | the working headline handed to the writer. |
| `summary` | the brief. This is what the draft gets written **from**. |
| `sources` | the **only** URLs `blog_writer` may research. |

### ⚠️ The topics are subjects to write about, not parts of this example

The shipped backlog is **self-referential**: the factory writes blog posts about
Omnigent itself. So you will see entries like `cross-harness-delegation` and
`guarded-tools-escalation`.

Those are *article topics*. They are **not** components of the content factory,
and `cross-harness-delegation` has nothing to do with the separate
[cross_harness_coding](../cross_harness_coding/) example — it is simply a real
Omnigent feature that makes a good blog post. Reading the backlog and thinking
"why is a content demo talking about coding harnesses?" is an easy and
reasonable mistake; the answer is that the backlog is *content*, not config.

If that is distracting for your audience, replace the five entries with topics
from your own domain. Nothing in the factory depends on what they say — see
[Part 5](#part-5--add-your-own-topic).

### What the statuses mean

```
READY  ──▶  DRAFTED  ──▶  APPROVED  ──▶  PUBLISHED
```

| status | set by | meaning |
|---|---|---|
| `READY` | you | available for the next cycle to pick up |
| `DRAFTED` | the supervisor, step 5 | a draft exists and is staged |
| `APPROVED` | the supervisor, step 8 | the editor returned `PASS` |
| `PUBLISHED` | the supervisor, step 13 | shipped — written only after you approved *and* the publish actually succeeded |
| `EDITED` | nobody | a valid value the workflow never writes |

`PUBLISHED` is the terminal state and the supervisor reaches it on its own, but
only on real success: if a shipping call is denied, parked or errors, the entry
stays at `APPROVED` and the supervisor says what failed. An entry reading
`PUBLISHED` therefore means *shipped*, never *about to ship*.

That one is enforced, not merely instructed. `publish_gate` R4 DENIES a
`PUBLISHED` write for an article the session did not watch fully ship — see
[DENY #3](#deny-3--a-published-status-that-did-not-happen). It is the only
`update_backlog` status that is checked at all.

Two honest caveats:

- `update_backlog` validates the **value**, not the transition. It will happily
  set `DRAFTED` on an entry that has no draft, or `APPROVED` on one no editor
  saw. The intended order comes from the supervisor's prompt, not from
  enforcement. `PUBLISHED` is the single exception, and the policy rather than
  the tool is what enforces it.
- `APPROVED` is load-bearing beyond bookkeeping. The `publish_gate` policy
  refuses to post social copy for a slug it has not seen recorded as `APPROVED`
  in this session. More on that in [Part 3](#part-3--try-to-break-the-gate).

As shipped: **four `READY`**, one already `PUBLISHED` (the factory skips it), and
one of the `READY` four — `recurring-schedules` — deliberately too thin to write
900 honest words from. Watch for that one in Part 2.

### Who creates it, and how

**You do, by hand.** It is a text file; edit it in any editor. There is no
generator, no schema validation, and no CLI command.

The factory only ever does two things to it:

```
read_backlog(status="READY", limit=1)     →  pull the next topic
update_backlog(slug=..., status=...)      →  advance one entry's status
```

Neither can add, remove, or rewrite an entry. `update_backlog` changes exactly
one `- status:` line and leaves every other byte of the file alone.

### Can an agent create the backlog automatically?

Short answer: **it could, but this example deliberately does not let it.**

Three layers to that:

1. **No tool is wired for it.** The five tools in `tools/python/` can read
   entries and change statuses. None writes a new one.
2. **The capability nonetheless exists.** The supervisor declares
   `os_env: {type: caller_process, sandbox: {type: none}}`, which grants
   filesystem access through the framework's own `sys_os_*` tools. If you asked
   it to append a topic to `backlog.md`, it could.
3. **Leaving it unwired is the point.** The backlog is the last place a human
   decides **what** gets written. If the factory fills its own queue it chooses
   its own subjects, and your only remaining control is a yes/no at publish
   time — on an article whose premise you never agreed to. Approving *output*
   is much weaker than choosing *input*.

If you do want an automated backlog, the shape that keeps the human in the loop
is a **proposal status**:

- add an `add_backlog_item(slug, title, summary, sources)` tool,
- have a research sub-agent write new entries as `status: PROPOSED`,
- teach `read_backlog` to ignore `PROPOSED`,
- and promote `PROPOSED` → `READY` yourself.

Then the agent fills the funnel and you still pick what enters production. That
is a genuine extension of this example rather than a change to it, and it is a
good exercise if you want to go further.

---

## Part 2 — Run one cycle

```
Run one factory cycle.
```

On a **fresh** session the supervisor will first propose a daily schedule. Say
no for now — Part 4 covers it — or approve it and carry on; it does not affect
this cycle.

Then watch thirteen steps. The supervisor announces which agent and which
harness is working at each one, by design.

Before it starts, the supervisor renders a full-width Markdown dashboard of the
whole backlog and opens the same read-only, disk-derived snapshot at
`artifacts/dashboard.md`. It refreshes only at `DRAFTED`, `APPROVED`, the
publish gate, and successful `PUBLISHED` — not after every step — so the table
shows durable backlog and artifact facts without flooding the chat. There is no
Start button to hunt for: example agents cannot configure one, so your `Run one
factory cycle.` chat message starts the work. The native Approve/Reject card at
step 12 is the review UI. Its publication total is all-time disk state, not a
fraction of the session-scoped daily ceiling, so the table does not claim it
knows the current policy counter.

| # | what happens | who | you? |
|---|---|---|---|
| 1 | pull the next `READY` topic | supervisor | — |
| 2 | stage an outline | supervisor | — |
| 3 | **draft the blog post** | `blog_writer` (Codex) | — |
| 4 | stage the draft | supervisor | — |
| 5 | set status `DRAFTED` | supervisor | — |
| 6 | **review the draft** | `editor` (Claude) | — |
| 7 | on `REVISE`/`REJECT`, back to step 3 | supervisor | — |
| 8 | set status `APPROVED` | supervisor | — |
| 9 | **derive X + LinkedIn copy** | `social_writer` (Claude) | — |
| 10 | stage both social pieces | supervisor | — |
| 11 | write the cycle log | supervisor | — |
| 12 | **publish / post** | — | **yes** |
| 13 | set status `PUBLISHED` — only if step 12 succeeded | supervisor | — |

Default `limit=1` means step 1 takes the *first* `READY` entry, so your first
cycle will draft `contextual-policies`.

### What to look for

**Two vendors in one pipeline.** Codex writes, Claude edits. The draft is
produced by one model family and judged by another.

**The research leash.** `blog_writer` is the only agent with `web_search`, and
its prompt restricts it to the URLs in that entry's `sources:` list. If a source
is unreachable it must say so in the draft rather than substitute another.

**Nobody approved anything.** Steps 1–11 run unattended. That is the design: if
drafting needed a signature, the factory would be a slow text editor.

When it stops, inspect what it made:

```bash
find examples/content_factory/artifacts -type f | sort
```

Six files for one topic — outline, draft, X thread, LinkedIn post, cycle log,
and the current dashboard snapshot. All free. All cheap to throw away.

The cycle log is the one that is **not** per-topic: it is named for the UTC date,
so a second cycle on the same day adds four new files and *appends* a second
entry to the same `artifacts/cycles/<date>-cycle.md`, separated by a rule. So a
multi-cycle day leaves you one log that reads as a sequence of cycles — rather
than, as it used to, one log describing only the last one.

If you ask for the whole backlog, expect an honest warning first: the $0.50
daily-cost policy will likely ask during four entries across three sub-agents,
and the three-articles-per-UTC-day ceiling stops the fourth publish. To stage
everything, ask for steps 1–11 across the backlog, then approve publishing one
entry at a time.

### See the editor push back

Run cycles until `recurring-schedules` comes up (it is `READY`, so a cycle will
reach it). Its summary is one bare sentence — "Omnigent supports recurring
scheduled tasks defined with an RRULE" — with no mechanism and no motivation.

The editor is designed to send that back as `REVISE`; `REJECT` is also a fair
outcome for a draft that thin. Either way the supervisor is **forbidden by its
prompt** from proceeding, so it routes the feedback back to `blog_writer`
instead of shrugging and publishing.

Note the enforcement strength here: that one is a *prompt* rule. The gate in
Part 3 is a *policy* rule. The difference matters.

---

## Part 3 — Try to break the gate

This is the part worth your attention. Everything above is plumbing.

### The gate itself

At step 12 the cycle stops and asks. Read the reason — it names the slug and
what is about to ship.

**Two policies fired, and you got one prompt.** The engine evaluates every
policy and joins all `ASK` reasons into a single pending approval, so you see
one request carrying both reasons:

| policy | what it contributes |
|---|---|
| `publish_gate` | custom, stateful, slug-aware — the specific reason |
| `guarded_tools` | builtin `risk_score`, slug-blind — the blanket brake |

The second is deliberately redundant. It knows nothing about slugs or state, so
the gate still holds if the custom policy is removed or misconfigured.

Approve it. The content moves to `artifacts/published/<slug>/`, and *then* the
supervisor calls `update_backlog(slug, "PUBLISHED")` — step 13. Check
`backlog.md`: the entry you just shipped is the one that reads `PUBLISHED`.

### DENY #1 — social copy before the post is approved

Ask it to post for a slug that has not been through the editor:

```
Post the LinkedIn copy for recurring-schedules.
```

**DENIED** — and note it happens *before* any approval prompt, because a `DENY`
short-circuits the engine.

Be precise about what that rule checks. `publish_gate` R1 refuses because this
session has no recorded successful `update_backlog(slug=..., status="APPROVED")`
for that slug. It does **not** inspect an editor verdict or confirm a blog
exists. The supervisor only records `APPROVED` after a `PASS`, and that is what
connects the policy to the editorial rule.

The useful part: this is not a prompt instruction the model might forget under
pressure. It lives outside the model, and the agent cannot talk its way past it.

### DENY #2 — the per-cycle ceiling

Ship three **articles** in one cycle, then start a fourth.

**DENIED**, and note it is a `DENY`, not another `ASK`. A ceiling that only nags
is not a ceiling. It holds until the next cycle — a UTC calendar day, matching
the daily schedule.

The unit is the **article**, meaning a distinct backlog slug — not the guarded
call. That distinction is load-bearing, because shipping one article fully takes
three guarded calls: `publish_content`, then a `post_social` per channel. If the
ceiling counted calls, `max_articles_per_cycle: 3` would stop the *second*
article on its first publish.

So the semantics are **finish what you started, but do not start a new one**:

| at a ceiling of 3 | verdict |
|---|---|
| articles A and B shipped; C's `publish_content` | `ASK` — the third article |
| C's `post_social` for x and linkedin, now at the ceiling | `ASK` — C is already counted |
| a fourth slug D's `publish_content` | **`DENY`** — D would be a new article |

Without that exemption C would end up published with no social copy — stranded
half-shipped by its own guardrail. Try it: at the ceiling, the article in flight
finishes and the next one does not begin.

The exemption has a consequence worth stating: the ceiling bounds the articles a
cycle **starts**, not the shipping actions it takes. An already-counted slug can
be re-published within the same cycle and R3 will not notice. `R2` is what holds
there — it ASKs on every single shipping call — so nothing goes out unattended
regardless, but do not read "3 per cycle" as a cap on outbound actions.

### DENY #3 — a `PUBLISHED` status that did not happen

The backlog's status column is about to be read by a dashboard, so the third
`DENY` guards the *record* rather than the action. Ask for a status you have not
earned:

```
Mark stateful-risk-scoring as PUBLISHED.
```

**DENIED.** `publish_gate` R4 refuses a `PUBLISHED` write for an article this
session did not watch *fully* ship. "Fully" is the operative word, and it is
what makes the rule worth having:

| what the session saw | `PUBLISHED` write |
|---|---|
| nothing shipped for the slug | **`DENY`** |
| social posts went out, `publish_content` never succeeded | **`DENY`** |
| `publish_content` succeeded, staged X and LinkedIn posts never posted | **`DENY`** — half shipped |
| `publish_content` plus every staged post succeeded | `ALLOW` |

That third row is the realistic failure. A check that only asked "did anything
ship?" would wave it through and leave the dashboard reporting a half-published
article as done — false confidence, which is worse than an honest prompt rule.

Note it is a `DENY`, not an `ASK`. Step 13 stays unattended; it just cannot lie.

Two limits, stated because a reader will find them anyway: an article for which
**no** social variant was staged counts as complete once published — R4 cannot
require a post nobody wrote — and R4 is not a security boundary. The supervisor
has `os_env: caller_process` with `sandbox: none`, so it could edit `backlog.md`
directly and skip `update_backlog` entirely. R4 raises the floor on careless
optimism; it does not stop a determined agent.

### What is and is not gated

```bash
# always free, every time, on every path
read_backlog (including dashboard mode) · save_artifact
# free for READY, DRAFTED, EDITED, APPROVED — checked only for PUBLISHED
update_backlog
```

That contrast is still the whole lesson: drafting is cheap and reversible, so it
is unattended. Publishing is neither, so it asks.

R4 does not dent it, and it is worth seeing why. **R4 gates no work.** The
producing tier runs start to finish with nobody watching. What R4 checks is the
claim that the work finished — and it answers `DENY` or `ALLOW`, never `ASK`, so
no human is added to the unattended path. Free to do the work; not free to
misreport it.

---

## Part 4 — Make it continuous

Agent YAML has **no cron field**. Recurring work is created at runtime, by the
agent, through a tool — so the factory sets up its own schedule:

```yaml
rrule: "FREQ=DAILY;BYHOUR=9;BYMINUTE=0"
session_mode: new
```

On its first fresh run the supervisor *proposes* this via
`sys_scheduled_task_create`. Each firing starts a new session and runs one
cycle.

**Creating a schedule is itself approval-gated.** The first thing this agent
asks you to approve is its own existence — which is the right default for
something proposing to wake up every morning and write in your name.

```bash
omnigent run examples/content_factory/   # then: "Show me the schedule you created."
```

---

## Part 5 — Add your own topic

The real test of whether you understand the example.

```markdown
## my-first-topic
- status: READY
- title: A Headline You Would Actually Click
- summary: Two or three sentences of real detail. This is the brief the writer
  drafts from, so a thin summary produces a thin draft the editor will bounce.
- sources:
  - https://example.com/the-one-page-you-want-cited
```

Append that to `backlog.md`, then:

```
Run one factory cycle.
```

Three rules worth respecting:

1. **The slug must be unique** and is used verbatim in every artifact filename.
2. **Do not start a line inside a field with `## `** — sections are split on
   `^## `, so that manufactures a phantom entry which never surfaces.
3. **Put real URLs in `sources:`.** They are the writer's only permitted
   research, and it must flag a missing one rather than invent a replacement.

The parser handles colons in titles and summaries, slugs that are prefixes of
other slugs, empty `sources:` lists, and CRLF line endings. Any rejected update
leaves the file byte-for-byte unchanged.

---

## Presenting this to an audience

A ~12 minute version:

| min | beat |
|---|---|
| 2 | `backlog.md` and the two-tier `artifacts/` layout — the design in two files |
| 4 | one unattended cycle: Codex drafts, Claude edits, five content artifacts plus the dashboard, no human |
| 2 | the gate — two policies, one prompt — then approve |
| 1 | DENY: social copy before the post is approved |
| 1 | DENY: the per-cycle ceiling — three articles, and the one in flight still finishes |
| 1 | DENY: a `PUBLISHED` status for an article that only half shipped |
| 2 | it schedules itself, and that is gated too |

Never cut the unattended cycle or the gate. Those two together are the argument.

---

## Troubleshooting

**"Nothing is `READY`."** Every entry has moved on. Reset one:
`update_backlog` back to `READY`, or edit the file.

**The same topic keeps coming up.** Its status never advanced — the cycle
probably stopped at the editor. Check `artifacts/drafts/`.

**A social post is denied and you think it should not be.** The gate needs a
recorded `APPROVED` transition **in this session**. A fresh session starts with
no memory, so re-run the cycle rather than jumping to step 12.

**The publish ceiling will not lift.** It counts distinct articles (slugs)
shipped, and is scoped to a UTC day. Raise `max_articles_per_cycle` in
`config.yaml`, or wait for the next cycle. If the slug you are shipping is
already counted this cycle, the ceiling does not apply to it — a `DENY` naming
the ceiling means that slug is a *new* article.

**Nothing posts to X or LinkedIn.** Correct — `post_social` is a local stub. It
writes a simulated JSON record to `artifacts/published/<slug>/` and makes no
network request.

**A `PUBLISHED` write is denied and you think it should not be.** R4 needs the
publish to have happened **in this session**, and needs it to be complete — if
you staged an X post and a LinkedIn post, both have to have gone out. The
message names which part is missing. A legitimate case it still refuses: the
publish happened in an *earlier* session (the daily schedule uses
`session_mode: new`), so a later session cannot close the entry out. Re-run the
cycle, or edit `backlog.md` by hand.
