# OmniAgent: Local vs Remote — All Components Explained

## The 5 Components

| Component | Role | Source File | Framework |
|-----------|------|-------------|-----------|
| **OmniAgent Server** | Agent registry, conversation persistence, session/label state, policy orchestration, sub-agent dispatch, runner tunnel routing | `omniagent/server/app.py` | FastAPI + Uvicorn |
| **Runner** | Spawns and manages harness subprocesses, resolves tool calls (priorities 1-5), manages OS environments/sandboxes, streams SSE events to server | `omniagent/runner/app.py` | FastAPI |
| **Harness** | Drives the LLM-tool loop for one SDK — translates SDK events into standard SSE format, per-conversation in-memory state | `omniagent/inner/*_harness.py` | FastAPI wrappers |
| **Web UI** | Browser-based chat interface with terminal emulation (xterm.js) and code editor (Monaco), connects to server via HTTP/SSE | Built into the server (or `ap-web/` for development) | React 19 + Vite |
| **PolicyEngine** | Per-session policy evaluation — checks labels, enforces ALLOW/DENY/ASK verdicts, persists labels to `conversation_labels` table | `omniagent/runtime/policies/engine.py` | Python class (in runner) |

### Available Harnesses

| Harness | CLI shorthand | LLM |
|---------|---------------|-----|
| `claude-sdk` | -- | Claude (Anthropic / Databricks), headless |
| `native-claude` | `omnigent claude` | Claude Code TUI (native terminal) |
| `openai-agents` | -- | GPT / OpenAI-compatible (OpenAI / Databricks / Gateway) |
| `codex` | -- | Codex CLI |
| `native-codex` | `omnigent codex` | Codex TUI (native terminal) |
| `pi` | -- | Perplexity |

### Wire Protocols

| Direction | Protocol | Transport |
|-----------|----------|-----------|
| Client (Browser/REPL) to Server | REST/SSE | HTTPS (remote) or HTTP (local) |
| Server to Runner | REST/SSE subset | WebSocket tunnel (remote) or localhost HTTP (local) |
| Runner to Harness | REST/SSE subset | UDS (Unix Domain Socket) |
| Harness to LLM | SDK-native | Claude SDK / OpenAI Agents SDK |

**UDS (Unix Domain Socket):** A local inter-process communication channel that uses a file path (e.g. `/tmp/omniagent-harness-abc123.sock`) instead of a TCP port. The runner spawns each harness as a subprocess and communicates with it over a UDS — faster and more secure than TCP because the traffic never touches the network stack. It stays entirely within the laptop's kernel.

---

## Remote Mode (Default — Databricks-Hosted)

![Remote Architecture](../images/omniagent_remote_architecture.svg)

### How it works

```
Browser ──HTTPS──▶ Databricks App (OmniAgent Server + Web UI)
                          │
                    WebSocket Tunnel
                          │
                          ▼
Terminal REPL ──▶ Runner (laptop) ──▶ Harness (laptop) ──▶ AI Gateway ──▶ Model API
                     │
                     ▼
              Local Tools + Files
```

### What runs where

| Component | Location | Address |
|-----------|----------|---------|
| **OmniAgent Server** | Databricks App | `omnigent-3272836215725701.aws.databricksapps.com` |
| **Web UI** | Built into the Databricks App | Same URL |
| **Database** | PostgreSQL on Databricks | Managed |
| **Runner** | User's laptop | Outbound WebSocket tunnel to server |
| **PolicyEngine** | Inside Runner (laptop) | In-process |
| **Harness** | User's laptop (subprocess) | UDS to Runner |
| **LLM calls** | Via Databricks AI Gateway | Rate limits, PII detection, content filters |

### How to run

```bash
# One terminal — runs the agent REPL and connects to the Databricks server
omnigent run examples/telco_customer_agent/

# Claude Code TUI — registers your laptop as a host so
# the Web UI and mobile clients can co-attach
omnigent claude --host

# Codex TUI
omnigent codex --host

# Register your laptop as a host without starting a session
# (new sessions can then be started from the Web UI)
omnigent host <server-url> --profile oss
```

The CLI reads `~/.omnigent/config.yaml` (profile: `oss`, server: `omnigent-*.databricksapps.com`), connects to the Databricks server, spawns a local runner that opens an outbound WebSocket tunnel, and starts the REPL.

### Session collaboration

```bash
# Co-attach to a teammate's running session (messages execute on THEIR machine)
omnigent attach <session_id>

# Fork a session onto your own machine — continue independently
omnigent run --fork <session_id>
```

### Model defaults with `--profile`

When `--profile oss` is set, each harness auto-picks a Databricks-hosted default:

| Harness | Default model |
|---------|---------------|
| `claude` / `claude-sdk` | `databricks-claude-opus-4-7` |
| `codex` | `databricks-gpt-5-5` |
| `openai-agents` | `databricks-gpt-5-5` |

Override with `--model <name>`, e.g. `--model databricks-claude-sonnet-4-6`. Stick to `databricks-*` aliases when `--profile` is set.

### Key properties

- Session state is durable (DB-backed), resumable from any device
- Web UI is built into the Databricks App — open the app URL in a browser
- Mobile access via Databricks One app (iOS)
- LLM calls route through Databricks AI Gateway (rate limits, PII detection, audit logging)
- Runner + harness execute on the laptop — local filesystem access, local tools, local terminals
- Auth via Databricks SSO (profile `oss` in `~/.databrickscfg`)

---

## Fully Local Mode

![Local Architecture](../images/omniagent_local_architecture.svg)

### How it works

```
Browser ──HTTP──▶ OmniAgent Server + Web UI (localhost:8000)
                          │
                     localhost
                          │
                          ▼
Terminal REPL ──▶ Runner (localhost) ──▶ Harness ──▶ Direct API
                     │
                     ▼
              Local Tools + Files
```

### What runs where

| Component | Location | Address |
|-----------|----------|---------|
| **OmniAgent Server** | localhost | `localhost:8000` |
| **Web UI** | Built into server | `localhost:8000` |
| **Database** | Local SQLite | `~/.omnigent/omnigent.db` |
| **Runner** | localhost | Connects to `localhost:8000` |
| **PolicyEngine** | Inside Runner | In-process |
| **Harness** | Subprocess of Runner | UDS to Runner |
| **LLM calls** | Direct API | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |

### Prerequisites

```bash
# One-time setup — configure model credentials
omnigent setup
```

On first run, Omnigent auto-detects any model credentials already in your environment — an `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, or a `claude` / `codex` CLI you're already logged into — and offers them as defaults.

```bash
# Export API keys for direct LLM access (if not already in environment)
export ANTHROPIC_API_KEY=...   # for claude-sdk harness
export OPENAI_API_KEY=...      # for openai-agents harness, and for search_policies embeddings
```

### How to run

**Simplest — one command starts everything:**

```bash
omnigent
```

This picks up your configured credentials, auto-spawns a local background server, and opens a REPL. The Web UI is available at `http://localhost:8000`.

**Explicit server + host (for browser-only workflow):**

```bash
# Start the server in the background (serves Web UI at http://localhost:8000)
omnigent server start

# Register this machine as a host (separate terminal)
omnigent host

# Open http://localhost:8000 — click New Chat, pick your machine, go
```

**Run a specific agent:**

```bash
omnigent run examples/telco_customer_agent/

# Override model and harness at the command line
omnigent run examples/fema_supervisor/ --model gpt-4o --harness openai-agents
omnigent run examples/fema_supervisor/ --model claude-sonnet-4-6 --harness claude-sdk
```

**Server management:**

```bash
omnigent server status    # is the background server running?
omnigent server stop      # stop just the server
omnigent stop             # stop everything (server + host)
```

### Key properties

- All components run on localhost — no cloud dependency
- No AI Gateway — harness calls the LLM API directly (no rate limits, no PII detection at the gateway layer)
- Session state is local SQLite — single machine, not resumable from other devices
- Credentials managed via `omnigent setup` / `omnigent config`
- Switch models mid-session with the `/model` command

---

## Key Differences

| Aspect | Remote (Databricks) | Fully Local |
|--------|---------------------|-------------|
| **Server** | Databricks App (cloud) | `omnigent server start` on localhost:8000 |
| **Web UI** | Built into the Databricks App | Built into server at localhost:8000 |
| **Runner** | On your laptop (WebSocket tunnel to cloud) | On your laptop (HTTP to localhost) |
| **Harness** | On your laptop (subprocess) | Same — on your laptop |
| **PolicyEngine** | In runner (laptop) | Same — in runner (laptop) |
| **LLM routing** | Via Databricks AI Gateway | Direct API (OpenAI/Anthropic/Gateway/Ollama) |
| **Auth** | `omnigent login <url>` (OIDC/accounts) | `omnigent setup` (local credentials) |
| **Session persistence** | PostgreSQL, resumable anywhere | Local SQLite, single machine |
| **Models** | `databricks-gpt-5-5`, `databricks-claude-sonnet-4-6`, `databricks-claude-opus-4-7` | `gpt-5.4`, `gpt-5.4-mini`, `claude-sonnet-4-6`, Ollama models |
| **Config** | `omnigent config set --global server=<url>` | `omnigent setup` |
| **Terminals needed** | 1 (just `omnigent run --server <url>`) | 1 (`omnigent`, auto-spawns background server) or 2 (`server start` + `host`) |
| **AI Gateway guardrails** | Yes (rate limits, PII detection, content filters) | No — direct API, no gateway layer |
| **Collaboration** | `attach <session_id>`, `run --fork <session_id>` | Same commands, but sessions are local-only |
| **Deploy** | Databricks App | Docker, Render, AWS EC2, or bare `omnigent server` |

---

## Credential Types

Omnigent works with four kinds of credentials (configured via `omnigent setup`):

| | Kind | What it is |
|---|---|---|
| **API key** | First-party vendor key — Anthropic, OpenAI |
| **Subscription** | Claude Pro/Max or ChatGPT plan, via the official `claude` / `codex` CLIs |
| **Gateway** | Any OpenAI- or Anthropic-compatible `base_url` + key — OpenRouter, LiteLLM, Ollama, vLLM, Azure |
| **Databricks** | A Databricks workspace profile |

Defaults are per agent, so a Claude default and a Codex default coexist.

### Gateway examples

| Provider | For | Base URL | Key |
|---|---|---|---|
| **OpenRouter** | Claude Code | `https://openrouter.ai/api` | your OpenRouter key (`sk-or-...`) |
| **OpenRouter** | Codex / OpenAI agents | `https://openrouter.ai/api/v1` | your OpenRouter key |
| **Ollama** (local) | Codex / OpenAI agents | `http://localhost:11434/v1` | any value (Ollama ignores it) |

---

## Session Management

```bash
# Co-attach to a running session (messages execute on the host's machine)
omnigent attach <session_id>

# Fork a session onto your own machine and continue independently
omnigent run --fork <session_id>

# Switch models mid-session (inside the REPL)
/model
```

---

## Multi-User Accounts

By default Omnigent runs single-user, no login needed. To enable multi-user accounts for collaboration:

```bash
OMNIGENT_AUTH_ENABLED=1 omnigent server start
```

With auth on, the first run prints an admin password. Invite teammates via **Admin > Members > Invite** in the Web UI — no email server needed.

### SSO (Google, GitHub, Okta, Microsoft)

Add OIDC configuration to your server environment:

```bash
OMNIGENT_OIDC_ISSUER=https://accounts.google.com   # or github.com / your Okta URL
OMNIGENT_DOMAIN=agents.yourcompany.com
OMNIGENT_OIDC_CLIENT_ID=...
OMNIGENT_OIDC_CLIENT_SECRET=...
```

---

## Self-Hosted Deploy

For a server with a stable URL (accessible from your phone or teammates' machines):

| Target | Setup |
|--------|-------|
| **Docker** | `cd deploy/docker && ./bootstrap.sh && docker compose up -d` |
| **Render** | One-click deploy button in the upstream repo |
| **AWS EC2** | One-command Terraform in `deploy/` |

Then connect your laptop:

```bash
omnigent login https://your-host
omnigent host https://your-host
```

See the upstream [agent-framework `deploy/` directory](https://github.com/databricks-eng/agent-framework/tree/main/deploy) for full instructions.

---

## Verification

- Server health: `curl http://localhost:8000/health`
- Session creation: `curl -X POST http://localhost:8000/v1/sessions`
- Web UI: open `http://localhost:8000/` in browser
- Terminal REPL: `omnigent run examples/telco_customer_agent/`
