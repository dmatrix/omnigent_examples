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
databricks auth login
omniagents run examples/greeter/
```

---

## Run Locally (Non-Databricks)

```bash
mv ~/.omniagents/config.yaml ~/.omniagents/config.yaml.bak
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
omniagents run examples/greeter/ --model claude-sonnet-4-6 --harness claude-sdk --server ""
```

Restore when done:

```bash
mv ~/.omniagents/config.yaml.bak ~/.omniagents/config.yaml
```
