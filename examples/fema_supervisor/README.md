# FEMA Disaster Agent

**Multi-tool disaster response agent with text-to-SQL and semantic policy search.**

![FEMA Supervisor Architecture](../../images/fema_supervisor_architecture.svg)

---

## Overview

The FEMA agent has two auto-discovered tools with prompt-driven routing:

- **`run_sql`** -- Executes SQLite queries against a local database (`fema_disaster.db`) containing 80 FEMA disaster records (2020--2025). Uses Python's built-in `sqlite3` -- no external SQL warehouse.

- **`search_policies`** -- Semantic search over 9 FEMA policy documents (evacuation protocols, disaster declarations, aid eligibility, flood/wildfire/hurricane/earthquake/tornado procedures). Uses OpenAI embeddings and cosine similarity. Requires `OPENAI_API_KEY` in a `.env` file at the repo root.

The agent's prompt enforces strict tool usage: data questions go to `run_sql`, policy questions go to `search_policies`, combined questions use both. The agent never falls back to training data.

---

## Setup

### 1. Build the database

```bash
python examples/tools/create_fema_db.py
```

This creates `examples/tools/data/fema_disaster.db` with 80 disaster records.

### 2. Set up the OpenAI API key

Create a `.env` file at the repo root (the `search_policies` tool needs it for embeddings):

```bash
echo 'OPENAI_API_KEY="sk-..."' > .env
```

### 3. Run the agent

```bash
omniagents run examples/fema_supervisor/
```

This uses `databricks-claude-sonnet-4-6` via Databricks AI Gateway (requires `databricks auth login`).

---

## Example Queries

**Data queries** (calls `run_sql`):
```
What were the top 5 states by federal aid in 2024?
How many severity-5 disasters occurred between 2020 and 2025?
Which disaster type affected the most people overall?
```

**Policy queries** (calls `search_policies`):
```
What are the evacuation protocols for hurricanes?
How do I apply for FEMA individual assistance?
What should I do immediately after an earthquake?
```

**Combined queries** (calls both tools):
```
How much aid did California get from wildfires and what safety guidelines apply?
What was the worst flood disaster and what are FEMA's flood response procedures?
Which states got hit hardest by tornadoes and what shelter standards does FEMA require?
```

---

## How It Works

The system prompt defines routing rules:

| Query type | Tool called | Example |
|---|---|---|
| Data (statistics, counts, trends) | `run_sql` | "Top 5 states by federal aid in 2024?" |
| Policy (procedures, guidelines) | `search_policies` | "What are the evacuation protocols?" |
| Combined (data + policy) | Both | "California wildfire aid and safety guidelines?" |

---

## Tools

### `run_sql`

Reads from `examples/tools/data/fema_disaster.db`. The database has one table:

| Column | Type | Example |
|---|---|---|
| `disaster_id` | TEXT | DR-4001 |
| `year` | INTEGER | 2020-2025 |
| `state` | TEXT | California |
| `disaster_type` | TEXT | Wildfire, Hurricane, Flood, Earthquake, Tornado |
| `severity` | INTEGER | 2-5 |
| `affected_population` | INTEGER | 820000 |
| `federal_aid_amount` | INTEGER | 1800000000 |
| `declaration_date` | TEXT | 2020-08-18 |

### `search_policies`

Searches 9 inline FEMA policy documents using OpenAI embeddings (`text-embedding-3-small`) and cosine similarity. Documents: evacuation protocols (ICS-300), disaster declarations, aid eligibility, flood response, wildfire safety/management, hurricane preparedness, earthquake response, and tornado safety.

---

## Running Without Databricks

By default the agent uses `databricks-claude-sonnet-4-6` via Databricks AI Gateway. You can run it with any supported provider by overriding the model and harness at the command line.

### Setup

1. **Temporarily disable the Databricks global config** (the global `profile: oss` in `~/.omniagents/config.yaml` forces Databricks routing):

```bash
mv ~/.omniagents/config.yaml ~/.omniagents/config.yaml.bak
```

2. **Export your API keys:**

```bash
# For OpenAI models (also needed for search_policies embeddings regardless of LLM)
export $(grep OPENAI_API_KEY .env | tr -d '"')

# For Claude models
export $(grep ANTHROPIC_API_KEY .env | tr -d '"')
```

3. **Run with a non-Databricks model:**

```bash
# OpenAI
omniagents run examples/fema_supervisor/ --model gpt-4o --harness openai-agents --server ""

# Anthropic Claude
omniagents run examples/fema_supervisor/ --model claude-sonnet-4-6 --harness claude-sdk --server ""
```

4. **Restore Databricks config when done:**

```bash
mv ~/.omniagents/config.yaml.bak ~/.omniagents/config.yaml
```

### Tested Models

| Model | Harness | Status |
|---|---|---|
| `claude-sonnet-4-6` | `claude-sdk` | Works -- accurate SQL and policy search on all query types |
| `gpt-4o` | `openai-agents` | Works -- self-corrects SQL, accurate policy search |
| `gpt-4.1-mini` | `openai-agents` | Works -- occasional SQL column name errors |

See the [top-level README](../../README.md) for the full supported models table and alternative LLM provider configuration.
