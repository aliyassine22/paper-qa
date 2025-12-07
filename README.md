# Research Assistant Multi-Agent System

An AI-powered research assistant that combines a **RAG (Retrieval-Augmented Generation) knowledge base**, **arXiv search**, **paper downloading**, and **PDF report generation** into a unified agent system. Built with LangGraph, FastMCP (Model Context Protocol), and FastAPI.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation & Setup](#installation--setup)
- [File Path Configuration](#file-path-configuration)
- [Running the System](#running-the-system)
- [API Endpoints](#api-endpoints)
- [Agent Workflow](#agent-workflow)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Overview

This system enables users to:

1. **Query a local knowledge base** of research papers using semantic search (RAG)
2. **Search arXiv** for new academic papers on any topic
3. **Download papers** from arXiv and automatically index them into the vector database
4. **Generate PDF reports** from research findings in markdown format
5. **Have multi-turn conversations** with context memory

The system uses the **Model Context Protocol (MCP)** to expose tools that the LangGraph agent can call, creating a modular and extensible architecture.

---

## Features

| Feature | Description |
|---------|-------------|
| **RAG Knowledge Base** | Query indexed research papers with semantic search using ChromaDB |
| **arXiv Integration** | Search arXiv for academic papers with metadata (title, abstract, authors, year) |
| **Auto-Indexing** | Downloaded papers are automatically chunked, embedded, and added to the vector database |
| **Auto-Indexing on Startup** | When the server starts, it checks for new PDFs in the Papers folder and indexes them |
| **PDF Report Generation** | Generate formatted PDF reports from markdown content |
| **Conversation Memory** | Multi-turn conversations with full context retention |
| **RESTful API** | FastAPI backend for easy integration with any frontend |
| **Streamlit Frontend** | Beautiful, animated web interface for interacting with the assistant |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Streamlit Frontend (port 8501)                 │
│                       Frontend/app.py                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               FastAPI Backend (port 8000)                       │
│               Agentic System/main.py                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         LangGraph Agent (ResearchAssistant)             │   │
│   │         - Conversation history                          │   │
│   │         - Tool orchestration via MCP                    │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │ (SSE Connection)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 MCP Server (port 8787)                          │
│                 Tools Server/McpServer.py                       │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐ │
│   │ research_     │ │ search_arxiv  │ │ download_paper        │ │
│   │ paper_probe   │ │               │ │ (auto-indexes to RAG) │ │
│   └───────────────┘ └───────────────┘ └───────────────────────┘ │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │              generate_report (PDF from markdown)          │ │
│   └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ChromaDB Vector Store                        │
│                 Tools Server/RAG SETUP/VectorDB/                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installation & Setup

### Prerequisites

- **Python 3.10+** (recommended: Python 3.11)
- **pip** (Python package manager)
- **OpenAI API Key** (for embeddings and LLM)

### Step 1: Clone the Repository

```bash
git clone <repo-url>
cd "paper-qa"
```

### Step 2: Create a Virtual Environment

It is **strongly recommended** to use a virtual environment to isolate dependencies.

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

> **Note:** You should see `(.venv)` prefix in your terminal prompt when the virtual environment is active.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- `fastapi`, `uvicorn` - Web framework and server
- `langchain`, `langchain-openai`, `langgraph` - LLM orchestration
- `chromadb` - Vector database
- `mcp` - Model Context Protocol
- `streamlit` - Frontend UI
- `arxiv` - arXiv API client
- `PyMuPDF` - PDF processing
- `markdown-pdf` - PDF report generation

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Alternatively, copy the example file:

```bash
cp .env.example .env
# Then edit .env and add your API key
```

---

## File Path Configuration

This section documents all configurable file paths in the project. **Modify these paths if you want to change where data is stored.**

### 1. RAG Papers Directory

**Location:** `Tools Server/RAG SETUP/Papers/`

**Files to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Tools Server/RAG SETUP/Rag.py` | `final_papers_path` | 84 | Default papers directory |
| `Tools Server/RAG SETUP/RagTool.py` | `papers_path` | 9 | Papers path for RAG tool |
| `Tools Server/RAG SETUP/corpus_expansion.py` | `PAPERS_PATH` | 20 | Where downloaded papers are saved |

**Default behavior:** All paths are relative to `Tools Server/RAG SETUP/` using `Path(__file__).resolve().parent`.

**To change the papers directory:**
```python
# In corpus_expansion.py (line 20)
PAPERS_PATH = Path("C:/your/custom/papers/path")

# In RagTool.py (line 9)
papers_path = Path("C:/your/custom/papers/path")
```

**Expected folder structure for papers:**
```
Papers/
├── Artificial Intelligence/     # Subject folder
│   ├── Agentic AI/              # Topic folder
│   │   └── Paper Title - 2024.pdf
│   ├── Finetuning/
│   │   └── Another Paper - 2023.pdf
│   └── Hierarchical Reasoning Models/
└── Other Subject/
    └── Topic/
```

### 2. Vector Database Directory

**Location:** `Tools Server/RAG SETUP/VectorDB/`

**Files to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Tools Server/RAG SETUP/Rag.py` | `final_persist_dir` | 85 | ChromaDB persistence directory |
| `Tools Server/RAG SETUP/RagTool.py` | `vectordb_path` | 10 | VectorDB path for RAG tool |
| `Tools Server/RAG SETUP/corpus_expansion.py` | `VECTORDB_PATH` | 21 | VectorDB path for indexing |

**To change the vector database directory:**
```python
# In corpus_expansion.py (line 21)
VECTORDB_PATH = Path("C:/your/custom/vectordb/path")

# In RagTool.py (line 10)
vectordb_path = Path("C:/your/custom/vectordb/path")
```

> **Important:** All three files must point to the **same VectorDB directory** for the system to work correctly.

### 3. Generated Reports Directory

**Location:** `Reports/` (project root)

**File to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Tools Server/McpServer.py` | `REPORTS_DIR` | 159 | Where PDF reports are saved |

**To change the reports directory:**
```python
# In McpServer.py (line 159)
REPORTS_DIR = Path("C:/your/custom/reports/path")
```

### 4. MCP Server URL

**Default:** `http://127.0.0.1:8787/sse`

**Files to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Agentic System/Agent SetUp/agent.py` | `server_url` | 78 | MCP connection URL |
| `Agentic System/main.py` | `mcp_server_url` | 44 | MCP server URL for assistant |

### 5. FastAPI Backend URL

**Default:** `http://localhost:8000`

**File to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Frontend/app.py` | `API_BASE_URL` | 14 | Backend URL for frontend |

### 6. Agent Prompt File

**Location:** `Agentic System/Agent SetUp/prompt.md`

**File to modify:**

| File | Variable | Line | Description |
|------|----------|------|-------------|
| `Agentic System/Agent SetUp/agent.py` | File path in `open()` | 129 | Path to system prompt file |

**To change the prompt file path:**
```python
# In agent.py (line 129-130)
with open(r"C:\your\custom\path\prompt.md", "r", encoding="utf-8") as file:
    RESEARCH_ASSISTANT_PROMPT = file.read()
```

---

## Running the System

### Start Order

The system must be started in this order:
1. **MCP Server** (Tools Server) - First
2. **FastAPI Backend** (Agentic System) - Second
3. **Streamlit Frontend** - Third (optional)

### Terminal 1: Start the MCP Server

```bash
cd "Tools Server"
python McpServer.py
```

**Expected output:**
```
Starting Research Assistant MCP Server...
Available tools:
  1. research_paper_probe - Query the RAG knowledge base
  2. search_arxiv - Search arXiv for papers
  3. download_paper - Download and index papers
  4. generate_report - Generate PDF reports
INFO:     Uvicorn running on http://0.0.0.0:8787 (Press CTRL+C to quit)
```

### Terminal 2: Start the FastAPI Backend

```bash
cd "Agentic System"
python main.py
```

**Expected output:**
```
🚀 Starting Research Assistant API...
✓ Connected to MCP Server
✓ Loaded 4 tools: ['research_paper_probe', 'search_arxiv', 'download_paper', 'generate_report']
✓ Agent created with workflow system prompt
✓ Research Assistant ready!
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Terminal 3: Start the Streamlit Frontend

```bash
cd Frontend
streamlit run app.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Assistant status (ready, tools, conversation length) |
| `POST` | `/chat` | Send message (maintains conversation history) |
| `POST` | `/chat/single` | Send a single message without history |
| `POST` | `/clear` | Clear conversation history |

### Example API Usage

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Send a Chat Message:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the latest advances in LLMs?"}'
```

**Interactive API Documentation:**
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

---

## Agent Workflow

The agent follows this workflow when answering questions:

1. **Check Local Knowledge Base** - First queries the RAG database for relevant papers
2. **Offer arXiv Search** - If no relevant papers found, offers to search arXiv
3. **Present Results** - Shows numbered list of papers with titles, authors, abstracts
4. **Download on Request** - Downloads selected papers and auto-indexes them
5. **Answer with New Sources** - Re-queries RAG to answer using newly added papers
6. **Generate Reports** - Can create PDF reports summarizing research findings

---

## Project Structure

```
Research Assistant Multi Agent System/
├── .env                          # Environment variables (OPENAI_API_KEY)
├── .env.example                  # Example environment file
├── requirements.txt              # Python dependencies
├── README.md                     # This file
│
├── Tools Server/                 # MCP Server (port 8787)
│   ├── McpServer.py              # MCP server with 4 tools
│   ├── doc.md                    # Tool documentation
│   └── RAG SETUP/
│       ├── Rag.py                # Core RAG implementation
│       ├── RagTool.py            # RAG search tool wrapper
│       ├── corpus_expansion.py   # arXiv search + download + auto-index
│       ├── Papers/               # Downloaded PDFs (organized by subject/topic)
│       │   └── Artificial Intelligence/
│       │       ├── Agentic AI/
│       │       ├── Finetuning/
│       │       └── Hierarchical Reasoning Models/
│       └── VectorDB/             # ChromaDB vector store (auto-generated)
│
├── Agentic System/               # FastAPI Backend (port 8000)
│   ├── main.py                   # FastAPI app with endpoints
│   └── Agent SetUp/
│       ├── __init__.py
│       ├── agent.py              # LangGraph agent + MCP connection
│       └── prompt.md             # System prompt for the agent
│
├── Frontend/                     # Streamlit Web UI (port 8501)
│   └── app.py                    # Streamlit application
│
├── Reports/                      # Generated PDF reports (auto-created)
│
└── Build Up Phase/               # Development notebooks and experiments
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not found` | Ensure `.env` file exists in project root with valid API key |
| `MCP Server connection failed` | Start MCP Server first, then FastAPI backend |
| `ChromaDB version error` | Delete `VectorDB/` folder and restart to rebuild |
| `ModuleNotFoundError` | Ensure virtual environment is activated and run `pip install -r requirements.txt` |
| `Port already in use` | Kill existing process or change port in respective file |

### Rebuilding the Vector Database

If you encounter VectorDB issues, delete and rebuild:

```bash
# Delete existing VectorDB
rm -rf "Tools Server/RAG SETUP/VectorDB"

# Restart MCP Server - it will rebuild the VectorDB from papers
cd "Tools Server"
python McpServer.py
```

