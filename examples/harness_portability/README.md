# Harness Portability with Omnigent <img src="../../images/omnigent_icon.svg" alt="Omnigent" height="32" align="top">

**One supervisor, four inspectors, four harnesses — a Code Project Health Inspector built from composition.**

![Harness Portability Architecture](images/harness_portability_architecture.svg)

---

## Overview

### Why this example matters

Most AI agent frameworks lock you into a single LLM provider. Your prompts, tools, and governance are written against one SDK — and when you need to swap models (a better model launches, pricing changes, a provider has an outage, or compliance requires a specific vendor), you rewrite everything. Omnigent eliminates that lock-in. This example proves it with a real application: a **Code Project Health Inspector** that clones a GitHub repository, analyzes it across four dimensions, and produces a graded health report — using four different LLM providers simultaneously, orchestrated from pure YAML.

### What this demonstrates

This example shows three Omnigent capabilities working together:

1. **Harness portability** — The same agent definition (prompt, tools, guardrails) runs unchanged on Claude SDK, Codex, Pi, and Hermes. The harness is a one-line config value, not an architectural commitment. Swapping a sub-agent from Codex to Claude takes one line edit — zero prompt changes, zero tool rewrites, zero policy adjustments.

2. **Multi-agent composition** — A supervisor agent dispatches four specialist sub-agents, each running on a different LLM harness, within a single session tree. The agents share filesystem access and policy state. This is not four independent scripts — it is one coordinated workflow with a shared session, layered cost governance, and a unified output artifact.

3. **Provider-agnostic governance** — Guardrails (cost checkpoints, tool call limits) are defined in YAML and enforced by the Omnigent PolicyEngine — not by the LLM provider. The cost guard never hard-terminates — it asks for approval at soft thresholds and prompts for a model downgrade at the budget limit. The user always decides whether to continue. These fire identically whether the agent behind them is Claude, GPT, Pi, or Hermes. You define governance once and it follows the workflow across providers.

4. **Cross-harness observability** — MLflow tracing captures every agent turn, tool call, and policy evaluation across the session tree. Load `/setup-mlflow-tracing-claude` and `/setup-mlflow-tracing-codex` to enable tracing for the supported harnesses. Traces are stored in a local `mlflow.db` and viewable in the MLflow UI — no per-harness instrumentation code needed.

### Why Omnigent

Without Omnigent, building this would require writing four separate integrations (Anthropic SDK, OpenAI SDK, Pi client, Hermes client), four different tool registration mechanisms, four separate cost-tracking implementations, custom orchestration code to tie them together, and per-provider tracing instrumentation. With Omnigent, it is five YAML files and zero lines of Python. The framework handles harness translation, tool registration, session management, policy enforcement, and MLflow tracing — so you focus on what the agent does, not how it talks to each provider.

### The architecture at a glance

- **Supervisor** (`claude-sdk`) — asks for a GitHub repo URL (or accepts one inline), clones the repo, dispatches four inspectors, assembles the final report
- **`structure_inspector`** (`claude-sdk`) — Project Structure & Documentation
- **`test_inspector`** (`codex`) — Test Coverage & CI
- **`dependency_inspector`** (`pi`) — Dependency Health
- **`security_inspector`** (`hermes`) — Code Quality & Security

No `tools/python/` directory. No custom Python functions. All capabilities come from `os_env` (shell access). The only `tools:` block is the supervisor's four agent references. The supervisor assembles a `health_report.md` with letter grades, findings, and actionable recommendations from all four inspectors.

Start with [cross-harness coding](../cross_harness_coding/) to learn the delegation pattern (Codex implements, Claude reviews), then come here to see four harnesses collaborating in one session. From here, explore [governance](../secure_code_assistant/) (information flow control) and [data taint](../telco_customer_agent/) (PII/financial labels).

---

## Get Started

No database setup needed. No custom tool code. Just YAML.

### Prerequisites

- Python 3.12+
- The `omnigent` CLI installed (`pip install omnigent`)
- `git` installed (for cloning repos to inspect)
- API key(s) and CLI tools for the harnesses you want to use

| Agent | Harness | CLI Tool Required | API Key |
|---|---|---|---|
| Supervisor | `claude-sdk` | None | `ANTHROPIC_API_KEY` in `.env` |
| `structure_inspector` | `claude-sdk` | None | `ANTHROPIC_API_KEY` in `.env` |
| `test_inspector` | `codex` | Codex CLI (`npm i -g @openai/codex`) | `OPENAI_API_KEY` in `.env` |
| `dependency_inspector` | `pi` | Pi CLI (`npm i -g @earendil-works/pi-coding-agent`) | Uses configured provider |
| `security_inspector` | `hermes` | Hermes CLI | Uses configured provider |

> To run the full example out of the box, you need credentials for all four harnesses. To get started quickly, swap the sub-agents you don't have credentials for to `claude-sdk` (one-line edit per sub-agent).

---

## Run Locally

### 1. Configure credentials (one-time)

```bash
omnigent setup
```

### 2. Export your API keys

```bash
# For Claude SDK (supervisor + structure_inspector)
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')

# For Codex (test_inspector)
export $(grep OPENAI_API_KEY .env | tr -d '"')
```

### 3. Enable MLflow tracing

MLflow tracing captures every agent turn, tool call, and policy evaluation across all harnesses. Enable it before running the agent:

**For Claude SDK** (supervisor, structure_inspector):
```
/setup-mlflow-tracing-claude
```

**For Codex** (test_inspector):
```
/setup-mlflow-tracing-codex
```

Each skill is idempotent — safe to run multiple times. It checks/starts the local MLflow tracking server, runs `mlflow autolog` for the harness, configures the environment, and confirms tracing is active. Traces are stored in a local `mlflow.db` SQLite file and viewable at `http://localhost:5000`.

You can also configure tracing manually in `.claude/settings.json`:

```json
{
  "env": {
    "MLFLOW_CLAUDE_TRACING_ENABLED": "true",
    "MLFLOW_TRACKING_URI": "http://localhost:5000",
    "MLFLOW_EXPERIMENT_NAME": "harness-portability-traces"
  }
}
```

With tracing enabled, every run produces a trace tree showing the supervisor dispatching to four sub-agents across four harnesses — with timing, cost, and token usage per span.

### 4. Run the agent

```bash
omnigent run examples/harness_portability/

# Fresh session (no persistence)
omnigent run examples/harness_portability/ --no-session

# Provide a GitHub URL directly (skips the prompt)
omnigent run examples/harness_portability/ --no-session -p "https://github.com/dmatrix/omnigent_examples"
```

The supervisor will ask for a GitHub repository URL, or detect one if you provide it via `-p` or in your first message. It will then clone the repo, dispatch the four inspectors, and generate a health report.

---

## Example Queries

### Recommended for testing (small repos, low token cost)

These repos are small enough to avoid burning tokens yet have enough structure to exercise all four inspectors:

**This repo (smoke test — you know the expected output):**
```
Inspect https://github.com/dmatrix/omnigent_examples
```

**Dual-ecosystem library (Rust + Python, CI, lock files, real tests):**
```
Inspect https://github.com/ijl/orjson
```

**Small companion project (tests, pinned deps, GitHub Actions):**
```
Inspect https://github.com/willmcgugan/textual-web
```

**Well-known HTTP client (thorough README, pytest suite, CI, setup.cfg):**
```
Inspect https://github.com/httpie/cli
```

### Larger projects (more thorough, higher token cost)

**Well-maintained framework:**
```
Inspect https://github.com/pallets/flask
```

**Popular Python library:**
```
Inspect https://github.com/psf/requests
```

### Follow-up after inspection
```
Which findings are the most critical? What should the maintainers fix first?
```

The supervisor clones the repo to `/tmp/omnigent_inspect/<repo_name>`, dispatches four inspectors, and writes `health_report.md` in the current working directory.

---

## Harness Swapping

The CLI `--model`/`--harness` flags override the **supervisor only** — sub-agent harnesses are set in their own `config.yaml` files.

**Override the supervisor:**
```bash
omnigent run examples/harness_portability/ --model gpt-5.4 --harness codex
```

**Swap a sub-agent:** edit one line in its `config.yaml`. For example, to move `test_inspector` from Codex to Claude SDK:

```yaml
# agents/test_inspector/config.yaml
executor:
  type: omnigent
  model: claude-sonnet-4-6       # was: gpt-5.4
  config:
    harness: claude-sdk           # was: codex
```

The prompt, `os_env`, and guardrails stay identical — only the `executor:` block changes.

**Default sub-agent assignments:**

| Agent | Default Harness | Default Model |
|---|---|---|
| `structure_inspector` | `claude-sdk` | `claude-sonnet-4-6` |
| `test_inspector` | `codex` | `gpt-5.4` |
| `dependency_inspector` | `pi` | `claude-sonnet-4-6` |
| `security_inspector` | `hermes` | `claude-sonnet-4-6` |

---

## How to Demo (8-9 min)

### Act 1: The YAML (1.5 min) — "One supervisor, four inspectors, four harnesses"

**Show** `config.yaml`. Point out:

**Say:** "This is the supervisor — Claude SDK. It references four sub-agents in its `tools:` block. It doesn't inspect anything itself — it clones the repo, dispatches to four inspectors, and assembles the report."

**Show** `agents/test_inspector/config.yaml`.

**Say:** "Each inspector is its own config. This one runs on Codex. The structure inspector runs on Claude, the dependency inspector on Pi, the security inspector on Hermes. Four harnesses, one session tree. To swap any inspector's harness, change one line."

---

### Act 2: Run It (3 min) — "Inspect a real repo"

**Run:** `omnigent run examples/harness_portability/ --no-session`

**Prompt:**
```
Inspect https://github.com/pallets/flask
```

**Watch:** The supervisor clones Flask, then dispatches four inspectors. You'll see each inspector working on its category — structure, tests, dependencies, security — each on a different harness.

**Say:** "The supervisor cloned the repo and dispatched four inspectors. Each one runs on a different LLM — Claude analyzes structure, GPT analyzes tests, Pi checks dependencies, Hermes scans for security issues. Same prompt pattern, same tools, different brains."

---

### Act 3: The Report (1 min) — "Four inspectors, one report"

**Show** `health_report.md`.

**Say:** "The supervisor collected findings from all four inspectors and assembled them into one report with letter grades per category and an overall score. The inspectors ran on four different harnesses, but the output is a single coherent artifact."

---

### Act 4: The Swap (2 min) — "Change one line, different brain"

**Edit** `agents/test_inspector/config.yaml` — change `harness: codex` to `harness: claude-sdk` and `model: gpt-5.4` to `model: claude-sonnet-4-6`.

**Re-run:** `omnigent run examples/harness_portability/ --no-session`

**Same prompt:** `Inspect https://github.com/pallets/flask`

**Say:** "Same supervisor. Same prompt. Same guardrails. I swapped the test inspector from Codex to Claude — one line. The report covers the same four categories with the same structure. The workflow is defined in the config, not in the harness."

---

### Act 5: The Guardrails (1.5 min) — "Layered governance across harnesses"

**Show** the `guardrails:` blocks in both `config.yaml` and one sub-agent config.

**Say:** "Two layers of governance. The supervisor has a $5 session-wide cost cap. Each sub-agent has its own $5 cost cap and a 250 tool-call limit — so no single inspector can run away. The PolicyEngine runs in the Omnigent runner, not in the harness. These policies fire identically on Claude, GPT, Pi, and Hermes."

---

### Timing Summary

| Act | Duration | Focus |
|-----|----------|-------|
| 1. The YAML | 1.5 min | Supervisor + sub-agent configs, four harness assignments |
| 2. Run It | 3 min | Inspect a real repo, watch cross-harness delegation |
| 3. The Report | 1 min | Assembled health report with grades from all inspectors |
| 4. The Swap | 2 min | Change one sub-agent's harness, same result |
| 5. Guardrails | 1.5 min | Layered cost governance across harnesses |
| **Total** | **9 min** | |

---

## Architecture

| Agent | Role | Harness | Model |
|---|---|---|---|
| **Supervisor** | Clone repo, dispatch inspectors, assemble report | `claude-sdk` | `claude-sonnet-4-6` |
| **`structure_inspector`** | Project Structure & Documentation | `claude-sdk` | `claude-sonnet-4-6` |
| **`test_inspector`** | Test Coverage & CI | `codex` | `gpt-5.4` |
| **`dependency_inspector`** | Dependency Health | `pi` | `claude-sonnet-4-6` |
| **`security_inspector`** | Code Quality & Security | `hermes` | `claude-sonnet-4-6` |

One supervisor, four inspectors. Each inspector's harness is set in its own `config.yaml` and can be swapped independently.

### Request flow

```
1. User provides a GitHub repository URL
2. Supervisor clones the repo to /tmp/omnigent_inspect/<repo_name>
3. Supervisor dispatches four inspectors with the cloned repo path:
   a. structure_inspector (Claude SDK) → structure & docs
   b. test_inspector (Codex)           → tests & CI
   c. dependency_inspector (Pi)        → dependencies
   d. security_inspector (Hermes)      → code quality & security
4. Each inspector analyzes its category and reports findings
5. Supervisor collects findings, assigns letter grades, computes overall score
6. Supervisor writes health_report.md and prints the full report
```

---

## Guardrails

### Supervisor

| Policy | Scope | Limit |
|---|---|---|
| `cost_guard` | Per session | ASK at $1.00, downgrade gate at $5.00 |

### Sub-agents (each)

| Policy | Scope | Limit |
|---|---|---|
| `cost_guard` | Per invocation | ASK at $1.00, downgrade gate at $5.00 |
| `tool_call_limit` | Per invocation | 250 tool calls max |

The cost guard **never hard-terminates a session**. It works in two phases:

1. **ASK threshold** (`ask_thresholds_usd`) — the agent pauses and asks for approval when spend crosses the checkpoint. Approve to continue, deny to stop.
2. **Downgrade gate** (`max_cost_usd`) — when spend reaches the limit, the policy asks the user to switch to a cheaper model (via `/model`). Once switched, the session continues. The budget resets its gate — it's a model-downgrade prompt, not a session kill.

The tool call limit on each sub-agent prevents runaway inspection loops. The supervisor has no tool call limit — it only makes a handful of calls (clone + dispatch + write report). All policies are harness-agnostic: they evaluate in the Omnigent runner, not in the LLM harness.

### Cost guard behavior

| Scenario | What happens | How to continue |
|---|---|---|
| **ASK threshold** ($1.00) | The agent pauses and asks for approval. | Approve to continue, or deny to stop. |
| **Downgrade gate** ($5.00) | The agent asks you to switch to a cheaper model. | Switch models with `/model`, then continue. |
| **Tool call limit** (sub-agent hits 250) | Further tool calls are denied for that sub-agent. The supervisor can still dispatch other sub-agents. | Start a fresh session, or raise `limit` in the sub-agent's `config.yaml`. |

No session is ever hard-terminated by cost. The user always decides whether to continue.

**Adjusting limits:**

```bash
# Start a fresh session (resets all counters)
omnigent run examples/harness_portability/ --no-session
```

To permanently change when the agent pauses, edit the `guardrails:` block in the relevant `config.yaml`:

- **Fewer pauses** — raise `ask_thresholds_usd` (e.g., `[2.00]` instead of `[1.00]`)
- **More tool calls** — raise `limit` in sub-agent configs (e.g., `500` instead of `250`)
- **Higher downgrade gate** — raise `max_cost_usd` (e.g., `10.0` instead of `5.0`)

---

## Observability (MLflow Tracing)

MLflow tracing captures every agent turn, tool call, and guardrail policy evaluation — stored in a local `mlflow.db` SQLite file and viewable in the MLflow UI at `http://localhost:5000`. Tracing is supported for the **claude-sdk** and **codex** harnesses.

### Enable tracing with skills

Load the setup skills for each supported harness. Each skill is idempotent — safe to run multiple times:

```
/setup-mlflow-tracing-claude     # For claude-sdk harness (supervisor, structure_inspector)
/setup-mlflow-tracing-codex      # For codex harness (test_inspector)
```

Each skill checks/starts the local MLflow tracking server, runs `mlflow autolog` for the harness, configures environment variables, and confirms tracing is active.

### What you see in traces

Once tracing is enabled, open `http://localhost:5000` to see trace trees for each run:

```
harness_portability  (AGENT, claude-sdk)
├── sys_os_shell "git clone ..."  (TOOL)
├── cost_guard  (GUARDRAIL, verdict: ALLOW)
├── structure_inspector  (AGENT, claude-sdk)  ← traced
│   ├── sys_os_shell "find ..."  (TOOL)
│   ├── cost_guard  (GUARDRAIL, verdict: ALLOW)
│   └── tool_call_limit  (GUARDRAIL, verdict: ALLOW)
├── test_inspector  (AGENT, codex)  ← traced
│   └── ...
├── dependency_inspector  (AGENT, pi)
│   └── ...
├── security_inspector  (AGENT, hermes)
│   └── ...
└── sys_os_write "health_report.md"  (TOOL)
```

Each span records the agent name, harness, model, duration, token usage, and policy verdict. The MLflow UI lets you compare runs across different inspections — see which sub-agent used the most tokens, which harness was fastest, and where policy verdicts fired.

### Manual configuration

You can also configure tracing via `.claude/settings.json` instead of using the setup skills:

```json
{
  "env": {
    "MLFLOW_CLAUDE_TRACING_ENABLED": "true",
    "MLFLOW_TRACKING_URI": "http://localhost:5000",
    "MLFLOW_EXPERIMENT_NAME": "harness-portability-traces"
  }
}
```

### Supported harnesses

| Harness | Tracing Support | Setup Skill |
|---|---|---|
| `claude-sdk` | Fully traced | `/setup-mlflow-tracing-claude` |
| `codex` | Fully traced | `/setup-mlflow-tracing-codex` |
| `pi` | Not yet supported | — |
| `hermes` | Not yet supported | — |

---

## Key Concepts

- **Composition**: A supervisor dispatches four specialist sub-agents, each focused on one inspection category. The supervisor clones the repo, delegates, and assembles — it never inspects code itself.
- **Harness portability**: Four different harnesses (Claude SDK, Codex, Pi, Hermes) collaborate in a single session tree. Each sub-agent's harness is set in its own `config.yaml` and can be swapped independently with a one-line edit.
- **Session tree**: The supervisor and all sub-agents share one session — filesystem, policy state, and conversation history flow through the tree. Each sub-agent's cost counter is scoped to its own invocation, while the supervisor's counter spans the full session.
- **Zero tool code**: No `tools/python/` directory. All capabilities come from `os_env` (filesystem and shell access). The agent uses standard CLI tools (find, grep, wc, git) for analysis.
- **Layered governance**: Two tiers of cost control — the supervisor caps the full session, each sub-agent caps its own invocation. The `tool_call_limit` policy on each sub-agent prevents runaway inspection loops. All policies fire identically across harnesses.
- **Tangible output**: The supervisor produces a structured `health_report.md` — not just conversation, but a reusable artifact assembled from four independent inspections.
- **Cross-harness observability**: MLflow tracing captures every call across the session tree — agent turns, tool calls, policy verdicts — stored in a local `mlflow.db` and viewable in the MLflow UI. Enable with `/setup-mlflow-tracing-claude` and `/setup-mlflow-tracing-codex`.
- **Builds on cross-harness coding**: Start with [cross-harness coding](../cross_harness_coding/) to learn two-harness delegation (Codex implements, Claude reviews), then come here to see four harnesses collaborating with layered governance and MLflow tracing.
