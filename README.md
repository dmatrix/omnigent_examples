# Omnigent Examples

**YAML-defined custom AI agents for the Omnigent Meta Harness -- from single-tool assistants to multi-tool customer support, secure code assistants, and cross-harness orchestration.**

These examples help you get started with Omnigent. All examples can run locally or with a
Databricks-hosted Omnigent Server.

[![omnigent.ai](https://img.shields.io/badge/omnigent.ai-Visit-00C853)](https://omnigent.ai)
![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Anthropic-6B4FBB)
![Codex](https://img.shields.io/badge/Codex-OpenAI-412991)
![Pi](https://img.shields.io/badge/Pi-Earendil-2E7D32)
![Hermes](https://img.shields.io/badge/Hermes-Nous_Research-B71C1C)
![MLflow](https://img.shields.io/badge/MLflow-Tracing-0194E2?logo=mlflow&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

---

## Overview

This repository contains example agent configurations for the [Omnigent](https://github.com/omnigent) meta-harness. Each example defines a [Custom Omnigent AI agent](https://omnigent.ai/docs/use/custom-agents) in YAML -- specifying the executor, system prompt, contextual and custom policies, skills, and tools. Six examples demonstrate different patterns, each using [session-based contextual policies](https://www.databricks.com/blog/contextual-policies-omnigent-using-session-state-better-govern-ai-agents) and the meta-harness for orchestrating agents and secured execution:

1. **[Content Factory](examples/content_factory/README.md)** -- an agentic software factory across three harnesses: a Claude supervisor pulls a feature from a backlog, a Codex `blog_writer` drafts, a Claude `editor` returns PASS/REVISE/REJECT, a Claude `social_writer` derives short-form copy. Drafting is unattended; publishing and outbound posting stop at a custom stateful `publish_gate`. Scheduling itself is approval-gated too.
2. **[Cross-Harness Coding](examples/cross_harness_coding/README.md)** -- multi-harness delegation (Codex implements, Claude reviews, one shared session)
3. **[Harness Portability](examples/harness_portability/README.md)** -- one supervisor, four inspectors, four harnesses: a Code Project Health Inspector with Claude SDK, Codex, Pi, and Hermes sub-agents, including MLflow tracing of Claude and Codex.
4. **[Secure Code Assistant](examples/secure_code_assistant/README.md)** -- session-based information flow control blocks web search after private code read, blocks file writes after web content reads, and enforces ALLOW, DENY, ASK policy guardrails, and budget control costs at session level.
5. **[Slow-Burn Guard](examples/slow_burn_guard/README.md)** -- a compromised runbook fragments a data-exfiltration goal into individually-benign steps; a single stateful risk-score policy sees the whole session and DENIES the outbound send. Databricks [Omnigent blog](https://www.databricks.com/blog/blocking-slow-burn-attacks-contextual-policies-omnigent) companion example.
6. **[Telco Customer Agent](examples/telco_customer_agent/README.md)** -- multi-tool customer data agent with 9 contextual and session-based policies: PII/financial taint labels, cost budget, PII leak prevention, stateful risk scoring, and a custom bulk access guard

> **Three of the six use custom policy handlers and only run as a local ephemeral session.** `content_factory`, `telco_customer_agent` and `secure_code_assistant` are rejected by a persistent local daemon or a remote server before the session starts. See [Custom policies: local ephemeral only](#custom-policies-local-ephemeral-only).

---

## Get Started

### Prerequisites

- Python 3.12+
- The `omnigent` CLI installed (`pip install omnigent`)
- A `.env` file at the repo root. `ANTHROPIC_API_KEY` is needed for the `claude-sdk` harness and `OPENAI_API_KEY` for the `codex` harness -- several examples mix both, so most setups want both keys.

```bash
cat > .env <<'EOF'
ANTHROPIC_API_KEY="sk-ant-..."
OPENAI_API_KEY="sk-..."
EOF
```

Tool subprocesses do not inherit shell environment variables, so keys must be in a `.env` file at the working directory or `~/.env`. For non-Databricks Claude, `ANTHROPIC_API_KEY` must *also* be exported in your shell.

### First-time setup

Run the interactive setup to configure your model credentials:

```bash
omnigent setup
```

This walks you through choosing providers for each harness (Claude, OpenAI, Ollama, etc.) and stores configurations in `~/.omnigent/config.yaml`. View your configuration at any time with `omnigent config list`.

---

## Run on Databricks

Connect to a Databricks-hosted Omnigent server. Override the model to route through Databricks AI Gateway:

```bash
# Authenticate with the remote server
omnigent login https://omnigent-<id>.aws.databricksapps.com

# Cross-Harness Coding
omnigent run examples/cross_harness_coding/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com

# Harness Portability -- Code Project Health Inspector
omnigent run examples/harness_portability/ --server https://omnigent-<id>.aws.databricksapps.com -p "https://github.com/dmatrix/omnigent_examples"

# Slow-Burn Guard
omnigent run examples/slow_burn_guard/ --model databricks-gpt-5-4 --server https://omnigent-<id>.aws.databricksapps.com
```

Only these three examples run against a remote server. `content_factory`, `telco_customer_agent` and `secure_code_assistant` use custom policy handlers, which a remote server rejects before the session is created -- see [Custom policies: local ephemeral only](#custom-policies-local-ephemeral-only).

The CLI opens an interactive REPL. A Web UI is also available at the Databricks Apps URL.

To avoid repeating `--server`, set it as a default:

```bash
omnigent config set --global server=https://omnigent-<id>.aws.databricksapps.com
```

---

## Run Locally

All example configs default to direct API models (Anthropic or OpenAI). Runs fully on your machine with no Databricks dependency. The CLI auto-spawns a local background server.

### 1. Configure credentials (one-time)

```bash
omnigent setup
```

Choose your providers (Claude subscription, OpenAI API key, Ollama local, etc.). Omnigent auto-detects credentials already in your environment and offers them as defaults.

### 2. Export your API keys

```bash
# Always needed (embeddings use OpenAI regardless of LLM)
export $(grep OPENAI_API_KEY .env | tr -d '"')

# Only needed for Claude models via direct API
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
```

### 3. Run an agent

Three examples use only builtin policies and run with a plain `omnigent run`:

```bash
# Cross-Harness Coding -- Codex implements, Claude reviews
omnigent run examples/cross_harness_coding/

# Harness Portability -- Code Project Health Inspector (4 harnesses)
omnigent run examples/harness_portability/
omnigent run examples/harness_portability/ --no-session -p "https://github.com/dmatrix/omnigent_examples"

# Slow-Burn Guard -- stateful risk score blocks the exfil send (codex harness)
export $(grep OPENAI_API_KEY .env | tr -d '"')
omnigent run examples/slow_burn_guard/
```

The other three use custom policy handlers and need a local ephemeral session:

```bash
# Content Factory -- backlog -> draft -> edit -> social, gated at publish
PYTHONPATH=$(pwd) omnigent run examples/content_factory/ --server local --no-session

# Telco Customer Agent -- PII/financial policy labels
PYTHONPATH=$(pwd) omnigent run examples/telco_customer_agent/ --server local --no-session

# Secure Code Assistant -- information flow policies (no PYTHONPATH needed)
omnigent run examples/secure_code_assistant/ --server local --no-session
```

Each example README has detailed local setup instructions -- see [Content Factory](examples/content_factory/README.md), [Cross-Harness](examples/cross_harness_coding/README.md), [Harness Portability](examples/harness_portability/README.md), [Secure Code Assistant](examples/secure_code_assistant/README.md), [Slow-Burn Guard](examples/slow_burn_guard/README.md), [Telco](examples/telco_customer_agent/README.md).

### Custom policies: local ephemeral only

A `config.yaml` whose policy `function.path` is not in the server's policy registry is rejected **before a session is created**. Two independent checks cause this, and both apply to a persistent local daemon as well as to a remote server:

- **Handler allowlist** -- an uploaded bundle may only use handlers from the policy registry. Note `omnigent.policies.function.make_fixed_action_callable` is a framework path but is *not* registered, so taint/label policies trip this too.
- **Server-side tool files** -- an uploaded bundle may not ship a `tools/python/` file at all, because its module body is imported and executed in-process on the runner at tool discovery.

Only `--no-session` takes the legacy in-process ephemeral path, which trusts a locally authored spec. `--server local` on its own is **not** enough.

Separately, CLI preflight imports each policy's dotted path to validate it, but does **not** add the workspace directory to `sys.path`. An example whose policy lives in the workspace (`examples.<name>.policies...`) therefore needs `PYTHONPATH=$(pwd)`, run from the repo root. Without it you get:

```
Error: ... policy 'publish_gate' references function
'examples.content_factory.policies.publish_gate.publish_gate', which cannot be
resolved from sys.path (ModuleNotFoundError: No module named 'examples').
```

(The `omnigent stop` hint appended to that error is generic text on any run failure, not a diagnosis.)

| Example | Policy handlers | `--no-session` | `PYTHONPATH=$(pwd)` |
|---|---|---|---|
| `cross_harness_coding` | builtins only | not needed | not needed |
| `harness_portability` | builtins only | not needed | not needed |
| `slow_burn_guard` | builtins only | not needed | not needed |
| `secure_code_assistant` | `make_fixed_action_callable` (framework path, unregistered) | **required** | not needed |
| `telco_customer_agent` | `bulk_access_guard` + `make_fixed_action_callable` | **required** | **required** |
| `content_factory` | `publish_gate` | **required** | **required** |

**What ephemeral costs you.** The database, artifacts, schedules and conversation state are per-run. State accumulates *within* one invocation but not across them, so anything depending on durable `session_state` -- including `content_factory`'s publish rules and `telco_customer_agent`'s `bulk_access_guard` counts -- cannot be validated across separate CLI runs this way.

For a persistent or remote deployment, an operator must install the policy module into both the server and runner Python environments, export a `POLICY_REGISTRY` list, add its dotted path to `policy_modules:` in the server config, pre-register the agent as operator-owned, and restart.

### Local Web UI

The Web UI is built into the server. When you run an agent, the CLI auto-spawns a local server on a free port and prints the URL:

```
  Web UI: http://127.0.0.1:6767
  Open in your browser for a visual interface
```

The port is dynamically assigned — use the URL printed in your terminal.

You can also manage the background server directly:

```bash
omnigent server start     # ensure background server is running
omnigent server status    # is the background server running?
omnigent server stop      # stop server and local host daemon
```

---

Each example README has a full list of queries, and most have a `demo.md` walkthrough:
- [Content Factory](examples/content_factory/README.md) -- [the cycle, step by step](examples/content_factory/README.md#the-cycle-step-by-step) and the [walkthrough](examples/content_factory/demo.md)
- [Cross-Harness Coding queries](examples/cross_harness_coding/README.md#example-queries)
- [Harness Portability queries](examples/harness_portability/README.md#example-queries)
- [Secure Code Assistant queries](examples/secure_code_assistant/README.md#example-queries)
- [Slow-Burn Guard walkthrough](examples/slow_burn_guard/README.md#the-attack-step-by-step)
- [Telco Customer Agent queries](examples/telco_customer_agent/README.md#example-queries-to-trigger-policies)

---

## Alternative LLM Providers

By default each agent uses a direct API model (Anthropic or OpenAI). You can swap the LLM provider while keeping the same tools and prompts.

**Note:** When using a Databricks-hosted server (`--server` flag), `databricks auth login` is required. Without `--server`, the CLI runs fully locally -- see [Run Locally](#run-locally) above.

To use a different model, change the `executor` block in `config.yaml`:

**Direct Anthropic API** (requires `ANTHROPIC_API_KEY` in `.env`):
```yaml
executor:
  type: omnigent
  model: claude-sonnet-4-6
  config:
    harness: claude-sdk
```

**Direct OpenAI API** (requires `OPENAI_API_KEY` in `.env`):
```yaml
executor:
  type: omnigent
  model: gpt-5.4
  config:
    harness: openai-agents
```

**Local model via Ollama** (no API key needed):
```yaml
executor:
  type: omnigent
  model: llama3.3
  config:
    harness: openai-agents
    connection:
      base_url: http://localhost:11434/v1
```

**Codex harness** (requires `OPENAI_API_KEY` in `.env`):
```yaml
executor:
  type: omnigent
  model: gpt-5.5
  config:
    harness: codex
```

**Pi harness** (requires Pi CLI: `npm i -g @earendil-works/pi-coding-agent`):
```yaml
executor:
  type: omnigent
  model: claude-sonnet-4-6
  config:
    harness: pi
```

Or override at the command line without editing the YAML:
```bash
omnigent run examples/cross_harness_coding/ --model gpt-5.5 --harness codex
omnigent run examples/harness_portability/ --harness pi
omnigent run examples/slow_burn_guard/ --model claude-sonnet-4-6 --harness claude-sdk

# Custom-policy examples still need their local ephemeral flags
omnigent run examples/secure_code_assistant/ --server local --no-session --model claude-sonnet-4-6 --harness claude-sdk
PYTHONPATH=$(pwd) omnigent run examples/telco_customer_agent/ --server local --no-session --model gpt-5.4 --harness openai-agents
```

### Supported harnesses

Omnigent supports 13 harnesses in direct mode (Omnigent drives the model and tools) plus native-TUI wrappers, and each harness is a one-line config value — swap providers without changing prompts, tools, or policies. See the [Harnesses reference](https://omnigent.ai/docs/build/harnesses) for the full list of harness ids, aliases, and auth requirements.

### Supported models

Omnigent runs models from Anthropic and OpenAI (direct API), Databricks AI Gateway, any OpenAI- or Anthropic-compatible gateway (OpenRouter, LiteLLM, vLLM, Azure), and local Ollama. See the [Models & Credentials reference](https://omnigent.ai/docs/build/models) for the full provider and model list.

> **Databricks models are dynamic.** The `databricks-` prefix maps to serving endpoints in your workspace (e.g., `databricks-claude-sonnet-4-6` → `claude-sonnet-4-6`). Your workspace may serve different endpoints. Use `omnigent models list --server <url>` to see available models.

> **Model family rules.** `claude-sdk` only accepts Claude models. `codex` only accepts GPT models. `antigravity` only accepts Gemini models. All other harnesses (`openai-agents`, `pi`, `hermes`, `goose`, `cursor`, `kimi`, `qwen`, `copilot`) accept any model.

No Python tool code changes are needed -- the tools are provider-independent.

---

## Architecture

Each agent has its own architecture diagram in its README:

- [Content Factory architecture](examples/content_factory/README.md)
- [Cross-Harness Coding architecture](examples/cross_harness_coding/README.md)
- [Harness Portability](examples/harness_portability/README.md)
- [Secure Code Assistant](examples/secure_code_assistant/README.md)
- [Slow-Burn Guard](examples/slow_burn_guard/README.md)
- [Telco Customer Agent architecture](examples/telco_customer_agent/README.md)

Reference docs:

- [Local vs Remote modes](docs/local_vs_remote.md) -- how all Omnigent components (server, runner, harness, Web UI, PolicyEngine) fit together in Databricks-hosted and fully-local deployments
- [Policy reference](docs/policy.md) -- the builtin policy handlers, their arguments, and what each one gates

Most examples also ship a `README_YAML_CONFIG.md` that walks the `config.yaml` block by block.

---

## The Omnigent YAML Pattern

Every agent is defined in a `config.yaml` with three core sections:

```yaml
spec_version: 1
name: secure_code_assistant
description: Coding assistant with information flow policies.

executor:
  type: omnigent
  model: claude-sonnet-4-6
  config:
    harness: claude-sdk

os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none

prompt: |
  You are a secure code assistant. You help developers understand
  codebases, find patterns, search documentation, and navigate projects.

  Your tools:
  1. `read_source` — reads source files in the project
  2. `search_docs` — searches the web for documentation
  3. `web_search` — general web search (builtin)
```

Tools are auto-discovered from `tools/python/` in the agent's directory. Each `.py` file with a `@tool`-decorated function is registered automatically.

### Standalone YAML vs. directory bundles

Every example here is a **directory bundle**: a directory containing `config.yaml`, plus any of `tools/python/`, `policies/`, `skills/`, `agents/` and `images/`. Custom Python tools in `tools/python/` are auto-discovered, and sub-agents are directory bundles of their own under `agents/<name>/`.

| Bundle | Sub-agents | Custom tools | Custom policy | Skills |
|---|---|---|---|---|
| `content_factory/` | 3 (`blog_writer`, `editor`, `social_writer`) | 6 | `publish_gate` | `blog-style` |
| `cross_harness_coding/` | 2 (`impl_worker`, `review_worker`) | -- | -- | -- |
| `harness_portability/` | 4 inspectors | -- | -- | -- |
| `secure_code_assistant/` | -- | 2 | -- | -- |
| `slow_burn_guard/` | -- | 4 | -- | -- |
| `telco_customer_agent/` | -- | 3 | `bulk_access_guard` | `customer-report` |

There is **no shared tool library**. Every tool lives in the `tools/python/` directory of the example that uses it and is auto-discovered from there. `examples/tools/` holds only the telco database and its setup script.

---

## Project Structure

```
omnigent_examples/
|-- README.md
|-- CLAUDE.md
|-- DEVELOPER_EXPERIENCE.md
|-- LICENSE                                  # Apache-2.0
|-- .env                                     # OPENAI_API_KEY / ANTHROPIC_API_KEY (not committed)
|-- pyproject.toml
|-- docs/
|   |-- local_vs_remote.md                   # Omnigent local vs remote architecture
|   +-- policy.md                            # Builtin policy handler reference
|-- examples/
|   |-- content_factory/                     # Agentic content factory (3 harnesses, human publish gate)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- backlog.md                       #   Markdown work queue -- the factory's input
|   |   |-- config.yaml                      #   Supervisor (claude-sdk, databricks-claude-sonnet-4-6)
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   |-- agents/
|   |   |   |-- blog_writer/config.yaml      #   Drafts (codex, databricks-gpt-5-4) + blog-style skill
|   |   |   |-- editor/config.yaml           #   PASS/REVISE/REJECT (claude-sdk) + read_local_file
|   |   |   +-- social_writer/config.yaml    #   X thread + LinkedIn post (claude-sdk)
|   |   |-- policies/
|   |   |   +-- publish_gate.py              #   Custom policy: R1-R4 publish rules
|   |   |-- skills/blog-style/SKILL.md       #   House style for the blog writer
|   |   |-- tools/python/                    #   6 tools, two of them guarded
|   |   |   |-- read_backlog.py              #   Next READY feature + disk-derived dashboard
|   |   |   |-- update_backlog.py            #   Status transitions (PUBLISHED is gated)
|   |   |   |-- save_artifact.py             #   Stage outline/draft/social/cycle log (free)
|   |   |   |-- read_artifact.py             #   Read a staged artifact back (free)
|   |   |   |-- publish_content.py           #   Promote draft to published/ (GUARDED)
|   |   |   +-- post_social.py               #   Outbound post stub (GUARDED)
|   |   |-- tests/                           #   pytest suite for the tools and the gate
|   |   +-- artifacts/                       #   Factory output: outlines, drafts, social, published
|   |-- cross_harness_coding/                # Cross-harness coding (Codex + Claude)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   Supervisor (claude-sdk)
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   +-- agents/
|   |       |-- impl_worker/config.yaml      #   Implementer (codex, databricks-gpt-5-4)
|   |       +-- review_worker/config.yaml    #   Reviewer (claude-sdk)
|   |-- harness_portability/                 # Harness portability (supervisor + 4 inspector sub-agents)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   Supervisor (claude-sdk), dispatches to 4 sub-agents
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   +-- agents/
|   |       |-- structure_inspector/config.yaml   #   Structure & docs (claude-sdk)
|   |       |-- test_inspector/config.yaml        #   Tests & CI (codex, gpt-5.4)
|   |       |-- dependency_inspector/config.yaml  #   Dependencies (pi)
|   |       +-- security_inspector/config.yaml    #   Security & quality (hermes)
|   |-- secure_code_assistant/               # Secure code assistant (information flow policies)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   harness: claude-sdk, model: claude-sonnet-4-6
|   |   |-- images/                          #   Architecture + demo setup diagrams (SVG + PNG)
|   |   +-- tools/python/
|   |       |-- read_source.py               #   File reader (triggers has_proprietary_code)
|   |       +-- search_docs.py               #   Doc search stub (triggers has_external_content)
|   |-- slow_burn_guard/                     # Slow-burn attack demo (single risk-score policy)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   harness: codex, model: gpt-5.5-mini
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   +-- tools/python/
|   |       |-- read_runbook.py              #   Compromised runbook (prompt-injection vector, 0 risk)
|   |       |-- query_customers.py           #   Customer PII read (+30 risk)
|   |       |-- query_billing.py             #   Billing read (+30 risk)
|   |       +-- send_report.py               #   Outbound egress action (guarded, DENIED)
|   |-- telco_customer_agent/                # Telco customer data agent (PII/financial policies)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   harness: claude-sdk, model: claude-sonnet-4-6
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   |-- policies/
|   |   |   +-- bulk_access_guard.py         #   Custom policy: ASKs after 3+ distinct customers
|   |   |-- tools/python/
|   |   |   |-- query_plans.py               #   Public plan/pricing data (no labels)
|   |   |   |-- query_customers.py           #   Customer PII + devices (triggers has_pii)
|   |   |   +-- query_billing.py             #   Billing + subscriptions (triggers has_financial)
|   |   +-- skills/customer-report/
|   |       +-- SKILL.md                     #   On-demand report template with PII redaction
|   +-- tools/                               # Telco database only -- NOT a shared tool library
|       |-- create_telco_db.py               #   Telco database setup script
|       +-- data/telco.db                    #   Pre-built telco database (5 tables, 125 records)
+-- images/                                  # System-wide diagrams and logos only
    |-- omnigent_icon.svg
    |-- omnigent_logo.svg
    |-- omnigent_local_architecture.svg
    |-- omnigent_local_architecture.png
    |-- omnigent_remote_architecture.svg
    +-- omnigent_remote_architecture.png
```

---

## License

[Apache License 2.0](LICENSE)
