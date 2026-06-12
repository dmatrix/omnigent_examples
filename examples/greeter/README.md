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

Override the model to route through Databricks AI Gateway:

```bash
omnigent login https://omnigent-<id>.aws.databricksapps.com
omnigent run examples/greeter/ --model databricks-claude-sonnet-4-6 --server https://omnigent-<id>.aws.databricksapps.com
```

---

## Run Locally

The default config uses `gpt-5.3-codex` via direct OpenAI API. No Databricks dependency.

```bash
# One-time setup
omnigent setup

# Run the agent (requires OPENAI_API_KEY)
omnigent run examples/greeter/

# Override model at the command line
omnigent run examples/greeter/ --model claude-sonnet-4-6 --harness claude-sdk
```
