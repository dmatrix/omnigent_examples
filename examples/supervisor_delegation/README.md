# Supervisor Delegation

**Same-harness sub-agent delegation — a supervisor dispatches coding tasks to an implementation sub-agent.**

---

## Overview

This example demonstrates Omnigent's sub-agent delegation pattern using a single harness. A supervisor agent breaks down user requests and delegates all implementation work to an `impl_worker` sub-agent. Both run on `claude-sdk`.

For cross-harness delegation (different LLM providers per sub-agent), see [`cross_harness_coding/`](../cross_harness_coding/).

---

## Agents

| Agent | File | Description |
|---|---|---|
| **Coding Supervisor** | `supervisor.yaml` | Delegates coding tasks to an implementation sub-agent |

---

## Run on Databricks

Override the model to route through Databricks AI Gateway:

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/supervisor_delegation/supervisor.yaml --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

---

## Run Locally

```bash
# One-time setup
omnigent setup

# Run the supervisor
omnigent run examples/supervisor_delegation/supervisor.yaml

# Override model at the command line
omnigent run examples/supervisor_delegation/supervisor.yaml --model gpt-4o --harness openai-agents
```
