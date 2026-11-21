# CLAUDE.md

## Project Overview

Example agent configurations for the Omnigent CLI. The examples include a secure code assistant with information flow policies, a telco customer data agent demonstrating session-scoped PII/financial policy labels, a slow-burn guard that blocks a fragmented data-exfiltration attack with a single stateful risk-score policy, a cross-harness coding supervisor, and a harness portability inspector using four LLM providers.

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
# NOTE: only works for examples whose policies are all builtins -- see
# "Custom policies do not run against a remote server" under Known Issues.
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/cross_harness_coding/ --server https://omnigent-<id>.aws.databricksapps.com

# Force a LOCAL server, ignoring any configured remote default.
# Required for content_factory, telco_customer_agent and secure_code_assistant
# once you have run `omnigent login`, because a configured remote becomes the
# default for a plain `omnigent run`. PYTHONPATH is needed so the CLI preflight
# can import the `examples.*` policy modules.
PYTHONPATH=$(pwd) omnigent run examples/content_factory/ --server local --no-session

# Fresh session (no persistence)
omnigent run examples/telco_customer_agent/ --no-session

# Cross-harness coding (Codex + Claude)
omnigent run examples/cross_harness_coding/

# Harness portability (Code Project Health Inspector — runs on any harness)
omnigent run examples/harness_portability/
omnigent run examples/harness_portability/ --model gpt-5.4 --harness codex
omnigent run examples/harness_portability/ --harness pi
omnigent run examples/harness_portability/ --harness hermes

# Slow-burn guard (codex harness + gpt-5.4-mini; needs OPENAI_API_KEY)
omnigent run examples/slow_burn_guard/
omnigent run examples/slow_burn_guard/ --model claude-sonnet-4-6 --harness claude-sdk
```

## Key Conventions

### Auto-discovered tools

Tools in `tools/python/` within a directory bundle are auto-discovered. Every `.py` file is imported at load time -- keep module-level imports lightweight. Heavy imports (`pandas`, `numpy`, `openai`) must go inside the function body, not at the top of the file.

### Environment variables

Tool subprocesses do not inherit shell env vars, so API keys must be in a `.env` file at CWD or `~/.env`. For non-Databricks Claude, `ANTHROPIC_API_KEY` must also be exported in the shell.

### Database

The telco tools (`query_plans`, `query_customers`, `query_billing`) read from `examples/tools/data/telco.db`. Rebuild with `python examples/tools/create_telco_db.py`. All tools find the database relative to CWD (with `__file__` as fallback).

### MLflow Tracing

Omnigent has native OTEL tracing gated by `OMNIGENT_TELEMETRY_ENABLED=true`. When enabled, `telemetry.init()` fires at server startup and exports spans via OTLP. All required env vars are in the repo-root `.env` file:

```bash
set -a; source .env; set +a
```

Key env vars: `OMNIGENT_TELEMETRY_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OMNIGENT_OTEL_CAPTURE_CONTENT`. The evaluation tools also need `MLFLOW_TRACKING_URI` for `mlflow.search_traces()`.

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
|-- slow_burn_guard/              # Slow-burn attack demo (single risk-score policy)
|   |-- config.yaml               #   harness: codex, model: gpt-5.4-mini
|   |-- README.md
|   |-- demo.md
|   +-- tools/python/
|       |-- read_runbook.py       #   Compromised runbook (prompt-injection vector, 0 risk)
|       |-- query_customers.py    #   Customer PII read (+30 risk)
|       |-- query_billing.py      #   Billing read (+30 risk)
|       +-- send_report.py        #   Outbound egress action (guarded_tools, DENIED)
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
+-- tools/
    |-- create_telco_db.py        # Telco database setup script
    +-- data/telco.db             # Pre-built telco database (5 tables, 125 records)
```

There is no shared tool library. Every tool lives in the `tools/python/` directory
of the example that uses it, and is auto-discovered from there.

## Known Issues

- **Custom policies do not run against a remote server.** A remote Omnigent
  server rejects any agent bundle whose policy `function.path` is not in the
  server's policy registry, before a session is created:

  ```
  Error: Could not start a session on https://<host>/api/2.0/omnigent:
  Policy 'publish_gate': handler 'examples.content_factory.policies.publish_gate.publish_gate'
  is not a registered policy handler. Uploaded agent bundles may only use handlers
  from the policy registry; a server admin must add custom handlers via the
  'policy_modules' config.
  ```

  This is deliberate -- it stops an uploaded bundle injecting arbitrary Python.
  There is no way for a bundle to self-register a handler.

  **Affected examples** (3 of 6): `content_factory` (`publish_gate`),
  `telco_customer_agent` (`bulk_access_guard`, plus `make_fixed_action_callable`),
  and `secure_code_assistant` (`make_fixed_action_callable` x4). Note that
  `omnigent.policies.function.make_fixed_action_callable` is a framework path but
  is **not** in the registry, so taint/label policies trip this too.
  **Unaffected:** `cross_harness_coding`, `harness_portability`, `slow_burn_guard`
  -- these use only `omnigent.policies.builtins.*`.

  **`--server local` alone is NOT enough.** Verified by running both forms:

  | invocation | custom handler accepted? |
  |---|---|
  | `--server local --no-session` | yes -- session created |
  | `--server local` (persistent) | **no** -- rejected before session creation |

  Persistent local mode goes through the host daemon (loopback `:6767`), which
  uploads the agent as a session bundle and validates it with
  `enforce_handler_allowlist=True` -- the same check a remote server applies.
  Only `--no-session` takes the legacy in-process ephemeral path, which trusts
  a locally authored spec.

  **Ephemeral smoke run -- the only working one-command route:**

  ```bash
  PYTHONPATH=$(pwd) omnigent run examples/content_factory/ --server local --no-session
  ```

  `PYTHONPATH=$(pwd)` makes the `examples.*` policy module importable; CLI
  preflight does not import from the workspace directory on its own.
  `--no-session` is **required**, not optional.

  **What ephemeral costs you.** The database, artifacts, schedules and
  conversation state are per-run and temporary. State accumulates *within* one
  invocation but not across them, so anything depending on durable
  `session_state` -- including `content_factory`'s own R1/R3/R4 publish rules --
  cannot be validated across separate CLI runs this way.

  **A second, independent wall for uploaded bundles.** A bundle may also not
  ship server-side Python/TypeScript tool files at all:

  ```
  uploaded agent bundle may not ship a server-side Python/TS tool file
  (tool 'post_social' -> 'tools/python/post_social.py'); its module body is
  imported and executed in-process on the runner at tool discovery, so it is
  rejected from untrusted uploads
  ```

  This applies to bundle uploads to a persistent local daemon as well as to a
  remote server, and does **not** apply to the `--no-session` route or to a
  pre-registered trusted operator agent. So passing `--server local` cannot make
  these examples persistent -- two separate checks block it.

  **For a persistent or remote deployment**, an operator must install the policy
  module into both the server and runner Python environments, have it export a
  `POLICY_REGISTRY` list, add its dotted path to `policy_modules:` in the server
  config, pre-register the agent as an operator-owned agent, and restart.

- **`omnigent login` silently changes what a plain `omnigent run` does.** Once a
  remote server is configured it becomes the default target, so
  `omnigent run examples/<dir>/` is no longer a local run. Pass
  `--server local` when you want the local path -- and for the three
  custom-policy examples, `--server local --no-session`, per the previous
  entry. `--server local` on its own is not enough for those.

- **Module-level heavy imports hang auto-discovery.** The framework imports every `.py` in `tools/python/` at agent load time. Module-level `import pandas` or `import mlflow` blocks indefinitely. Use lazy imports inside function bodies.
- **Tool subprocesses don't inherit shell env vars.** Tools run in isolated subprocesses. Use a `.env` file at the repo root for API keys -- the tool must load it explicitly.
- **Tool subprocesses use temp `__file__` paths.** The agent bundle is copied to a temp directory. Use `os.getcwd()` to find repo-root files (database, `.env`), not `Path(__file__).parent`.
- **GPT-5.5 reasoning models don't work with `openai-agents` harness.** GPT-5.x reasoning models require every `function_call` in conversation history to be paired with its `reasoning` item. The executor sets `reasoning_item_id_policy="omit"`, which breaks this pairing. Error: "function_call was provided without its required reasoning item". Use `claude-sdk` with Claude models, or `gpt-5.5` (non-reasoning) with `openai-agents` instead.
