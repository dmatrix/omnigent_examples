# OmniAgents Harness

**YAML-defined AI agents for the OmniAgents CLI -- from single-tool assistants to multi-tool disaster response agents.**

![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Anthropic-6B4FBB)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

---

## Overview

This repository contains example agent configurations for the [OmniAgents](https://github.com/databricks/omniagents) CLI. Each example defines an AI agent in YAML -- specifying the executor, system prompt, and tools. The flagship example is a **FEMA disaster response agent** converted from the [mlflow-genai-tutorials multi-agent supervisor notebook](https://github.com/dmatrix/mlflow-genai-tutorials/blob/main/10_multi_agent_supervisor.ipynb) into the OmniAgents harness format.

All agents use the `databricks-claude-sonnet-4-6` model via the `claude-sdk` harness.

### FEMA Disaster Agent

The FEMA agent (`examples/fema_supervisor/`) has two auto-discovered tools with prompt-driven routing:

- **`run_sql`** -- Executes SQLite queries against a local database (`fema_disaster.db`) containing 80 FEMA disaster records (2020--2025). Uses Python's built-in `sqlite3` -- no external SQL warehouse.

- **`search_policies`** -- Semantic search over 9 FEMA policy documents (evacuation protocols, disaster declarations, aid eligibility, flood/wildfire/hurricane/earthquake/tornado procedures). Uses OpenAI embeddings and cosine similarity. Requires `OPENAI_API_KEY` in a `.env` file at the repo root.

The agent's prompt enforces strict tool usage: data questions go to `run_sql`, policy questions go to `search_policies`, combined questions use both. The agent never falls back to training data.

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- The `omniagents` CLI installed
- Databricks CLI authenticated (`databricks auth login`)

### 2. Set up the FEMA database

```bash
python examples/tools/create_fema_db.py
```

This creates `examples/tools/data/fema_disaster.db` with 80 disaster records.

### 3. Set up the OpenAI API key

Create a `.env` file at the repo root (the `search_policies` tool needs it for embeddings):

```bash
echo 'OPENAI_API_KEY="sk-..."' > .env
```

### 4. Run the agent

```bash
omniagents run examples/fema_supervisor/
```

The CLI opens an interactive REPL in your terminal. A Web UI is also available at the Databricks Apps URL printed at startup (e.g., `https://omnigents-<id>.aws.databricksapps.com`) -- open it in a browser to chat with the agent through a web interface.

### 5. Try these queries

**Data queries** (calls `run_sql`):
```
What were the top 5 states by federal aid in 2024?
How many severity-5 disasters occurred between 2020 and 2025?
Which disaster type affected the most people overall?
```

**Policy queries** (calls `search_policies`):
```
What are the evacuation protocols for hurricanes?
How do I apply for FEMA individual assistance?
What should I do immediately after an earthquake?
```

**Combined queries** (calls both tools):
```
How much aid did California get from wildfires and what safety guidelines apply?
What was the worst flood disaster and what are FEMA's flood response procedures?
Which states got hit hardest by tornadoes and what shelter standards does FEMA require?
```

---

## Using Non-Databricks Providers

By default the agent uses `databricks-claude-sonnet-4-6` via Databricks AI Gateway. To run without any Databricks dependencies, change the `executor` block in `config.yaml`:

**Direct Anthropic API** (requires `ANTHROPIC_API_KEY` in `.env`):
```yaml
executor:
  type: omniagents
  model: anthropic/claude-sonnet-4-6
  config:
    harness: claude-sdk
```

**Direct OpenAI API** (requires `OPENAI_API_KEY` in `.env`):
```yaml
executor:
  type: omniagents
  model: openai/gpt-4o
  config:
    harness: openai-agents
```

**Local model via Ollama** (no API key needed):
```yaml
executor:
  type: omniagents
  model: ollama/llama-3
  config:
    harness: openai-agents
    connection:
      base_url: http://localhost:11434/v1
```

Or override at the command line without editing the YAML:
```bash
omniagents run examples/fema_supervisor/ --model anthropic/claude-sonnet-4-6
omniagents run examples/fema_supervisor/ --model openai/gpt-4o --harness openai-agents
```

| Harness | Provider |
|---|---|
| `claude-sdk` | Anthropic Claude (direct or Databricks) |
| `openai-agents` | OpenAI, Ollama, Groq, DeepSeek, or any OpenAI-compatible API |

No Python tool code changes are needed -- the tools are provider-independent. The `.env` file is still required for `search_policies` embeddings (`OPENAI_API_KEY`), regardless of which LLM provider you choose.

---

## Architecture

![FEMA Supervisor Architecture](images/fema_supervisor_architecture.svg)

### How it works

The FEMA agent is a single agent with two auto-discovered tools in `tools/python/`. The system prompt defines routing rules:

| Query type | Tool called | Example |
|---|---|---|
| Data (statistics, counts, trends) | `run_sql` | "Top 5 states by federal aid in 2024?" |
| Policy (procedures, guidelines) | `search_policies` | "What are the evacuation protocols?" |
| Combined (data + policy) | Both | "California wildfire aid and safety guidelines?" |

### Tools

**`run_sql`** reads from a pre-built SQLite file (`examples/tools/data/fema_disaster.db`). The database has one table:

| Column | Type | Example |
|---|---|---|
| `disaster_id` | TEXT | DR-4001 |
| `year` | INTEGER | 2020-2025 |
| `state` | TEXT | California |
| `disaster_type` | TEXT | Wildfire, Hurricane, Flood, Earthquake, Tornado |
| `severity` | INTEGER | 2-5 |
| `affected_population` | INTEGER | 820000 |
| `federal_aid_amount` | INTEGER | 1800000000 |
| `declaration_date` | TEXT | 2020-08-18 |

**`search_policies`** searches 9 inline FEMA policy documents using OpenAI embeddings (`text-embedding-3-small`) and cosine similarity. The documents cover: evacuation protocols (ICS-300), disaster declarations, aid eligibility, flood response, wildfire safety/management, hurricane preparedness, earthquake response, and tornado safety.

---

## The OmniAgents YAML Pattern

Every agent is defined in a `config.yaml` with three core sections:

```yaml
spec_version: 1
name: fema_supervisor
description: FEMA disaster response agent with SQL and policy search tools.

executor:
  type: omniagents
  model: databricks-claude-sonnet-4-6
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
| **FEMA Disaster** | `examples/fema_supervisor/` | SQL + policy search with prompt-driven routing |
| **Coding Supervisor** | `examples/yamls/supervisor.yaml` | Delegates coding tasks to an implementation sub-agent |
| **Researcher** | `examples/yamls/researcher.yaml` | Web search + custom `summarize_topic` tool |
| **Code Assistant** | `examples/yamls/code_assistant.yaml` | File I/O and shell access |
| **Greeter (tool)** | `examples/greeter/` | Auto-discovered `greet` tool |
| **Greeter (prompt)** | `examples/yamls/greeter.yaml` | Prompt-only, no tools |
| **Simple Agent** | `examples/yamls/simple.yaml` | Python coder with research sub-agent |

---

## Project Structure

```
omniagents_harness/
|-- README.md
|-- CLAUDE.md
|-- LICENSE                                  # Apache-2.0
|-- .env                                     # OPENAI_API_KEY (not committed)
|-- pyproject.toml
|-- examples/
|   |-- fema_supervisor/                     # FEMA disaster agent
|   |   |-- config.yaml                      #   Agent config with prompt-driven routing
|   |   +-- tools/python/
|   |       |-- run_sql.py                   #   SQLite query tool (auto-discovered)
|   |       +-- search_policies.py           #   Policy search tool (auto-discovered)
|   |-- greeter/                             # Tool-based greeter
|   |   |-- config.yaml
|   |   +-- tools/python/greet.py
|   |-- tools/                               # Shared utilities
|   |   |-- create_fema_db.py                #   Database setup script
|   |   |-- data/fema_disaster.db            #   Pre-built SQLite database (80 records)
|   |   +-- python/                          #   Shared tool library
|   |       |-- greet.py, summarize.py, reverse_string.py, ...
|   |       |-- fema_data.py                 #   FEMA record definitions
|   |       +-- policy_docs.py               #   FEMA policy document corpus
|   +-- yamls/                               # Standalone YAML agents
|       |-- greeter.yaml, researcher.yaml, code_assistant.yaml,
|       |-- supervisor.yaml, simple.yaml
|       +-- agents/impl_worker/config.yaml
+-- images/
    +-- fema_supervisor_architecture.svg
```

---

## License

[Apache License 2.0](LICENSE)
