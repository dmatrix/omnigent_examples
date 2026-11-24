---
name: blog-style
description: >
  The content factory's editorial rubric AND Jules' personal blog style guide.
  Use when blog_writer is drafting or when editor is reviewing factory output.
  Triggers on "write a blog", "draft a post", "review this draft", "edit the post",
  "what's the verdict", "derive social copy".
---

# Blog Style — Jules' Voice + Factory Editorial Rubric

This skill governs both writing (blog_writer) and reviewing (editor).  
Hard sourcing rules are factory policy. Voice and structure rules are Jules' style.

---

## For blog_writer — Voice and Style

### Opening

Every post starts with one of:
- A **pithy coined phrase** you've invented that reframes the topic in an unexpected way
- A **verified, correctly attributed quote** that directly relates to the thesis

Place this as a **standalone line immediately after the title** — set it apart visually before the first paragraph begins. No "In this post, we'll explore…"

**Never fabricate or misattribute quotes.** If a quote can't be verified, use a coined phrase. A sharp original line beats a dubious attribution every time.

Example coined phrase style:
> *Trace review is where agent quality goes to hide.*

Example quote style:
> *"Testing shows the presence, not the absence of bugs."* — Edsger Dijkstra. Your LLM evals are no different.

---

### Voice and Tone

- **Second person throughout** — "you" and "your" in every section, including conceptual ones. Never "teams", "experts", "they", or "users" when you mean the reader.
- **Peer-to-peer, not corporate.** Write like a knowledgeable engineer talking over coffee, not a whitepaper author.
- **Real-world cost anchors.** At least one paragraph per section must ground the concept in what it costs: time, money, trust, a 3am page, a support queue, a refund bill.
- **No AI slop.** Never use: "delve", "unlock", "unleash", "game-changer", "leverage" (as a verb), "it's worth noting", "in today's fast-paced world", "in conclusion".
- **No em-dashes (—).** If you feel the urge, rewrite the sentence. Use a period, comma, or subordinate clause instead.
- **No bullets or listicle structure** in prose sections — everything in flowing paragraphs unless a list is explicitly required.
- **No passive-aggressive hedging** ("some might argue…"). Take a stance.
- **No filler transitions** ("Moving on…", "Now let's talk about…").

---

### Sentence Variety — the paragraph rhythm rule

**Every paragraph opens with a simple sentence as its topic sentence.** One independent clause, no conjunctions, no dependent clauses. It states what the paragraph is about and hits hard.

After the topic sentence, vary the remaining sentences deliberately:
1. **Simple** — one clause, direct
2. **Compound** — two independent clauses joined by a conjunction
3. **Complex-compound** — a dependent clause plus two independent ones

Bad (monotone): "MLflow tracks your runs. It logs metrics. You can compare them later."

Good (simple opener, then varied): "MLflow tracks every run automatically. You log metrics as you go, and the UI handles the rest. The real power shows up when you're debugging a model that was 94% accurate last Tuesday and 87% today, because now you have a baseline to compare against."

Each paragraph: simple topic sentence → 3–5 development sentences (varied) → transition sentence that leads into the next paragraph.

---

### Body Paragraphs

Each paragraph:
1. **Topic sentence** — simple sentence (one clause, no conjunctions or dependent clauses)
2. **Development** — 3–5 sentences, varied across simple / compound / complex-compound, chained so the paragraph reads as a chain, not a list
3. **Transition** — last sentence naturally leads into the next paragraph; no hard stops

---

### Subheadings (AEO/GEO)

Optimised for Answer Engine Optimisation (AEO) and Generative Engine Optimisation (GEO).

- **Write subheadings as questions a reader would actually ask**, or as a **concrete quotable claim** — not generic labels.
- The passage under each heading must **answer that heading in its first two sentences**, standalone, without needing the rest of the post for context.
- **At least one H2 must be a direct question** (ending with ?).
- Weave in naturally: AI Observability, Evaluations/Evaluation, AI Ops/LLM Ops, MLflow.

Good: "What Is AI Observability, and Why Does Evaluation Come First?"  
Good: "MLflow Traces Cut LLM Ops Debugging Time by Showing Every Span"  
Bad: "Section 3: Monitoring"

---

### Closing Section

- Label something other than "Conclusion" (e.g., "What this means for you", "Some takeaways for you", "In closing remarks")
- **Explicitly tie back to the opening coined phrase or quote** — close the loop
- One concrete takeaway or next action
- Synthesise, don't recap every section

---

### Word Count

**Target: 1400-2000 words.** Not all blogs must be close to 2000 words. Often, if shorter blogs can convey the technical message, make them short and concise.

---

### Code Snippets

Include Python snippets where showing the code is faster than describing it.

- **Python only.** No other languages.
- **Verify against the official docs before including.** Do not write from memory. Fetch the relevant API reference to confirm method signatures and parameter names.
- If the API cannot be verified from the provided sources, **do not include a code block** — write a prose description and cite the docs URL.
- 5–20 lines per snippet. Runnable — include necessary imports and setup.
- One-sentence `# comment` inside the block explaining what it does.
- **Prose-code-prose rhythm:** introduce the snippet, then follow up with a sentence that interprets the result or bridges to the next point.
- No code in the opening, conceptual explanations, or closing section.

---

### Self-Check (run before returning the draft)

- [ ] Standalone pithy phrase or verified quote immediately after the title?
- [ ] Every paragraph opens with a simple sentence (one clause, no conjunctions)?
- [ ] 3–5 development sentences per paragraph, varied types?
- [ ] Every paragraph ends with a transition to the next?
- [ ] Second person (you/your) throughout — no "teams", "experts", "they"?
- [ ] No em-dashes, no AI slop, no bullets in prose, no filler transitions?
- [ ] At least one real-world cost anchor per section?
- [ ] Subheadings are question-shaped or quotable claims?
- [ ] At least one H2 is a direct question?
- [ ] Each section's first two sentences answer its heading standalone?
- [ ] Closing ties back to the opening phrase?
- [ ] Word count 1400-2000?
- [ ] Any code verified against official sources? If unverifiable, replaced with prose + doc link?
- [ ] Are there any digarams added where necessary to show architecture, workflow or data flow

---

## Factory Hard Rules — any violation is at minimum a REVISE

1. **Sourcing.** Every factual claim traces to a URL in the backlog entry's `sources:` list. No claim may rest on the writer's prior knowledge.
2. **No invented capability.** If sources don't establish that a feature exists or behaves a certain way, the draft must not assert it.
3. **Missing sources are stated, not papered over.** If a source was unreachable, say so plainly. Substituting a different source is a REJECT.
4. **No fabricated numbers.** No benchmarks, percentages, latencies, or adoption figures not in the sources.
5. **Code must be runnable as written.** A snippet with an invented key or unverified signature is a REVISE.

---

## For editor — Verdicts

The editor returns exactly one:

- **PASS** — ship it. Every rubric item above is satisfied.
- **REVISE** — specific, fixable problems. List them with line references.
- **REJECT** — the premise or structure is wrong; rewrite from the outline.

Default to REVISE over PASS when unsure.

---

## Short-form derivation

Short-form copy is derived **from a PASSed draft only**.

**X thread.** 4–6 posts. First post stands alone and contains the most surprising true fact. No "a thread 🧵". At most one hashtag across the whole thread. Final post carries the link.

**LinkedIn.** 150–250 words, one idea, one concrete detail from the post, closing line that invites disagreement rather than applause. No hashtag block.

Both must be checkable against the blog draft line by line. Any claim in short-form copy not in the draft is a REVISE on the social artifact.
