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

## Running

```bash
omniagents run examples/yamls/greeter.yaml
omniagents run examples/yamls/researcher.yaml
omniagents run examples/yamls/code_assistant.yaml
omniagents run examples/yamls/supervisor.yaml
omniagents run examples/yamls/simple.yaml
```

---

## Standalone YAML vs. Directory Bundles

| Layout | Use when | Examples |
|---|---|---|
| **Standalone YAML** | No custom tools. Prompt-only agents or agents using builtins like `web_search`. | `greeter.yaml`, `code_assistant.yaml` |
| **Directory bundle** | Custom Python tools in `tools/python/`. The framework auto-discovers `@tool` functions. | [`fema_supervisor/`](../fema_supervisor/), [`greeter/`](../greeter/) |
