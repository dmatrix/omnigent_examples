# OmniAgent Harness

**YAML-defined AI agents for the OmniAgent CLI -- from single-tool assistants to multi-tool disaster response agents and secure code assistants.**

![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Anthropic-6B4FBB)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

---

## Overview

This repository contains example agent configurations for the [OmniAgent](https://github.com/databricks/omniagent) CLI. Each example defines an AI agent in YAML -- specifying the executor, system prompt, and tools. Three flagship examples demonstrate different patterns:

1. **[Telco Customer Agent](examples/telco_customer_agent/)** -- multi-tool customer data agent with PII/financial policy labels
2. **[Secure Code Assistant](examples/secure_code_assistant/)** -- information flow control (blocks web search after code read, blocks file writes after web 
3. **[FEMA Disaster Agent](examples/fema_supervisor/)** -- multi-tool routing (text-to-SQL + semantic policy search)
4. **[MLflow Docs RAG Agent](examples/rag_mlflow_docs/)** -- self-building RAG pipeline (embeds documents, then searches them)
---

## Get Started

### Prerequisites

- Python 3.12+
- The `omnigent` CLI installed (`pip install omnigent` or editable from `agent-framework`)
- `OPENAI_API_KEY` in a `.env` file at the repo root (needed for embeddings in the FEMA and RAG agents)

```bash
echo 'OPENAI_API_KEY="sk-..."' > .env
```

### First-time setup

Run the interactive setup to configure your model credentials:

```bash
omnigent setup
```

This walks you through choosing providers for each harness (Claude, OpenAI, Ollama, etc.) and stores credentials in `~/.omnigent/config.yaml`. View your configuration at any time with `omnigent config list`.

### Set up databases

```bash
python examples/tools/create_fema_db.py    # FEMA agent (80 disaster records)
python examples/tools/create_telco_db.py   # Telco agent (5 tables, 125 records)
# MLflow RAG agent builds its own DB on first query -- no setup needed
```

---

## Run on Databricks

Connect to a Databricks-hosted OmniAgent server. Override the model to route through Databricks AI Gateway:

```bash
# Authenticate with the remote server
omnigent login https://omnigent-<id>.aws.databricksapps.com

# FEMA disaster agent
omnigent run examples/fema_supervisor/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com

# MLflow docs RAG agent
omnigent run examples/rag_mlflow_docs/ --model databricks-gpt-5-5 --server https://omnigent-<id>.aws.databricksapps.com

# Telco customer agent
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
# FEMA -- uses credentials configured in setup
omnigent run examples/fema_supervisor/

# Override model and harness at the command line
omnigent run examples/fema_supervisor/ --model gpt-4o --harness openai-agents

# Anthropic Claude
omnigent run examples/fema_supervisor/ --model claude-sonnet-4-6 --harness claude-sdk

# Telco -- OpenAI
omnigent run examples/telco_customer_agent/ --model gpt-4o --harness openai-agents

# Fresh session (no persistence)
omnigent run examples/telco_customer_agent/ --no-session
```

Each example README has detailed local setup instructions -- see [FEMA](examples/fema_supervisor/), [RAG](examples/rag_mlflow_docs/), [Telco](examples/telco_customer_agent/).

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

## Example Queries

```
What were the top 5 states by federal aid in 2024?
What are the evacuation protocols for hurricanes?
How much aid did California get from wildfires and what safety guidelines apply?
```

Each example README has a full list of queries:
- [FEMA Disaster Agent queries](examples/fema_supervisor/#example-queries)
- [MLflow Docs RAG queries](examples/rag_mlflow_docs/#example-queries)
- [Telco Customer Agent queries](examples/telco_customer_agent/#example-queries)
- [Secure Code Assistant queries](examples/secure_code_assistant/#example-queries)

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

Or override at the command line without editing the YAML:
```bash
omnigent run examples/fema_supervisor/ --model claude-sonnet-4-6 --harness claude-sdk
omnigent run examples/fema_supervisor/ --model gpt-5 --harness openai-agents
```

### Supported models

| Provider | Model | Harness | Additional Auth |
|---|---|---|---|
| **Databricks AI Gateway** | `databricks-claude-sonnet-4-6` | `claude-sdk` | -- (Databricks auth only) |
| | `databricks-claude-opus-4-7` | `claude-sdk` | -- |
| | `databricks-claude-opus-4-8` | `claude-sdk` | -- |
| | `databricks-gpt-5-5` | `openai-agents` | -- |
| | `databricks-gpt-5-4` | `openai-agents` | -- |
| | `databricks-gpt-5-4-mini` | `openai-agents` | -- |
| | `databricks-kimi-k2-6` | `openai-agents` | -- |
| | `databricks-meta-llama-3.3-70b-instruct` | `openai-agents` | -- |
| **Anthropic (direct)** | `claude-sonnet-4-6` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| | `claude-opus-4-7` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| | `claude-haiku-4-5` | `claude-sdk` | `ANTHROPIC_API_KEY` in `.env` |
| **OpenAI (direct)** | `gpt-4o` | `openai-agents` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.3-codex` | `openai-agents` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.4` | `openai-agents` | `OPENAI_API_KEY` in `.env` |
| | `gpt-5.4-mini` | `openai-agents` | `OPENAI_API_KEY` in `.env` |
| **Gateway** | Any model via OpenRouter, LiteLLM, vLLM, Azure | `openai-agents` or `claude-sdk` | Gateway `base_url` + key |
| **Ollama (local)** | `ollama/llama-3` | `openai-agents` | None |

Databricks AI Gateway models require `databricks auth login` and `--server`. Non-Databricks models (Anthropic, OpenAI, Ollama) run fully locally -- see [Run Locally](#run-locally). `OPENAI_API_KEY` is always required regardless of LLM provider (the `search_policies` tool uses it for embeddings).

No Python tool code changes are needed -- the tools are provider-independent.

---

## Architecture

Each flagship agent has its own architecture diagram in its README:

- [FEMA Disaster Agent architecture](examples/fema_supervisor/)
- [MLflow Docs RAG Agent architecture](examples/rag_mlflow_docs/)
- [Telco Customer Agent architecture](examples/telco_customer_agent/)

Reference docs:

- [Local vs Remote modes](docs/local_vs_remote.md) -- how all OmniAgent components (server, runner, harness, Web UI, PolicyEngine) fit together in Databricks-hosted and fully-local deployments
- [Telco agent design doc](examples/telco_customer_agent/design.md) -- policy rationale, database schema, and staged implementation plan

---

## The OmniAgent YAML Pattern

Every agent is defined in a `config.yaml` with three core sections:

```yaml
spec_version: 1
name: fema_supervisor
description: FEMA disaster response agent with SQL and policy search tools.

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
  You are a FEMA disaster response agent. You MUST use your tools to answer
  every question. You are FORBIDDEN from answering from your training data.

  Your tools:
  1. `run_sql` — Queries a LOCAL SQLite database (fema_disaster.db)
  2. `search_policies` — Searches LOCAL FEMA policy documents

  Routing:
  - Data questions → call `run_sql`
  - Policy questions → call `search_policies`
  - Combined questions → call BOTH tools
```

Tools are auto-discovered from `tools/python/` in the agent's directory. Each `.py` file with a `@tool`-decorated function is registered automatically.

### Standalone YAML vs. directory bundles

| Layout | Use when | Examples |
|---|---|---|
| **Standalone YAML** | No custom tools. Prompt-only agents or agents using builtins like `web_search`. | `greeter.yaml`, `code_assistant.yaml` |
| **Directory bundle** | Custom Python tools in `tools/python/`. The framework auto-discovers `@tool` functions. | `fema_supervisor/`, `greeter/` |

---

## All Examples

| Agent | Path | Description |
|---|---|---|
| **FEMA Disaster** | [`examples/fema_supervisor/`](examples/fema_supervisor/) | SQL + policy search (supports Databricks, OpenAI, Claude) |
| **MLflow Docs RAG** | [`examples/rag_mlflow_docs/`](examples/rag_mlflow_docs/) | Self-building RAG over MLflow docs (supports Databricks, OpenAI, Claude) |
| **Secure Code Assistant** | [`examples/secure_code_assistant/`](examples/secure_code_assistant/) | Information flow control — blocks web search after code read, blocks file writes after web search |
| **Telco Customer** | [`examples/telco_customer_agent/`](examples/telco_customer_agent/) | Customer data agent with PII/financial policy labels (supports Databricks, OpenAI, Claude) |
| **Coding Supervisor** | [`examples/yamls/`](examples/yamls/) | Delegates coding tasks to an implementation sub-agent |
| **Researcher** | [`examples/yamls/`](examples/yamls/) | Web search + custom `summarize_topic` tool |
| **Code Assistant** | [`examples/yamls/`](examples/yamls/) | File I/O and shell access |
| **Greeter (tool)** | [`examples/greeter/`](examples/greeter/) | Auto-discovered `greet` tool |
| **Greeter (prompt)** | [`examples/yamls/`](examples/yamls/) | Prompt-only, no tools |
| **Simple Agent** | [`examples/yamls/`](examples/yamls/) | Python coder with research sub-agent |

---

## Project Structure

```
omniagent_harness/
|-- README.md
|-- CLAUDE.md
|-- LICENSE                                  # Apache-2.0
|-- .env                                     # OPENAI_API_KEY (not committed)
|-- pyproject.toml
|-- docs/
|   +-- local_vs_remote.md                   # OmniAgent local vs remote architecture
|-- examples/
|   |-- fema_supervisor/                     # FEMA disaster agent
|   |   |-- README.md
|   |   |-- config.yaml                      #   Agent config with prompt-driven routing
|   |   +-- tools/python/
|   |       |-- run_sql.py                   #   SQLite query tool (auto-discovered)
|   |       +-- search_policies.py           #   Policy search tool (auto-discovered)
|   |-- rag_mlflow_docs/                     # MLflow docs RAG agent
|   |   |-- README.md
|   |   |-- config.yaml
|   |   +-- tools/python/
|   |       |-- build_docs_db.py             #   Builds SQLite DB with docs + embeddings
|   |       +-- search_docs.py               #   Semantic search over embedded docs
|   |-- secure_code_assistant/               # Secure code assistant (information flow policies)
|   |   |-- README.md
|   |   |-- config.yaml                      #   harness: claude-sdk, model: claude-sonnet-4-6
|   |   +-- tools/python/
|   |       |-- read_source.py               #   File reader (triggers has_proprietary_code)
|   |       +-- search_docs.py               #   Doc search stub (triggers has_external_content)
|   |-- telco_customer_agent/                # Telco customer data agent (PII/financial policies)
|   |   |-- README.md
|   |   |-- config.yaml
|   |   |-- design.md                        #   Policy rationale + staged implementation plan
|   |   |-- tools/python/
|   |   |   |-- query_plans.py               #   Public plan/pricing data (no labels)
|   |   |   |-- query_customers.py           #   Customer PII + devices (triggers has_pii)
|   |   |   +-- query_billing.py             #   Billing + subscriptions (triggers has_financial)
|   |   +-- skills/customer-report/
|   |       +-- SKILL.md                     #   On-demand report template with PII redaction
|   |-- greeter/                             # Tool-based greeter
|   |   |-- README.md
|   |   |-- config.yaml
|   |   +-- tools/python/greet.py
|   |-- tools/                               # Shared utilities
|   |   |-- create_fema_db.py                #   FEMA database setup script
|   |   |-- create_telco_db.py               #   Telco database setup script
|   |   |-- data/fema_disaster.db            #   Pre-built FEMA database (80 records)
|   |   |-- data/telco.db                    #   Pre-built telco database (5 tables, 125 records)
|   |   +-- python/                          #   Shared tool library
|   |       |-- greet.py                     #   Greeting tool (used by simple.yaml)
|   |       +-- summarize.py                 #   Summarization tool (used by researcher.yaml)
|   +-- yamls/                               # Standalone YAML agents
|       |-- README.md
|       |-- greeter.yaml, researcher.yaml, code_assistant.yaml,
|       |-- supervisor.yaml, simple.yaml
|       +-- agents/impl_worker/config.yaml
+-- images/
    |-- fema_supervisor_architecture.svg
    |-- rag_mlflow_docs_architecture.svg
    |-- telco_customer_agent_architecture.svg
    |-- omniagent_local_architecture.svg
    +-- omniagent_remote_architecture.svg
```

---

## License

[Apache License 2.0](LICENSE)
