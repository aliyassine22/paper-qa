# Research Assistant Multi-Agent System

An AI-powered research assistant that combines a **RAG knowledge base**, **arXiv search**, and **paper downloading** into a unified agent system. Built with LangGraph, FastMCP, and FastAPI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Future)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               FastAPI Backend (port 8000)                       │
│               Agentic System/main.py                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         LangGraph Agent (ResearchAssistant)             │   │
│   │         - Conversation history                          │   │
│   │         - Tool orchestration                            │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 MCP Server (port 8787)                          │
│                 Tools Server/McpServer.py                       │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐ │
│   │ research_     │ │ search_arxiv  │ │ download_paper        │ │
│   │ paper_probe   │ │               │ │ (auto-indexes to RAG) │ │
│   │ (RAG query)   │ │               │ │                       │ │
│   └───────────────┘ └───────────────┘ └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ChromaDB Vector Store                        │
│                    Tools Server/RAG SETUP/VectorDB              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

- **RAG Knowledge Base**: Query indexed research papers with semantic search
- **arXiv Integration**: Search arXiv for new papers
- **Auto-Indexing**: Downloaded papers are automatically added to the vector database
- **Conversation Memory**: Multi-turn conversations with context
- **RESTful API**: Easy integration with any frontend

---

## Quick Start

### 1. Clone & Install Dependencies

```bash
git clone <repo-url>
cd "Research Assistant Multi Agent System"

# Create virtual environment (recommended)
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Start the MCP Server (Tools Server)

The MCP server provides the tools (RAG query, arXiv search, paper download).

```bash
cd "Tools Server"
python McpServer.py
```

Expected output:
```
Starting Research Assistant MCP Server...
Available tools:
  1. research_paper_probe - Query the RAG knowledge base
  2. search_arxiv - Search arXiv for papers
  3. download_paper - Download and index papers
INFO:     Uvicorn running on http://0.0.0.0:8787 (Press CTRL+C to quit)
```

### 4. Start the FastAPI Backend (Agent)

In a **new terminal**, start the FastAPI backend:

```bash
cd "Agentic System"
python main.py
```

Expected output:
```
🚀 Starting Research Assistant API...
✓ Connected to MCP Server
✓ Loaded 3 tools: ['research_paper_probe', 'search_arxiv', 'download_paper']
✓ Agent created with workflow system prompt
✓ Research Assistant ready!
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 5. Test the API

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Status:**
```bash
curl http://localhost:8000/status
```

**Chat (single message):**
```bash
curl -X POST http://localhost:8000/chat/single \
  -H "Content-Type: application/json" \
  -d '{"message": "What is quantum machine learning?"}'
```

**Interactive Docs:**
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Assistant status (ready, tools, conversation length) |
| `POST` | `/chat` | Send message (maintains conversation history) |
| `POST` | `/chat/single` | Send single message (no history) |
| `POST` | `/clear` | Clear conversation history |
| `POST` | `/reinitialize` | Reconnect to MCP server |

### Request/Response Examples

**POST /chat**
```json
// Request
{ "message": "What are the latest advances in LLMs for drug discovery?" }

// Response
{
  "response": "Based on the research papers in the knowledge base...",
  "success": true,
  "error": null
}
```

---

## Agent Workflow

The agent follows this workflow when answering questions:

1. **Check Local Knowledge Base** - First queries the RAG database for relevant papers
2. **Offer arXiv Search** - If no relevant papers found, offers to search arXiv
3. **Present Results** - Shows numbered list of papers with titles, authors, abstracts
4. **Download on Request** - Downloads selected papers and auto-indexes them
5. **Answer with New Sources** - Re-queries RAG to answer using newly added papers

---

## Project Structure

```
Research Assistant Multi Agent System/
├── .env                          # Environment variables (OPENAI_API_KEY)
├── requirements.txt              # Python dependencies
├── README.md                     # This file
│
├── Tools Server/                 # MCP Server (port 8787)
│   ├── McpServer.py              # MCP server with 3 tools
│   └── RAG SETUP/
│       ├── RagTool.py            # RAG search tool
│       ├── corpus_expansion.py   # arXiv search + download + auto-index
│       ├── Papers/               # Downloaded PDFs organized by subject/topic
│       └── VectorDB/             # ChromaDB vector store
│
├── Agentic System/               # FastAPI Backend (port 8000)
│   ├── main.py                   # FastAPI app with endpoints
│   ├── test_agent.py             # Quick test script
│   └── Agent SetUp/
│       ├── __init__.py
│       └── agent.py              # LangGraph agent + MCP connection
│
├── Build Up Phase/               # Development notebooks
│   └── MCP Server Tryout with the Agent/
│       └── McpTryout.ipynb       # Interactive testing notebook
│
└── Frontend/                     # (Future) Web UI
```

---

## Troubleshooting

### Port already in use

If you see `[Errno 10048] error while attempting to bind on address`:

```powershell
# Kill process on port 8787 (MCP)
Get-NetTCPConnection -LocalPort 8787 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Kill process on port 8000 (FastAPI)
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### MCP Server not running

If FastAPI shows "Research Assistant failed to initialize":

1. Make sure MCP server is running first (port 8787)
2. Call the reinitialize endpoint: `POST http://localhost:8000/reinitialize`

### Connection errors during chat

Transient network issues with OpenAI API. Simply retry the request.

---

## Development

### Run Tests

```bash
cd "Agentic System"
python test_agent.py
```

### Interactive Testing

Open `Build Up Phase/MCP Server Tryout with the Agent/McpTryout.ipynb` in VS Code or Jupyter.

---

## License

MIT
