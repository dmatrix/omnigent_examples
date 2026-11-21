# Content Factory — Demo Script

## How to Demo (~12 min)

The through-line: **a factory that works while you sleep, and knows what it may
not ship without you.** Everything else is scaffolding for that one sentence.

```bash
omnigent run examples/content_factory/
```

---

### Act 1: The two tiers (2 min) — "The whole policy is a directory listing"

Open `README.md` and show the `artifacts/` tree, then the config:

```bash
sed -n '/^artifacts/,/post_social/p' examples/content_factory/README.md
grep -A6 'guarded_tools:' examples/content_factory/config.yaml
```

Say it plainly:

> Five artifact kinds. Three are free, two are gated. The free ones are cheap
> and reversible — an outline, a draft, a cycle log. The gated ones are
> irreversible: promoting to `published/`, and posting outward. That's the
> entire design, and it's two lines of `guarded_tools`.

Then point at `threshold: 0` and note there is no `guarded_tools` builtin —
it's an argument to `risk_score_policy`. People always assume the former.

---

### Act 2: The backlog (1 min) — "Five features, one already shipped"

```bash
cat examples/content_factory/backlog.md
```

Four `READY` — one of them deliberately thin — and one already `PUBLISHED`,
which the state machine skips. Flag the thin one now so the audience is waiting
for it in Act 4:

> That last entry is too vague to write 900 honest words from. Watch what the
> editor does with it.

---

### Act 3: The unattended run (4 min) — "Steps 1 through 11, no human"

```
Run one factory cycle.
```

Narrate the handoffs as they appear — the supervisor announces each agent and
its harness by design:

1. `read_backlog` pulls the next `READY` feature.
2. The outline is staged.
3. **Codex** drafts the post, researching only the URLs in that entry's
   `sources:` list.
4. **Claude** edits and returns a verdict.
5. **Claude** derives the X thread and LinkedIn post.
6. The cycle log is written.

Then the point:

> Eleven steps, two vendors, five artifacts on disk — outline, draft, X thread,
> LinkedIn post, cycle log. Nobody approved anything. That's deliberate — if
> drafting needed a signature, the factory would be a very slow text editor.

Show the staged output:

```bash
find examples/content_factory/artifacts -type f | sort
```

---

### Act 4: The bounce (1 min) — "The editor is not a rubber stamp"

Run cycles until the thin entry comes up — it is seeded `READY`, so a normal
cycle will select it. To go straight there, set the other `READY` entries to
`DRAFTED` first, or just ask the factory to run the next cycle repeatedly.

The entry is designed to elicit a `REVISE` (a `REJECT` is also a valid outcome
for a draft this thin). Either way the supervisor is forbidden by its prompt
from proceeding — it routes the feedback back to `blog_writer` rather than
shrugging and publishing.

> The supervisor is forbidden by its prompt from overruling the editor or
> substituting its own opinion of the draft. The verdict is the verdict. Note
> this one is prompt-enforced, not policy-enforced — unlike the gate in Act 6.

---

### Act 5: The gate (2 min) — "Step 12 needs you"

The cycle stops and asks. Show the pending approval and read the reason aloud —
it names the slug and the artifact.

Point out that **two** policies fired and the human sees **one** prompt: the
engine joins the slug-specific reason from `publish_gate` with the blanket
reason from `guarded_tools` into a single pending approval.

Approve it. The content ships to `artifacts/published/<slug>/`.

---

### Act 6: Sequencing (1 min) — "You can't tweet about a post that doesn't exist"

Ask it to post social copy for a slug that was never approved:

```
Post the LinkedIn copy for <a slug that has not passed the editor>.
```

**DENIED**, before any approval prompt appears — R1 short-circuits the engine.

> No social post for a slug this session never recorded as `APPROVED`. That
> isn't a prompt instruction the model might forget under pressure — it's a
> policy, outside the model, that the agent cannot talk its way past. Be precise
> about what it checks: the recorded state transition, not the existence of a
> blog. The supervisor only records `APPROVED` after a `PASS`, and that is what
> connects the policy to the editorial rule.

---

### Act 7: The ceiling (1 min) — "Three a day, then stop"

Publish until the cycle ceiling is reached, then try a fourth.

**DENIED** — and note that this is a DENY, not another ASK. A ceiling that only
nags is not a ceiling. It holds until the next cycle.

---

### Act 8: Continuous operation (1 min) — "It schedules itself"

```bash
grep -A4 'Continuous operation' examples/content_factory/config.yaml
```

On its first fresh run the supervisor *proposes* the schedule, calling
`sys_scheduled_task_create` with `FREQ=DAILY;BYHOUR=9;BYMINUTE=0`. Close on the
detail that lands best:

> Creating that schedule is itself approval-gated. The first thing this agent
> ever asks you to approve is its own existence — which is exactly the right
> default for something that proposes to wake up every morning and write in
> your name.

---

### Timing Summary

| Act | Minutes | Beat |
|---|---|---|
| 1 | 2 | Two tiers, one config block |
| 2 | 1 | The seeded backlog |
| 3 | 4 | Eleven unattended steps, two vendors |
| 4 | 1 | The editor bounces a thin entry |
| 5 | 2 | The gate — two policies, one prompt |
| 6 | 1 | DENY: social before long-form |
| 7 | 1 | DENY: per-cycle ceiling |
| 8 | 1 | It schedules itself, gated |

**Total: ~13 min.** Drop Acts 4 and 7 for a 9-minute version; never drop 3 or
5, which are the whole argument.
