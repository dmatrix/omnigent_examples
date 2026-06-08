# Standalone YAML Agents

**Prompt-only and builtin-tool agents defined as single YAML files.**

---

## Overview

These agents demonstrate the standalone YAML pattern -- no `tools/python/` directory, just a single `.yaml` file. They use either no tools (prompt-only) or builtin tools like `web_search`.

---

## Agents

| Agent | File | Description |
|---|---|---|
| **Greeter** | `greeter.yaml` | Prompt-only greeter, no tools |
| **Researcher** | `researcher.yaml` | Web search + custom `summarize_topic` tool |
| **Code Assistant** | `code_assistant.yaml` | File I/O and shell access |
| **Coding Supervisor** | `supervisor.yaml` | Delegates coding tasks to an implementation sub-agent |
| **Simple Agent** | `simple.yaml` | Python coder with research sub-agent |

---

## Get Started

No setup required -- these agents have no database or API key dependencies (except `researcher.yaml` which uses `web_search`).

---

## Run on Databricks

All YAML agents default to `databricks-claude-sonnet-4-6` via Databricks AI Gateway.

```bash
databricks auth login
omniagents run examples/yamls/greeter.yaml
omniagents run examples/yamls/researcher.yaml
omniagents run examples/yamls/code_assistant.yaml
omniagents run examples/yamls/supervisor.yaml
omniagents run examples/yamls/simple.yaml
```

---

## Run Locally (Non-Databricks)

```bash
mv ~/.omniagents/config.yaml ~/.omniagents/config.yaml.bak
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')

omniagents run examples/yamls/greeter.yaml --model claude-sonnet-4-6 --harness claude-sdk --server ""
omniagents run examples/yamls/researcher.yaml --model claude-sonnet-4-6 --harness claude-sdk --server ""
omniagents run examples/yamls/code_assistant.yaml --model claude-sonnet-4-6 --harness claude-sdk --server ""
omniagents run examples/yamls/supervisor.yaml --model claude-sonnet-4-6 --harness claude-sdk --server ""
omniagents run examples/yamls/simple.yaml --model claude-sonnet-4-6 --harness claude-sdk --server ""
```

Restore when done:

```bash
mv ~/.omniagents/config.yaml.bak ~/.omniagents/config.yaml
```

---

## Standalone YAML vs. Directory Bundles

| Layout | Use when | Examples |
|---|---|---|
| **Standalone YAML** | No custom tools. Prompt-only agents or agents using builtins like `web_search`. | `greeter.yaml`, `code_assistant.yaml` |
| **Directory bundle** | Custom Python tools in `tools/python/`. The framework auto-discovers `@tool` functions. | [`fema_supervisor/`](../fema_supervisor/), [`greeter/`](../greeter/) |
