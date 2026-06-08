# OmniAgents: Local vs Remote — All Components Explained

## The 5 Components

| Component | Role | Source File | Framework |
|-----------|------|-------------|-----------|
| **AP Server** | Agent registry, conversation persistence, session/label state, policy orchestration, sub-agent dispatch, runner tunnel routing | `omniagents/server/app.py` | FastAPI + Uvicorn |
| **Runner** | Spawns and manages harness subprocesses, resolves tool calls (priorities 1-5), manages OS environments/sandboxes, streams SSE events to server | `omniagents/runner/app.py` | FastAPI |
| **Harness** | Drives the LLM-tool loop for one SDK — translates SDK events into standard SSE format, per-conversation in-memory state | `omniagents/inner/*_harness.py` | FastAPI wrappers |
| **Web UI (ap-web)** | Browser-based chat interface with terminal emulation (xterm.js) and code editor (Monaco), connects to server via HTTP/SSE | `ap-web/` | React 19 + Vite |
| **PolicyEngine** | Per-session policy evaluation — checks labels, enforces ALLOW/DENY/ASK verdicts, persists labels to `conversation_labels` table | `omniagents/runtime/policies/engine.py` | Python class (in runner) |

### Available Harnesses

| Harness | File | LLM |
|---------|------|-----|
| `claude-sdk` | `claude_sdk_harness.py` | Claude (Anthropic / Databricks) |
| `openai-agents` | `openai_agents_sdk_harness.py` | GPT (OpenAI / Databricks) |
| `codex` | `codex_harness.py` | Codex CLI |
| `pi` | `pi_harness.py` | Perplexity |

### Wire Protocols

| Direction | Protocol | Transport |
|-----------|----------|-----------|
| Client (Browser/REPL) to Server | REST/SSE | HTTPS (remote) or HTTP (local) |
| Server to Runner | REST/SSE subset | WebSocket tunnel (remote) or localhost HTTP (local) |
| Runner to Harness | REST/SSE subset | UDS (Unix Domain Socket) |
| Harness to LLM | SDK-native | Claude SDK / OpenAI Agents SDK |

**UDS (Unix Domain Socket):** A local inter-process communication channel that uses a file path (e.g. `/tmp/omniagents-harness-abc123.sock`) instead of a TCP port. The runner spawns each harness as a subprocess and communicates with it over a UDS — faster and more secure than TCP because the traffic never touches the network stack. It stays entirely within the laptop's kernel.

---

## Remote Mode (Default — Databricks-Hosted)

![Remote Architecture](images/omniagents_remote_architecture.svg)

### How it works

```
Browser ──HTTPS──▶ Databricks App (AP Server + Web UI)
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
| **AP Server** | Databricks App | `omnigents-3272836215725701.aws.databricksapps.com` |
| **Web UI** | Built into the Databricks App | Same URL |
| **Database** | PostgreSQL on Databricks | Managed |
| **Runner** | User's laptop | Outbound WebSocket tunnel to server |
| **PolicyEngine** | Inside Runner (laptop) | In-process |
| **Harness** | User's laptop (subprocess) | UDS to Runner |
| **LLM calls** | Via Databricks AI Gateway | Rate limits, PII detection, content filters |

### How to run

```bash
# One terminal — that's it
omniagents run examples/telco_customer_agent/
```

The CLI reads `~/.omniagents/config.yaml` (profile: `oss`, server: `omnigents-*.databricksapps.com`), connects to the Databricks server, spawns a local runner that opens an outbound WebSocket tunnel, and starts the REPL.

### Key properties

- Session state is durable (DB-backed), resumable from any device
- Web UI is built into the Databricks App — open the app URL in a browser
- LLM calls route through Databricks AI Gateway (rate limits, PII detection, audit logging)
- Runner + harness execute on the laptop — local filesystem access, local tools, local terminals
- Auth via Databricks SSO (profile `oss` in `~/.databrickscfg`)

---

## Fully Local Mode (3 Terminals)

![Local Architecture](images/omniagents_local_architecture.svg)

### How it works

```
Browser ──HTTP──▶ ap-web (localhost:5173) ──proxy──▶ AP Server (localhost:8000)
                                                          │
                                                     localhost
                                                          │
                                                          ▼
Terminal REPL ──────────────────────────────────▶ Runner (localhost) ──▶ Harness ──▶ Direct API
                                                     │
                                                     ▼
                                              Local Tools + Files
```

### What runs where

| Component | Location | Address |
|-----------|----------|---------|
| **AP Server** | Terminal 1 | `localhost:8000` |
| **Web UI (ap-web)** | Terminal 3 | `localhost:5173` (Vite dev server, proxies to :8000) |
| **Database** | Local SQLite | `~/.omniagents/omniagents.db` |
| **Runner** | Terminal 2 | Connects to `localhost:8000` |
| **PolicyEngine** | Inside Runner | In-process |
| **Harness** | Subprocess of Runner | UDS to Runner |
| **LLM calls** | Direct API | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |

### Prerequisites

```bash
# Disable Databricks routing — the global config forces Databricks auth on every harness subprocess
mv ~/.omniagents/config.yaml ~/.omniagents/config.yaml.bak

# Export API keys for direct LLM access
export ANTHROPIC_API_KEY=...   # for claude-sdk harness
export OPENAI_API_KEY=...      # for openai-agents harness, and for search_policies embeddings
```

### How to run

```bash
# Terminal 1: Start local server (auth disabled for local dev)
OMNIAGENTS_AUTH_MULTI_USER=false omniagents server --agent examples/telco_customer_agent/config.yaml
```

```bash
# Terminal 2: Register a runner (connects to the local server)
omniagents connect --server http://localhost:8000
```

```bash
# Terminal 3: Start the web frontend
cd /path/to/agent-framework/ap-web
npm install
OMNIAGENTS_URL=http://localhost:8000 npm run dev
```

Open `http://localhost:5173/` in the browser.

For terminal REPL instead of (or in addition to) the web UI:
```bash
omniagents run examples/telco_customer_agent/ --server http://localhost:8000
```

### Restore Databricks config when done

```bash
mv ~/.omniagents/config.yaml.bak ~/.omniagents/config.yaml
```

### Key properties

- All components run on localhost — no cloud dependency
- No AI Gateway — harness calls the LLM API directly (no rate limits, no PII detection at the gateway layer)
- Session state is local SQLite — single machine, not resumable from other devices
- Auth disabled (`OMNIAGENTS_AUTH_MULTI_USER=false`)
- Must rename `~/.omniagents/config.yaml` — the `profile: oss` setting injects Databricks routing into every harness subprocess

---

## Key Differences

| Aspect | Remote (Databricks) | Fully Local |
|--------|---------------------|-------------|
| **Server** | Databricks App (cloud) | `omniagents server` on localhost:8000 |
| **Web UI** | Built into the Databricks App | `ap-web` npm dev server on localhost:5173 |
| **Runner** | On your laptop (WebSocket tunnel to cloud) | On your laptop (HTTP to localhost) |
| **Harness** | On your laptop (subprocess) | Same — on your laptop |
| **PolicyEngine** | In runner (laptop) | Same — in runner (laptop) |
| **LLM routing** | Via Databricks AI Gateway | Direct API (OpenAI/Anthropic/Ollama) |
| **Auth** | Databricks SSO | Disabled (`OMNIAGENTS_AUTH_MULTI_USER=false`) |
| **Session persistence** | PostgreSQL, resumable anywhere | Local SQLite, single machine |
| **Models** | `databricks-gpt-5-5`, `databricks-claude-sonnet-4-6` | `gpt-4o`, `claude-sonnet-4-6`, Ollama models |
| **Config gotcha** | Uses `~/.omniagents/config.yaml` with `profile: oss` | Must rename/remove that config file |
| **Terminals needed** | 1 (just `omniagents run`) | 3 (server + runner + ap-web) or 2 without web UI |
| **AI Gateway guardrails** | Yes (rate limits, PII detection, content filters) | No — direct API, no gateway layer |

## Known Issue

The Web UI shows agents in the agent list but the "create session" button didn't work locally (as of 2026-06-03). Creating a session via API (`curl -X POST http://localhost:8000/v1/sessions`) succeeded. May need debugging in the ap-web frontend.

## Verification

- Server health: `curl http://localhost:8000/health`
- Session creation: `curl -X POST http://localhost:8000/v1/sessions`
- Web UI: open `http://localhost:5173/` in browser
- Terminal REPL: `omniagents run examples/telco_customer_agent/ --server http://localhost:8000`
