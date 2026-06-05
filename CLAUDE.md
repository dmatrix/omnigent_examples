# CLAUDE.md

## Project Overview

Example agent configurations for the OmniAgents CLI. Flagship examples include a FEMA disaster response agent with text-to-SQL and semantic policy search tools, and a telco customer data agent demonstrating session-scoped PII/financial policy labels.

## Tech Stack

- **OmniAgents CLI** -- runs agents from YAML configs
- **Claude SDK harness** (`harness: claude-sdk`) -- all agents use `databricks-claude-sonnet-4-6`
- **Python tools** -- `@tool` decorator from `omniagents_client.tools`, auto-discovered from `tools/python/`
- **SQLite** -- `run_sql` tool queries `examples/tools/data/fema_disaster.db`; telco tools query `examples/tools/data/telco.db`
- **OpenAI embeddings** -- `search_policies` tool uses `text-embedding-3-small` for semantic search

## Running

```bash
# Set up the database (once)
python examples/tools/create_fema_db.py

# Databricks-hosted Claude (default)
omniagents run examples/fema_supervisor/

# Direct OpenAI (no Databricks) — requires ~/.omniagents/config.yaml renamed
omniagents run examples/fema_supervisor_openai/ --server ""

# Direct Anthropic Claude (no Databricks) — requires ~/.omniagents/config.yaml renamed
omniagents run examples/fema_supervisor_claude/ --server ""

# Telco customer agent (requires telco.db setup)
python examples/tools/create_telco_db.py
omniagents run examples/telco_customer_agent/

# Other agents
omniagents run examples/greeter/
omniagents run examples/yamls/greeter.yaml
```

## Key Conventions

### Auto-discovered tools

Tools in `tools/python/` within a directory bundle are auto-discovered. Every `.py` file is imported at load time -- keep module-level imports lightweight. Heavy imports (`pandas`, `numpy`, `openai`) must go inside the function body, not at the top of the file.

### Environment variables

The `search_policies` tool loads `OPENAI_API_KEY` from a `.env` file at CWD or `~/.env`. The tool subprocess does not inherit shell env vars, so the `.env` file is required. For non-Databricks Claude, `ANTHROPIC_API_KEY` must also be exported in the shell.

### Database

The `run_sql` tool reads from `examples/tools/data/fema_disaster.db`. Rebuild with `python examples/tools/create_fema_db.py`. The telco tools (`query_plans`, `query_customers`, `query_billing`) read from `examples/tools/data/telco.db`. Rebuild with `python examples/tools/create_telco_db.py`. All tools find the database relative to CWD (with `__file__` as fallback).

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
|-- fema_supervisor/              # FEMA agent (Databricks Claude)
|   |-- config.yaml               #   harness: claude-sdk, model: databricks-claude-sonnet-4-6
|   +-- tools/python/
|       |-- run_sql.py            #   SQLite query tool (auto-discovered)
|       +-- search_policies.py    #   Semantic search tool (auto-discovered, inline docs)
|-- fema_supervisor_openai/       # FEMA agent (direct OpenAI)
|   |-- config.yaml               #   harness: openai-agents, model: gpt-4o
|   +-- tools/python/             #   Same tools as fema_supervisor
|-- fema_supervisor_claude/       # FEMA agent (direct Anthropic Claude)
|   |-- config.yaml               #   harness: claude-sdk, model: claude-sonnet-4-6
|   +-- tools/python/             #   Same tools as fema_supervisor
|-- telco_customer_agent/         # Telco customer data agent (PII/financial policies)
|   |-- config.yaml               #   harness: openai-agents, model: databricks-gpt-5-5
|   +-- tools/python/
|       |-- query_plans.py        #   Public plan/pricing data (no labels)
|       |-- query_customers.py    #   Customer PII + devices
|       +-- query_billing.py      #   Billing + subscriptions (financial data)
|-- greeter/                      # Tool-based greeter (auto-discovered greet tool)
|-- tools/
|   |-- create_fema_db.py         # FEMA database setup script
|   |-- create_telco_db.py        # Telco database setup script
|   |-- data/fema_disaster.db     # Pre-built FEMA database (80 records)
|   |-- data/telco.db             # Pre-built telco database (5 tables, 125 records)
|   +-- python/                   # Shared tool library
+-- yamls/                        # Standalone YAML agents
```

## Known Issues

- **Module-level heavy imports hang auto-discovery.** The framework imports every `.py` in `tools/python/` at agent load time. Module-level `import pandas` or `import mlflow` blocks indefinitely. Use lazy imports inside function bodies.
- **Tool subprocesses don't inherit shell env vars.** Tools run in isolated subprocesses. Use a `.env` file at the repo root for API keys -- the tool must load it explicitly.
- **Tool subprocesses use temp `__file__` paths.** The agent bundle is copied to a temp directory. Use `os.getcwd()` to find repo-root files (database, `.env`), not `Path(__file__).parent`.
