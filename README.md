# OmniAgents Harness

**YAML-defined AI agents for the OmniAgents CLI -- from single-tool assistants to multi-agent supervisors.**

![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Anthropic-6B4FBB)
![MLflow](https://img.shields.io/badge/MLflow-Tracing-0194E2?logo=mlflow&logoColor=white)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Supervisor%20Pattern-green)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

---

## Overview

This repository contains example agent configurations for the [OmniAgents](https://github.com/databricks/omniagents) CLI. Each example defines one or more AI agents entirely in YAML -- specifying the executor, system prompt, tools, and (optionally) sub-agents. The configurations range from a zero-tool greeter to a multi-agent FEMA disaster response supervisor with text-to-SQL and semantic search capabilities, all traced with MLflow.

All agents use the `databricks-claude-sonnet-4-6` model via the `claude-sdk` harness.

---

## Architecture: The OmniAgents YAML Pattern

Every agent is defined in a `config.yaml` (or standalone `.yaml` file) with four core sections:

```yaml
spec_version: 1            # optional schema version
name: my_agent
description: What the agent does.

executor:
  type: omniagents
  model: databricks-claude-sonnet-4-6
  config:
    harness: claude-sdk

prompt: |
  System prompt that defines the agent's behavior.

tools:
  # Built-in tools (optional)
  builtins:
    - web_search

  # Custom function tools -- Python callables
  my_tool:
    type: function
    callable: examples.my_agent.tools.python.my_module.my_function

  # Sub-agent tools -- full agents used as tools
  sub_agent:
    type: agent
    description: What this sub-agent does.
    executor: { ... }
    prompt: |
      Sub-agent system prompt.
    tools:
      nested_tool:
        type: function
        callable: examples.my_agent.tools.python.nested.func
```

### Key concepts

| Concept | Description |
|---|---|
| **Executor** | Runtime configuration: model name, harness type (`claude-sdk`), and optional OS environment settings. |
| **Prompt** | System-level instructions that define the agent's role, behavior, and how it should use its tools. |
| **`type: function` tools** | Python functions decorated with `@tool` (from `omniagents_client.tools`), referenced by their dotted import path. |
| **`type: agent` tools** | Full sub-agents defined inline. The parent agent calls them as tools; each sub-agent has its own executor, prompt, and tools. |
| **Auto-discovery** | Directory-based agents (`examples/<agent_dir>/config.yaml`) auto-discover tools from `tools/python/` within the same directory. |
| **`os_env`** | Optional section that gives the agent access to the caller's process, working directory, and shell -- with configurable sandboxing. |

---

## Examples

| Agent | Config Path | Pattern | Description | Key Features |
|---|---|---|---|---|
| **FEMA Supervisor** | `examples/fema_supervisor/config.yaml` | Multi-agent supervisor | Routes disaster queries to data and policy sub-agents | 3-way routing, text-to-SQL, semantic search, MLflow tracing |
| **Coding Supervisor** | `examples/yamls/supervisor.yaml` | Supervisor / worker | Delegates coding tasks to an implementation sub-agent | Task decomposition, code review, unsandboxed OS access |
| **Researcher** | `examples/yamls/researcher.yaml` | Single agent | Summarizes topics using web search and a custom tool | Built-in `web_search`, custom `summarize_topic` function |
| **Code Assistant** | `examples/yamls/code_assistant.yaml` | Single agent | Reads/writes files and runs shell commands | Full OS environment access, no sandbox |
| **Greeter (prompt-only)** | `examples/yamls/greeter.yaml` | Single agent | Greets people using prompt-defined behavior | Zero tools, prompt-only logic |
| **Greeter (tool-based)** | `examples/greeter/config.yaml` | Single agent | Greets people using a custom `greet` tool | Auto-discovered tool from `tools/python/greet.py` |
| **Simple Agent** | `examples/yamls/simple.yaml` | Single agent + sub-agent | Python coder with a research sub-agent | Inline sub-agent definition |
| **FEMA Minimal** | `examples/fema_supervisor_minimal/config.yaml` | Multi-agent supervisor | Minimal FEMA supervisor without custom tools | Sub-agent routing only, no function tools |
| **FEMA Test** | `examples/fema_supervisor_test/config.yaml` | Single agent | Standalone SQL test agent | Self-contained SQL tool, no sub-agents |

---

## FEMA Disaster Supervisor -- Deep Dive

The `fema_supervisor` agent demonstrates a production-style multi-agent architecture: a supervisor that routes user queries to specialized sub-agents, each equipped with their own tools and MLflow-traced execution.

### Architecture

```
                        +---------------------+
                        |   fema_supervisor    |
                        |   (routing agent)    |
                        +----------+----------+
                                   |
                  +----------------+----------------+
                  |                                 |
         +--------v--------+            +-----------v-----------+
         |      genie       |            |  knowledge_assistant  |
         |  (data analyst)  |            |   (policy expert)     |
         +--------+---------+            +-----------+-----------+
                  |                                  |
         +--------v--------+            +-----------v-----------+
         |     run_sql      |            |   search_policies     |
         | (SQLite query)   |            | (embedding search)    |
         +-----------------+            +-----------------------+
```

### Routing Logic

The supervisor classifies each incoming query and routes it to one or both sub-agents:

**Path 1 -- Data queries (genie only)**

User asks about statistics, counts, comparisons, trends, or rankings from FEMA disaster records. The supervisor dispatches to `genie`, which translates the question into a SQLite SELECT statement and executes it via `run_sql`.

> Example: "What were the top 5 states by federal aid in 2024?"

**Path 2 -- Policy queries (knowledge_assistant only)**

User asks about evacuation protocols, safety guidelines, aid eligibility, disaster declaration processes, or response procedures. The supervisor dispatches to `knowledge_assistant`, which searches the policy corpus via `search_policies` and cites documents by name.

> Example: "What are the evacuation protocols for hurricane-prone areas?"

**Path 3 -- Combined queries (both sub-agents)**

User asks a question that requires both data context and policy context. The supervisor calls both sub-agents and synthesizes their responses into a single comprehensive answer.

> Example: "How much aid did Florida receive from hurricanes in 2024, and what is the eligibility process for affected residents?"

### Tools

#### `run_sql` -- Text-to-SQL over FEMA disaster records

- **Callable:** `examples.fema_supervisor.tools.python.run_sql.run_sql`
- **Backend:** In-memory SQLite database loaded with 200 synthetic FEMA disaster records (2020--2025)
- **Data source:** `examples/fema_supervisor/tools/python/fema_data.py` -- generates a DataFrame with columns: `disaster_id`, `year`, `state`, `disaster_type`, `severity`, `affected_population`, `federal_aid_amount`, `declaration_date`
- **MLflow tracing:** Decorated with `@mlflow.trace(name="run_sql", span_type="TOOL")`. Records `sql_query` and `result_rows` as span attributes.

#### `search_policies` -- Semantic search over FEMA policy documents

- **Callable:** `examples.fema_supervisor.tools.python.search_policies.search_policies`
- **Backend:** Cosine similarity search over OpenAI embeddings (`text-embedding-3-small` by default, configurable via `EMBED_MODEL` env var)
- **Corpus:** 11 policy documents defined in `examples/fema_supervisor/tools/python/policy_docs.py`, covering:
  - Evacuation protocols (ICS-300)
  - Disaster declaration process
  - Individual assistance eligibility
  - Federal assistance guidelines
  - Flood response procedures (2 documents)
  - Wildfire safety and management (2 documents)
  - Hurricane preparedness and operational response
  - Earthquake response protocol
  - Tornado safety procedures
- **MLflow tracing:** Decorated with `@mlflow.trace(name="search_policies", span_type="RETRIEVER")`. Records `top_k`, `top_score`, and `retrieved_docs` as span attributes.

### Example Queries

```
# Data query (routed to genie)
"Which disaster type received the most federal aid across all years?"

# Policy query (routed to knowledge_assistant)
"What should I do if a tornado warning is issued for my area?"

# Combined query (routed to both)
"What was the total federal aid for California wildfires, and what wildfire safety guidelines does FEMA recommend?"
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- The `omniagents` CLI installed (`pip install omniagents`)
- `OPENAI_API_KEY` set (required for `search_policies` embedding tool)

### Run an agent

```bash
# Directory-based agent (auto-discovers tools from tools/python/)
omniagents run examples/fema_supervisor/

# Directory-based greeter with custom tool
omniagents run examples/greeter/

# Standalone YAML agent
omniagents run examples/yamls/greeter.yaml
```

---

## Project Structure

```
omniagents_harness/
|-- LICENSE                              # Apache-2.0
|-- mlflow.db                            # MLflow tracking database
|-- examples/
|   |-- __init__.py
|   |-- fema_supervisor/                 # Multi-agent FEMA supervisor
|   |   |-- config.yaml                 #   Supervisor + 2 sub-agents
|   |   |-- __init__.py
|   |   +-- tools/
|   |       |-- __init__.py
|   |       +-- python/
|   |           |-- __init__.py
|   |           |-- run_sql.py           #   Text-to-SQL tool (MLflow traced)
|   |           |-- search_policies.py   #   Semantic search tool (MLflow traced)
|   |           |-- fema_data.py         #   200 synthetic disaster records
|   |           |-- policy_docs.py       #   11 FEMA policy documents
|   |           |-- run_sql_standalone.py #   Self-contained SQL tool (no deps)
|   |           |-- run_sql_simple.py    #   Simplified SQL variant
|   |           +-- hello.py             #   Simple greeting tool
|   |-- fema_supervisor_minimal/         # Minimal FEMA supervisor (no custom tools)
|   |   +-- config.yaml
|   |-- fema_supervisor_test/            # Standalone SQL test agent
|   |   |-- config.yaml
|   |   +-- tools/python/
|   |       |-- fema_data.py
|   |       +-- run_sql_simple.py
|   |-- greeter/                         # Tool-based greeter
|   |   |-- config.yaml
|   |   +-- tools/python/
|   |       +-- greet.py                 #   Auto-discovered greet tool
|   |-- tools/python/                    # Shared tool library
|   |   |-- greet.py
|   |   |-- summarize.py
|   |   |-- reverse_string.py
|   |   |-- word_count.py
|   |   +-- check_syntax.py
|   +-- yamls/                           # Standalone YAML agents
|       |-- greeter.yaml                 #   Prompt-only greeter
|       |-- researcher.yaml             #   Web search + summarize
|       |-- code_assistant.yaml         #   File I/O + shell access
|       |-- supervisor.yaml             #   Coding supervisor/worker
|       |-- simple.yaml                 #   Python coder + sub-agent
|       +-- agents/
|           +-- impl_worker/
|               +-- config.yaml         #   Worker agent for supervisor
```

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
