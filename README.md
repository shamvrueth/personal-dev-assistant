# Personal Dev Assistant

An AI-powered codebase analysis tool that combines semantic search with agentic reasoning to help you understand, audit, and improve any code project — via a desktop app or CLI.

## Overview

Point the assistant at any local workspace and run natural language–style commands like `explain`, `lint`, `optimize`, or `find`. Under the hood, the assistant:

1. Indexes your codebase with vector embeddings (ChromaDB + SentenceTransformers)
2. Exposes structured code-analysis tools through an MCP (Model Context Protocol) server
3. Feeds those tools to a GPT-4o-mini agent that iteratively reasons about your code
4. Returns findings through a React + Tauri desktop UI or the CLI

## Architecture

```
React/Tauri frontend
        │  HTTP
        ▼
FastAPI server  (api.py, :8000)
        │  spawns
        ▼
MCP server  (mcp_server/server.py, :3000)
        │  tools used by
        ▼
GPT-4o-mini agent
        │  reads
        ▼
ChromaDB vector index  (~/.dev-assistant/chroma_db/)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, MCP SDK |
| Agent | OpenAI GPT-4o-mini |
| Vector search | ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`) |
| Desktop UI | React 19, Tauri 2, Vite |
| HTTP client | Axios |
| Package manager | uv (Python), npm (frontend) |

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — Python package manager
- Node.js 18+ and npm
- [Rust](https://rustup.rs/) — required by Tauri
- An OpenAI API key

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd personal-dev-assistant
cp .env.example .env          # or create .env manually
```

Add your key to `.env`:

```env
OPENAI_API_KEY=sk-...
MCP_WORKSPACE=/path/to/your/project
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

## Running the App

### Desktop app (recommended)

Start the backend first, then the Tauri desktop app in two separate terminals:

```bash
# Terminal 1 — backend
uvicorn api:app --host 127.0.0.1 --port 8000
```

```bash
# Terminal 2 — desktop UI
cd frontend
npm run tauri dev
```

The API server auto-launches the MCP server on port 3000 at startup.

### CLI only

```bash
python cli.py <command> [args]
```

## Commands

| Command | Description |
|---|---|
| `explain` | High-level summary of the project |
| `entry` | Identify execution entry points |
| `find <symbol>` | Locate a symbol's definition and usages |
| `explain-file <path>` | Explain a specific file |
| `explain-flow <path>` | Trace the execution flow of a file |
| `lint [path]` | Detect bugs and code issues |
| `optimize [path]` | Surface performance improvement opportunities |
| `fix [path]` | Generate suggested code fixes |
| `tree [--depth N]` | Print the directory tree |
| `git-summary` | Show recent git context |

## MCP Tools

The MCP server exposes these tools to the agent:

- `read_file` — Read source file contents
- `search_code` — Exact text search across the workspace
- `search_relevant_code` — Semantic similarity search via embeddings
- `find_entry_points` — Detect project entry points
- `summarize_project` — High-level project metadata
- `list_directory` — Directory traversal
- `project_tree` — Structured tree view

## Vector Index

Code files are chunked into 50-line segments with 50% overlap and embedded using `all-MiniLM-L6-v2`. The index is stored per-workspace under `~/.dev-assistant/chroma_db/` and is rebuilt automatically when the workspace changes.

## Project Structure

```
personal-dev-assistant/
├── api.py              # FastAPI server — orchestrates MCP server lifecycle
├── cli.py              # CLI interface and prompt construction
├── embedder.py         # Vector embedding and ChromaDB integration
├── config.py           # Workspace config and git context storage
├── main.py             # Minimal entry point
├── mcp_server/
│   ├── server.py       # MCP tool definitions and semantic search
│   ├── system_prompt.py
│   └── raw_signal.py
├── mcp_client/
│   └── client.py       # MCP HTTP client
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/ # Terminal, Workspace, Vector, PerformanceChart, Command
│   └── src-tauri/      # Tauri/Rust shell
├── pyproject.toml
└── .env
```

