# Omnigent Examples

**YAML-defined AI agents for the Omnigent Meta Harness -- from single-tool assistants to multi-tool customer support, secure code assistants, and cross-harness orchestration.**

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

This repository contains example agent configurations for the [Omnigent](https://github.com/omnigent) meta-harness. Each example defines a [Custom Omnigent AI agent](https://omnigent.ai/docs/use/custom-agents) in YAML -- specifying the executor, system prompt, contextual and custom policies, skills, and tools. Five examples demonstrate different patterns, each using [session-based contextual policies](https://www.databricks.com/blog/contextual-policies-omnigent-using-session-state-better-govern-ai-agents) and the meta-harness for orchestrating agents and secured execution:

1. **[Secure Code Assistant](examples/secure_code_assistant/)** -- session-based information flow control blocks web search after private code read, blocks file writes after web content reads, and enforces ALLOW, DENY, ASK policy guardrails, and budget control costs at session level. 
2. **[Cross-Harness Coding](examples/cross_harness_coding/)** -- multi-harness delegation (Codex implements, Claude reviews, one shared session)
3. **[Harness Portability](examples/harness_portability/)** -- one supervisor, four inspectors, four harnesses: a Code Project Health Inspector with Claude SDK, Codex, Pi, and Hermes sub-agents, including MLflow tracing of Claude and Codex.
4. **[Slow-Burn Guard](examples/slow_burn_guard/)** -- a compromised runbook fragments a data-exfiltration goal into individually-benign steps; a single stateful risk-score policy sees the whole session and DENIES the outbound send. Databricks [Omnigent blog](https://www.databricks.com/blog/blocking-slow-burn-attacks-contextual-policies-omnigent) companion example.
5. **[Telco Customer Agent](examples/telco_customer_agent/)** -- multi-tool customer data agent with 9 contextual and session-based policies: PII/financial taint labels, cost budget, PII leak prevention, stateful risk scoring, and a custom bulk access guard
---

## Get Started

### Prerequisites

- Python 3.12+
- The `omnigent` CLI installed (`pip install omnigent`)
- `OPENAI_API_KEY` in a `.env` file at the repo root (needed for the Codex harness)

```bash
echo 'ANTHROPIC_API_KEY="sk-..."' > .env
```

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

# Secure Code Assistant
omnigent run examples/secure_code_assistant/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com

# Cross-Harness Coding
omnigent run examples/cross_harness_coding/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com

# Harness Portability -- Code Project Health Inspector
omnigent run examples/harness_portability/ --server https://omnigent-<id>.aws.databricksapps.com -p "https://github.com/dmatrix/omnigent_examples"

# Slow-Burn Guard
omnigent run examples/slow_burn_guard/ --model databricks-gpt-5-4 --server https://omnigent-<id>.aws.databricksapps.com

# Telco Customer Agent
omnigent run examples/telco_customer_agent/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

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

```bash
# Secure Code Assistant -- information flow policies (Claude)
omnigent run examples/secure_code_assistant/
omnigent run examples/secure_code_assistant/ --model claude-sonnet-4-6 --harness claude-sdk

# Cross-Harness Coding -- Codex implements, Claude reviews
omnigent run examples/cross_harness_coding/

# Harness Portability -- Code Project Health Inspector (4 harnesses)
omnigent run examples/harness_portability/
omnigent run examples/harness_portability/ --no-session -p "https://github.com/dmatrix/omnigent_examples"

# Slow-Burn Guard -- stateful risk score blocks the exfil send (codex harness)
export $(grep OPENAI_API_KEY .env | tr -d '"')
omnigent run examples/slow_burn_guard/

# Telco Customer Agent -- PII/financial policy labels
omnigent run examples/telco_customer_agent/
omnigent run examples/telco_customer_agent/ --model gpt-5.5 --harness openai-agents
```

Each example README has detailed local setup instructions -- see [Secure Code Assistant](examples/secure_code_assistant/), [Cross-Harness](examples/cross_harness_coding/), [Harness Portability](examples/harness_portability/), [Slow-Burn Guard](examples/slow_burn_guard/), [Telco](examples/telco_customer_agent/).

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

Each example README has a full list of queries:
- [Secure Code Assistant queries](examples/secure_code_assistant/#example-queries)
- [Cross-Harness Coding queries](examples/cross_harness_coding/#example-queries)
- [Harness Portability queries](examples/harness_portability/#example-queries)
- [Slow-Burn Guard walkthrough](examples/slow_burn_guard/#the-attack-step-by-step)
- [Telco Customer Agent queries](examples/telco_customer_agent/#example-queries)

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
omnigent run examples/secure_code_assistant/ --model claude-sonnet-4-6 --harness claude-sdk
omnigent run examples/telco_customer_agent/ --model gpt-5.4 --harness openai-agents
omnigent run examples/cross_harness_coding/ --model gpt-5.5 --harness codex
omnigent run examples/telco_customer_agent/ --harness pi
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

- [Secure Code Assistant](examples/secure_code_assistant/)
- [Cross-Harness Coding architecture](examples/cross_harness_coding/)
- [Harness Portability](examples/harness_portability/)
- [Slow-Burn Guard](examples/slow_burn_guard/)
- [Telco Customer Agent architecture](examples/telco_customer_agent/)

Reference docs:

- [Local vs Remote modes](docs/local_vs_remote.md) -- how all Omnigent components (server, runner, harness, Web UI, PolicyEngine) fit together in Databricks-hosted and fully-local deployments

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

| Layout | Use when | Examples |
|---|---|---|
| **Directory bundle** | All examples. Custom Python tools in `tools/python/` are auto-discovered. | `secure_code_assistant/`, `telco_customer_agent/`, `cross_harness_coding/` |

---

## Project Structure

```
omnigent_examples/
|-- README.md
|-- CLAUDE.md
|-- LICENSE                                  # Apache-2.0
|-- .env                                     # OPENAI_API_KEY (not committed)
|-- pyproject.toml
|-- docs/
|   +-- local_vs_remote.md                   # Omnigent local vs remote architecture
|-- examples/
|   |-- cross_harness_coding/                # Cross-harness coding (Codex + Claude)
|   |   |-- README.md
|   |   |-- config.yaml                      #   Supervisor + impl_worker (codex) + review_worker (claude-sdk)
|   |   +-- images/                          #   Architecture diagram (SVG + PNG)
|   |-- harness_portability/                  # Harness portability (supervisor + 4 inspector sub-agents)
|   |   |-- README.md
|   |   |-- README_YAML_CONFIG.md
|   |   |-- config.yaml                      #   Supervisor (claude-sdk), dispatches to 4 sub-agents
|   |   +-- agents/
|   |       |-- structure_inspector/config.yaml   #   Structure & docs (claude-sdk)
|   |       |-- test_inspector/config.yaml        #   Tests & CI (codex)
|   |       |-- dependency_inspector/config.yaml  #   Dependencies (pi)
|   |       +-- security_inspector/config.yaml    #   Security & quality (hermes)
|   |-- secure_code_assistant/               # Secure code assistant (information flow policies)
|   |   |-- README.md
|   |   |-- config.yaml                      #   harness: claude-sdk, model: claude-sonnet-4-6
|   |   |-- images/                          #   Architecture + demo setup diagrams (SVG + PNG)
|   |   +-- tools/python/
|   |       |-- read_source.py               #   File reader (triggers has_proprietary_code)
|   |       +-- search_docs.py               #   Doc search stub (triggers has_external_content)
|   |-- slow_burn_guard/                     # Slow-burn attack demo (single risk-score policy)
|   |   |-- README.md
|   |   |-- demo.md
|   |   |-- config.yaml                      #   harness: codex, model: gpt-5.4-mini
|   |   +-- tools/python/
|   |       |-- read_runbook.py             #   Compromised runbook (prompt-injection vector)
|   |       |-- query_customers.py           #   Customer PII read (+30 risk)
|   |       |-- query_billing.py             #   Billing read (+30 risk)
|   |       +-- send_report.py               #   Outbound egress action (guarded, DENIED)
|   |-- telco_customer_agent/                # Telco customer data agent (PII/financial policies)
|   |   |-- README.md
|   |   |-- config.yaml
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
|   |   |-- policies/
|   |   |   +-- bulk_access_guard.py         #   Custom policy: ASKs after 3+ distinct customers
|   |   |-- tools/python/
|   |   |   |-- query_plans.py               #   Public plan/pricing data (no labels)
|   |   |   |-- query_customers.py           #   Customer PII + devices (triggers has_pii)
|   |   |   +-- query_billing.py             #   Billing + subscriptions (triggers has_financial)
|   |   +-- skills/customer-report/
|   |       +-- SKILL.md                     #   On-demand report template with PII redaction
|   |-- tools/                               # Shared utilities
|   |   |-- create_telco_db.py               #   Telco database setup script
|   |   |-- data/telco.db                    #   Pre-built telco database (5 tables, 125 records)
|   |   +-- python/                          #   Shared tool library
+-- images/                                  # System-wide diagrams only
    |-- omnigent_local_architecture.svg
    |-- omnigent_local_architecture.png
    |-- omnigent_remote_architecture.svg
    +-- omnigent_remote_architecture.png
```

---

## License

[Apache License 2.0](LICENSE)
