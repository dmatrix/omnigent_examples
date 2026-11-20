---
name: blog-style
description: The content factory's editorial rubric. Use when drafting or reviewing a blog post or short-form social copy produced by the factory, and when deciding a PASS / REVISE / REJECT verdict. Triggers on "review this draft", "edit the post", "what's the verdict", "derive social copy".
---

# Blog Style — the factory's editorial rubric

This is the standard the `editor` applies and the standard `blog_writer` should
write to. It is deliberately strict about sourcing, because the factory drafts
unattended and a confidently wrong post is the most expensive thing it can
produce.

## Verdicts

The editor returns exactly one:

- **PASS** — ship it. Every rubric item below is satisfied.
- **REVISE** — specific, fixable problems. List them with line references. The
  supervisor sends these back to `blog_writer` and the cycle does not advance.
- **REJECT** — the premise or structure is wrong and the draft needs rewriting
  from the outline, not patching.

Default to REVISE over PASS when unsure. A REVISE costs one more drafting pass;
a wrong PASS costs a published mistake.

## Hard rules — any violation is at minimum a REVISE

1. **Sourcing.** Every factual claim about the feature traces to a URL in the
   backlog entry's `sources:` list. No claim may rest on the writer's prior
   knowledge of the product.
2. **No invented capability.** If the sources do not establish that a feature
   exists or behaves a certain way, the draft must not assert it. "Omnigent
   can…" claims are the most dangerous sentences in the post.
3. **Missing sources are stated, not papered over.** If a source was
   unreachable, the draft says so plainly. Substituting a different source is a
   REJECT.
4. **No fabricated numbers.** No benchmarks, percentages, latencies or adoption
   figures that are not in the sources.
5. **Code must be runnable as written.** YAML keys, tool names and CLI
   invocations must match the sources exactly. A config snippet with an invented
   key is a REVISE even if the prose around it is good.

## Rubric

**Opening.** The first two sentences state the problem the feature solves, in
the reader's terms. Not "Omnigent has a new feature" — rather, the situation
that makes someone need it.

**One idea.** The post teaches exactly one thing. A draft covering three
features is a REVISE: it becomes three backlog entries.

**Concreteness.** At least one real, copy-pasteable artifact — a config block, a
command, a policy snippet. A post with no artifact is a brochure.

**Honest limits.** Say what the feature does not do. A post that reads as pure
advocacy loses the technical reader on first contact.

**Length.** 700–1200 words. Under 700 is usually a thin backlog entry that
should have been bounced earlier. Over 1200 usually means two posts.

**Ending.** Closes on what the reader can do next, not a summary of what they
just read.

## Voice

Plain, direct, technical. Address the reader as a peer who is busy.

Avoid: "unlock", "seamless", "effortless", "revolutionize", "game-changing",
"leverage" as a verb, "in today's fast-paced world", rhetorical questions as
section openers, and any sentence that would survive unchanged in a press
release.

Prefer: active voice, concrete nouns, short sentences next to long ones. Em
dashes over semicolons. No emoji in the blog body.

## Short-form derivation

Short-form copy is derived **from a PASSed draft only** — never written ahead of
it. The policy enforces this, but the rule is editorial first: a social post is
a pointer to something that exists.

**X thread.** 3–5 posts. The first post must stand alone and contain the single
most surprising true fact from the piece. No "a thread 🧵". No hashtags. Final
post carries the link.

**LinkedIn.** 120–200 words, one idea, one concrete detail from the post, and a
closing line that invites disagreement rather than applause. No hashtag block.

Both must be checkable against the blog draft line by line. Any claim in
short-form copy that is not in the draft is a REVISE on the social artifact.
