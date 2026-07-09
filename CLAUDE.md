# CLAUDE.md

## Project Overview

Example agent configurations for the Omnigent CLI. Flagship examples include a secure code assistant with information flow policies, a telco customer data agent demonstrating session-scoped PII/financial policy labels, a cross-harness coding supervisor, and a harness portability inspector using four LLM providers simultaneously.

## Tech Stack

- **Omnigent CLI** -- runs agents from YAML configs
- **Claude SDK harness** (`harness: claude-sdk`) -- most agents default to `claude-sonnet-4-6` (direct API); cross_harness_coding defaults to `databricks-claude-sonnet-4-6` (Databricks AI Gateway)
- **Python tools** -- `@tool` decorator from `omnigent_client.tools`, auto-discovered from `tools/python/`
- **SQLite** -- telco tools query `examples/tools/data/telco.db`

## Running

```bash
# First-time setup (configure credentials)
omnigent setup

# Set up databases (once)
python examples/tools/create_telco_db.py

# Run locally (auto-spawns background server, uses configured credentials)
omnigent run examples/secure_code_assistant/
omnigent run examples/telco_customer_agent/
omnigent run examples/cross_harness_coding/

# Override model and harness at the command line
omnigent run examples/secure_code_assistant/ --model gpt-5.5 --harness openai-agents
omnigent run examples/secure_code_assistant/ --model claude-sonnet-4-6 --harness claude-sdk

# Run against Databricks-hosted server
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/telco_customer_agent/ --server https://omnigent-<id>.aws.databricksapps.com

# Fresh session (no persistence)
omnigent run examples/telco_customer_agent/ --no-session

# Cross-harness coding (Codex + Claude)
omnigent run examples/cross_harness_coding/

# Harness portability (Code Project Health Inspector — runs on any harness)
omnigent run examples/harness_portability/
omnigent run examples/harness_portability/ --model gpt-5.4 --harness codex
omnigent run examples/harness_portability/ --harness pi
omnigent run examples/harness_portability/ --harness hermes
```

## Key Conventions

### Auto-discovered tools

Tools in `tools/python/` within a directory bundle are auto-discovered. Every `.py` file is imported at load time -- keep module-level imports lightweight. Heavy imports (`pandas`, `numpy`, `openai`) must go inside the function body, not at the top of the file.

### Environment variables

Tool subprocesses do not inherit shell env vars, so API keys must be in a `.env` file at CWD or `~/.env`. For non-Databricks Claude, `ANTHROPIC_API_KEY` must also be exported in the shell.

### Database

The telco tools (`query_plans`, `query_customers`, `query_billing`) read from `examples/tools/data/telco.db`. Rebuild with `python examples/tools/create_telco_db.py`. All tools find the database relative to CWD (with `__file__` as fallback).

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
|-- cross_harness_coding/          # Cross-harness coding (Codex implements, Claude reviews)
|   |-- config.yaml               #   Supervisor (claude-sdk), references sub-agents by name
|   +-- agents/
|       |-- impl_worker/
|       |   +-- config.yaml       #   Codex implementer (harness: codex)
|       +-- review_worker/
|           +-- config.yaml       #   Claude reviewer (harness: claude-sdk)
|-- harness_portability/           # Harness portability (supervisor + 4 inspector sub-agents)
|   |-- config.yaml               #   Supervisor (claude-sdk), dispatches to 4 sub-agents
|   +-- agents/
|       |-- structure_inspector/
|       |   +-- config.yaml       #   Structure & docs (claude-sdk)
|       |-- test_inspector/
|       |   +-- config.yaml       #   Tests & CI (codex)
|       |-- dependency_inspector/
|       |   +-- config.yaml       #   Dependencies (pi)
|       +-- security_inspector/
|           +-- config.yaml       #   Security & quality (hermes)
|-- secure_code_assistant/         # Secure code assistant (information flow policies)
|   |-- config.yaml               #   harness: claude-sdk, model: claude-sonnet-4-6
|   +-- tools/python/
|       |-- read_source.py        #   File reader (triggers has_proprietary_code)
|       +-- search_docs.py        #   Doc search stub (triggers has_external_content)
|-- telco_customer_agent/         # Telco customer data agent (PII/financial policies)
|   |-- config.yaml               #   harness: claude-sdk, model: claude-sonnet-4-6
|   |-- policies/
|   |   +-- bulk_access_guard.py  #   Custom policy: ASKs after 3+ distinct customers
|   |-- tools/python/
|   |   |-- query_plans.py        #   Public plan/pricing data (no labels)
|   |   |-- query_customers.py    #   Customer PII + devices
|   |   +-- query_billing.py      #   Billing + subscriptions (financial data)
|   +-- skills/customer-report/
|       +-- SKILL.md              #   On-demand report template with PII redaction
|-- agent_evaluator/              # Agent evaluator (MLflow + spawn)
|   |-- config.yaml               #   claude-opus-4-8, spawn: true, cost_budget
|   |-- agents/
|   |   +-- sample_target/        #   Built-in PoC target (FAQ agent)
|   |       |-- config.yaml       #     claude-sonnet-4-6, cost_budget
|   |       +-- tools/python/
|   |           +-- knowledge_base.py  #  In-memory FAQ lookup (no deps)
|   |-- tools/python/
|   |   |-- run_agent.py          #   Instructions for sys_session_create dispatch
|   |   |-- collect_traces.py     #   Retrieves MLflow traces
|   |   |-- evaluate_traces.py    #   Runs mlflow.genai.evaluate() with scorers
|   |   +-- check_policies.py     #   Inspects trace spans for policy events
|   +-- skills/eval-report/
|       +-- SKILL.md              #   Graded evaluation report template
|-- tools/
|   |-- create_telco_db.py        # Telco database setup script
|   |-- data/telco.db             # Pre-built telco database (5 tables, 125 records) 
|   +-- python/                   # Shared tool library
```

## Known Issues

- **Module-level heavy imports hang auto-discovery.** The framework imports every `.py` in `tools/python/` at agent load time. Module-level `import pandas` or `import mlflow` blocks indefinitely. Use lazy imports inside function bodies.
- **Tool subprocesses don't inherit shell env vars.** Tools run in isolated subprocesses. Use a `.env` file at the repo root for API keys -- the tool must load it explicitly.
- **Tool subprocesses use temp `__file__` paths.** The agent bundle is copied to a temp directory. Use `os.getcwd()` to find repo-root files (database, `.env`), not `Path(__file__).parent`.
- **GPT-5.5 reasoning models don't work with `openai-agents` harness.** GPT-5.x reasoning models require every `function_call` in conversation history to be paired with its `reasoning` item. The executor sets `reasoning_item_id_policy="omit"`, which breaks this pairing. Error: "function_call was provided without its required reasoning item". Use `claude-sdk` with Claude models, or `gpt-5.5` (non-reasoning) with `openai-agents` instead.
