# CLAUDE.md

## Project Overview

Example agent configurations for the OmniAgents CLI. The flagship example is a FEMA disaster response agent with text-to-SQL and semantic policy search tools.

## Tech Stack

- **OmniAgents CLI** -- runs agents from YAML configs
- **Claude SDK harness** (`harness: claude-sdk`) -- all agents use `databricks-claude-sonnet-4-6`
- **Python tools** -- `@tool` decorator from `omniagents_client.tools`, auto-discovered from `tools/python/`
- **SQLite** -- `run_sql` tool queries a local file (`examples/tools/data/fema_disaster.db`)
- **OpenAI embeddings** -- `search_policies` tool uses `text-embedding-3-small` for semantic search

## Running

```bash
# Set up the database (once)
python examples/tools/create_fema_db.py

# Run the FEMA agent
omniagents run examples/fema_supervisor/

# Run other agents
omniagents run examples/greeter/
omniagents run examples/yamls/greeter.yaml
```

## Key Conventions

### Auto-discovered tools

Tools in `tools/python/` within a directory bundle are auto-discovered. Every `.py` file is imported at load time -- keep module-level imports lightweight. Heavy imports (`pandas`, `numpy`, `openai`) must go inside the function body, not at the top of the file.

### Environment variables

The `search_policies` tool loads `OPENAI_API_KEY` from a `.env` file at CWD or `~/.env`. The tool subprocess does not inherit shell env vars, so the `.env` file is required.

### Database

The `run_sql` tool reads from `examples/tools/data/fema_disaster.db`. Rebuild with `python examples/tools/create_fema_db.py`. The tool finds the database relative to CWD (with `__file__` as fallback).

### os_env

Agents that need filesystem access declare:

```yaml
os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none
```

## Directory Structure

```
examples/
|-- fema_supervisor/              # FEMA disaster agent
|   |-- config.yaml               #   Prompt-driven routing to run_sql + search_policies
|   +-- tools/python/
|       |-- run_sql.py            #   SQLite query tool (auto-discovered)
|       +-- search_policies.py    #   Semantic search tool (auto-discovered, inline docs)
|-- greeter/                      # Tool-based greeter (auto-discovered greet tool)
|-- tools/
|   |-- create_fema_db.py         # Database setup script
|   |-- data/fema_disaster.db     # Pre-built SQLite database (80 records)
|   +-- python/                   # Shared tool library
+-- yamls/                        # Standalone YAML agents
```

## Known Issues

- **Module-level heavy imports hang auto-discovery.** The framework imports every `.py` in `tools/python/` at agent load time. Module-level `import pandas` or `import mlflow` blocks indefinitely. Use lazy imports inside function bodies.
- **Tool subprocesses don't inherit shell env vars.** Tools run in isolated subprocesses. Use a `.env` file at the repo root for API keys -- the tool must load it explicitly.
- **Tool subprocesses use temp `__file__` paths.** The agent bundle is copied to a temp directory. Use `os.getcwd()` to find repo-root files (database, `.env`), not `Path(__file__).parent`.
