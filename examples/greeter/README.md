# Greeter Agent (Tool-Based)

**Minimal agent demonstrating auto-discovered tools.**

---

## Overview

A simple agent with one auto-discovered `greet` tool in `tools/python/greet.py`. Demonstrates the directory bundle pattern -- the framework finds and registers `@tool`-decorated functions from `tools/python/` automatically.

For a prompt-only version (no tools), see [`yamls/greeter.yaml`](../yamls/).

---

## Get Started

No setup required -- this agent has no database or API key dependencies.

---

## Run on Databricks

Uses `databricks-claude-sonnet-4-6` via Databricks AI Gateway.

```bash
omnigents login https://omnigents-<id>.aws.databricksapps.com
omnigents run examples/greeter/ --server https://omnigents-<id>.aws.databricksapps.com
```

---

## Run Locally (Non-Databricks)

```bash
# One-time setup
omnigents setup

# Run the agent
omnigents run examples/greeter/

# Override model at the command line
omnigents run examples/greeter/ --model gpt-4o --harness openai-agents
```
