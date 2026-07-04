# Omnigent Examples

**YAML-defined AI agents for the Omnigent Meta Harness -- from single-tool assistants to multi-tool customer support, secure code assistants, and cross-harness orchestration.**

These examples help you get started and learn the nuances of what omnigent offers. Both
versions can run locally or with a Databricks hosted Omnigent Server. 

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

This repository contains example agent configurations for the [Omnigent](https://github.com/omnigent) meta-harness. Each example defines an AI agent in YAML -- specifying the executor, system prompt, and tools. Four flagship examples demonstrate different patterns:

1. **[Secure Code Assistant](examples/secure_code_assistant/)** -- information flow control blocks web search after private code read, blocks file writes after web content reads, and enforces ALLOW, DENY, ASK policy guardrails, and budget control costs at session level. 
2. **[Cross-Harness Coding](examples/cross_harness_coding/)** -- multi-harness delegation (Codex implements, Claude reviews, one shared session)
3. **[Harness Portability](examples/harness_portability/)** -- one supervisor, four inspectors, four harnesses: a Code Project Health Inspector with Claude SDK, Codex, Pi, and Hermes sub-agents
4. **[Telco Customer Agent](examples/telco_customer_agent/)** -- multi-tool customer data agent with PII/financial policy labels and control
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

### Set up databases

```bash
python examples/tools/create_telco_db.py   # Telco agent (5 tables, 125 records)
```

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

# Telco Customer Agent -- PII/financial policy labels
omnigent run examples/telco_customer_agent/
omnigent run examples/telco_customer_agent/ --model gpt-5.5 --harness openai-agents
```

Each example README has detailed local setup instructions -- see [Secure Code Assistant](examples/secure_code_assistant/), [Cross-Harness](examples/cross_harness_coding/), [Harness Portability](examples/harness_portability/), [Telco](examples/telco_customer_agent/).

### Local Web UI

The Web UI is built into the server. Start the server and register your machine as a host:

```bash
# Start the server in the background (serves Web UI at http://localhost:8000)
omnigent server start

# Register this machine as a host (separate terminal)
omnigent host

# Open http://localhost:8000/
```

### Manage the background server

```bash
omnigent server status    # is the background server running?
omnigent server stop      # stop server and local host daemon
```

---

Each example README has a full list of queries:
- [Secure Code Assistant queries](examples/secure_code_assistant/#example-queries)
- [Cross-Harness Coding queries](examples/cross_harness_coding/#example-queries)
- [Harness Portability queries](examples/harness_portability/#example-queries)
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
  model: gpt-5
  config:
    harness: openai-agents
```

**Local model via Ollama** (no API key needed):
```yaml
executor:
  type: omnigent
  model: ollama/llama-3
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
  model: databricks-claude-sonnet-4-6
  config:
    harness: pi
```

Or override at the command line without editing the YAML:
```bash
omnigent run examples/secure_code_assistant/ --model claude-sonnet-4-6 --harness claude-sdk
omnigent run examples/telco_customer_agent/ --model gpt-5 --harness openai-agents
omnigent run examples/cross_harness_coding/ --model gpt-5.5 --harness codex
omnigent run examples/telco_customer_agent/ --harness pi
```

### Supported models

| Provider | Model | Harness | Additional Auth |
|---|---|---|---|
| **Databricks AI Gateway** | `databricks-claude-sonnet-4-6` | `claude-sdk` | -- (Databricks auth only) |
| | `databricks-claude-opus-4-7` | `claude-sdk` | -- |
| | `databricks-claude-opus-4-8` | `claude-sdk` | -- |
| | `databricks-gpt-5-5` | `openai-agents` or `codex` | -- |
| | `databricks-gpt-5-4` | `openai-agents` or `codex` | -- |
| | `databricks-gpt-5-4-mini` | `openai-agents` or `codex` | -- |
| | `databricks-kimi-k2-6` | `openai-agents` | -- |
| | `databricks-meta-llama-3.3-70b-instruct` | `openai-agents` | -- |
| | `databricks-claude-sonnet-4-6` | `pi` | -- |
| **Anthropic (direct)** | `claude-sonnet-4-6` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| | `claude-opus-4-7` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| | `claude-haiku-4-5` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| **OpenAI (direct)** | `gpt-5.5` | `openai-agents` or `codex` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.3-codex` | `openai-agents` or `codex` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.4` | `openai-agents` or `codex` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.4-mini` | `openai-agents` or `codex` | `OPENAI_API_KEY` in `.env` |
| **Gateway** | Any model via OpenRouter, LiteLLM, vLLM, Azure | `openai-agents`, `claude-sdk`, `codex`, or `pi` | Gateway `base_url` + key |
| **Pi** | Claude or OpenAI models via Pi agent | `pi` | Pi CLI (`@earendil-works/pi-coding-agent`) |
| **Ollama (local)** | `ollama/llama-3` | `openai-agents` | None |

Databricks AI Gateway models require `databricks auth login` and `--server`. Non-Databricks models (Anthropic, OpenAI, Ollama) run fully locally -- see [Run Locally](#run-locally).

No Python tool code changes are needed -- the tools are provider-independent.

---

## Architecture

Each flagship agent has its own architecture diagram in its README:

- [Secure Code Assistant](examples/secure_code_assistant/)
- [Cross-Harness Coding architecture](examples/cross_harness_coding/)
- [Harness Portability](examples/harness_portability/)
- [Telco Customer Agent architecture](examples/telco_customer_agent/)
Reference docs:

- [Local vs Remote modes](docs/local_vs_remote.md) -- how all Omnigent components (server, runner, harness, Web UI, PolicyEngine) fit together in Databricks-hosted and fully-local deployments
- [Telco agent design doc](examples/telco_customer_agent/design.md) -- policy rationale, database schema, and staged implementation plan

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

## All Examples

| Agent | Path | Description |
|---|---|---|
| **Secure Code Assistant** | [`examples/secure_code_assistant/`](examples/secure_code_assistant/) | Information flow control — blocks web search after code read, blocks file writes after web search |
| **Cross-Harness Coding** | [`examples/cross_harness_coding/`](examples/cross_harness_coding/) | Multi-harness delegation — Codex implements, Claude reviews, one shared session |
| **Harness Portability** | [`examples/harness_portability/`](examples/harness_portability/) | One supervisor, four inspectors — Code Project Health Inspector (Claude SDK, Codex, Pi, Hermes sub-agents) |
| **Telco Customer** | [`examples/telco_customer_agent/`](examples/telco_customer_agent/) | Customer data agent with PII/financial policy labels (supports Databricks, OpenAI, Claude) |

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
|   |-- telco_customer_agent/                # Telco customer data agent (PII/financial policies)
|   |   |-- README.md
|   |   |-- config.yaml
|   |   |-- design.md                        #   Policy rationale + staged implementation plan
|   |   |-- images/                          #   Architecture diagram (SVG + PNG)
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
