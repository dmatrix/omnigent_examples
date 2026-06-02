# CLAUDE.md

## Project Overview

This repository contains example agent configurations for the [OmniAgents](https://github.com/databricks/omniagents) CLI. Each example defines AI agents entirely in YAML -- specifying the executor, system prompt, tools, and optionally sub-agents. Configurations range from a zero-tool greeter to a multi-agent FEMA disaster response supervisor with text-to-SQL and semantic search, all traced with MLflow.

## Tech Stack

- **OmniAgents CLI** (`omniagents`) -- runs agents from YAML configs
- **Claude SDK harness** (`harness: claude-sdk`) -- execution runtime for all agents
- **Databricks-hosted models** -- all agents use `databricks-claude-sonnet-4-6`
- **MLflow tracing** -- tools can be decorated with `@mlflow.trace()` for span-level observability; tracking database at `mlflow.db`
- **Python tools** -- custom functions decorated with `@tool` from `omniagents_client.tools`
- **OpenAI embeddings** -- used by `search_policies` tool (`text-embedding-3-small`, configurable via `EMBED_MODEL` env var)

## Key Patterns

### YAML Agent Configs

Two layout styles exist:

1. **Directory bundles** (preferred for agents with tools): `examples/<agent_dir>/config.yaml` with a `tools/python/` subdirectory. These use `spec_version: 1`.
2. **Single-file YAML**: `examples/yamls/<agent>.yaml` for simple agents or agents whose tools are referenced by full dotted callable paths.

### Tool Types

| Type | YAML Key | Description |
|---|---|---|
| `type: function` | `callable:` | Python function referenced by dotted import path (e.g., `examples.fema_supervisor.tools.python.run_sql.run_sql`) |
| `type: agent` | inline `executor:`, `prompt:`, `tools:` | A full sub-agent used as a tool by a parent agent |
| Auto-discovered | (none -- implicit) | Any `@tool`-decorated function in `tools/python/` within a directory bundle is auto-discovered |
| `builtins` | `builtins: [web_search]` | Built-in tools provided by the harness |

### Executor Config

All agents share the same executor pattern:

```yaml
executor:
  type: omniagents
  model: databricks-claude-sonnet-4-6
  config:
    harness: claude-sdk
```

### OS Environment Access

Agents that need shell/file access declare an `os_env` block:

```yaml
os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none
```

## Running Agents

```bash
# Directory-based agent (auto-discovers tools from tools/python/)
omniagents run examples/fema_supervisor/
omniagents run examples/greeter/

# Standalone YAML agent
omniagents run examples/yamls/greeter.yaml
omniagents run examples/yamls/supervisor.yaml
```

## Important Conventions

- Tools must use the `@tool` decorator from `omniagents_client.tools`.
- `callable:` paths must be importable from the repo root via `importlib.import_module`. Use fully qualified dotted paths like `examples.fema_supervisor.tools.python.run_sql.run_sql`.
- `__init__.py` files are required at every level of the package hierarchy for callable imports to work (see `examples/__init__.py`, `examples/fema_supervisor/__init__.py`, `examples/fema_supervisor/tools/__init__.py`, `examples/fema_supervisor/tools/python/__init__.py`).
- Auto-discovered tools go in `tools/python/` within the agent's directory bundle. Every Python file in that directory with a `@tool`-decorated function is registered automatically.
- `spec_version: 1` agents use directory bundles with `config.yaml` as the entry point.
- MLflow-traced tools stack the `@mlflow.trace()` decorator on top of `@tool` (see `run_sql.py` for the pattern).

## Directory Structure

```
omniagents_harness/
|-- CLAUDE.md
|-- README.md
|-- LICENSE                              # Apache-2.0
|-- mlflow.db                            # MLflow tracking database
|-- examples/
|   |-- __init__.py
|   |-- fema_supervisor/                 # Multi-agent FEMA supervisor
|   |   |-- config.yaml                  #   Supervisor + 2 sub-agents (sql_tool, knowledge_assistant)
|   |   |-- __init__.py
|   |   +-- tools/python/
|   |       |-- __init__.py
|   |       |-- run_sql.py               #   Text-to-SQL tool (MLflow traced)
|   |       |-- search_policies.py       #   Semantic search tool (MLflow traced)
|   |       |-- fema_data.py             #   200 synthetic disaster records
|   |       +-- policy_docs.py           #   11 FEMA policy documents
|   |-- fema_supervisor_minimal/         # Minimal FEMA supervisor variant
|   |   +-- config.yaml
|   |-- fema_supervisor_test/            # Standalone SQL test agent
|   |   |-- config.yaml
|   |   +-- tools/python/
|   |-- greeter/                         # Tool-based greeter (auto-discovered greet tool)
|   |   |-- config.yaml
|   |   +-- tools/python/greet.py
|   |-- tools/python/                    # Shared tool library (greet, summarize, reverse_string, word_count, check_syntax)
|   +-- yamls/                           # Standalone YAML agents
|       |-- greeter.yaml                 #   Prompt-only greeter (no tools)
|       |-- researcher.yaml              #   Web search + summarize_topic
|       |-- code_assistant.yaml          #   File I/O + shell access
|       |-- supervisor.yaml              #   Coding supervisor/worker pair
|       |-- simple.yaml                  #   Python coder with research sub-agent
|       +-- agents/impl_worker/config.yaml
```

## Known Issues

- **Auto-discovered tools with heavy imports may hang.** Tools that import `pandas`, `mlflow`, or other large libraries at module level can cause long delays or hangs during tool registration. Consider lazy imports inside the tool function body when possible.
- **`callable:` paths must be importable from the repo root.** The OmniAgents CLI uses `importlib.import_module` to resolve dotted paths. If packages are missing `__init__.py` files or the path is wrong, the tool silently fails to load.
- **Harness subprocess `sys.path` inheritance.** The `omniagents` CLI adds CWD to `sys.path`, but spawned harness subprocesses may not inherit this. If tool imports fail in a sub-agent, ensure the repo root is on `PYTHONPATH`.
