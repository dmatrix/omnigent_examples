# Greeter Agent (Tool-Based)

**Minimal agent demonstrating auto-discovered tools.**

---

## Overview

A simple agent with one auto-discovered `greet` tool in `tools/python/greet.py`. Demonstrates the directory bundle pattern -- the framework finds and registers `@tool`-decorated functions from `tools/python/` automatically.

For a prompt-only version (no tools), see [`yamls/greeter.yaml`](../yamls/).

---

## Running

```bash
omniagents run examples/greeter/
```
