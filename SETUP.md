# 🚀 Research Assistant - Complete Setup Guide

This guide will help you set up and run the Research Assistant system from scratch.

## 📋 Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- OpenAI API key (set in `.env` file)

## 🔧 Step-by-Step Setup

### 1. Install Dependencies

```bash
# Navigate to project root
cd C:\Users\Admin\Desktop\paper-qa

# Activate your virtual environment (if using one)
# For venv: .venv\Scripts\activate
# For conda: conda activate your_env_name

# Install all dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (if it doesn't exist) with your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the MCP Server (Terminal 1)

The MCP server provides the tools (RAG search, arXiv search, paper download) to the agent.

```bash
# Navigate to Tools Server directory
cd "Tools Server"

# Start the MCP server
python McpServer.py
```

**Expected output:**
```
Starting Research Assistant MCP Server...
Available tools:
  1. research_paper_probe - Query the RAG knowledge base
  2. search_arxiv - Search arXiv for papers
  3. download_paper - Download and index papers
```

**Keep this terminal running!** The server should be listening on `http://127.0.0.1:8787`

### 4. Start the FastAPI Backend (Terminal 2)

The FastAPI backend hosts the agent and provides the REST API endpoints.

```bash
# Navigate to Agentic System directory
cd "Agentic System"

# Start the FastAPI server
python main.py
```

**OR** using uvicorn directly:

```bash
cd "Agentic System"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
🚀 Starting Research Assistant API...
✓ Connected to MCP Server
✓ Loaded 3 tools: ['research_paper_probe', 'search_arxiv', 'download_paper']
✓ Agent created with workflow system prompt
✓ Research Assistant ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal running!** The API should be available at `http://localhost:8000`

### 5. Start the Streamlit Frontend (Terminal 3)

The Streamlit frontend provides the user interface.

```bash
# Navigate to Frontend directory
cd Frontend

# Start Streamlit
streamlit run app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

The browser should automatically open to `http://localhost:8501`

## 🎯 Quick Start (All Commands)

If you want to run everything quickly, open **3 separate terminals**:

**Terminal 1 - MCP Server:**
```bash
cd "C:\Users\Admin\Desktop\paper-qa\Tools Server"
python McpServer.py
```

**Terminal 2 - FastAPI Backend:**
```bash
cd "C:\Users\Admin\Desktop\paper-qa\Agentic System"
python main.py
```

**Terminal 3 - Streamlit Frontend:**
```bash
cd "C:\Users\Admin\Desktop\paper-qa\Frontend"
streamlit run app.py
```

## ✅ Verification

1. **Check MCP Server**: Should show "Starting Research Assistant MCP Server..."
2. **Check FastAPI**: Visit `http://localhost:8000/docs` - you should see the API documentation
3. **Check Frontend**: Visit `http://localhost:8501` - you should see the chat interface

## 🎨 Using the Frontend

1. **Check Status**: The sidebar shows connection status and system metrics
2. **Ask Questions**: Type your question in the chat input at the bottom
3. **Clear History**: Click "Clear History" in the sidebar to reset the conversation
4. **View Status**: Monitor tools loaded, conversation length, and connection status

## 🔍 Example Queries

Try asking:
- "What is QLoRA and how does it help with fine-tuning?"
- "Search for recent papers on agentic AI"
- "What are the latest advances in hierarchical reasoning models?"

## 🐛 Troubleshooting

### "Cannot connect to API"
- Make sure the FastAPI backend is running on port 8000
- Check that no firewall is blocking the connection
- Verify the API is accessible at `http://localhost:8000/health`

### "MCP Server not connected"
- Ensure the MCP server is running on port 8787
- Check that the backend can reach `http://127.0.0.1:8787/sse`
- Restart both servers if needed

### "Assistant not initialized"
- Wait a few seconds after starting the backend for initialization
- Check the backend terminal for error messages
- Verify your OpenAI API key is set correctly in `.env`

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using the correct Python environment
- Check that all required packages are in `requirements.txt`

## 📁 Project Structure

```
paper-qa/
├── Agentic System/          # FastAPI backend + agent
│   ├── main.py             # FastAPI app
│   └── Agent SetUp/
│       └── agent.py        # LangGraph agent
├── Tools Server/            # MCP server with tools
│   ├── McpServer.py        # MCP server entry point
│   └── RAG SETUP/          # RAG tools implementation
├── Frontend/                # Streamlit frontend
│   └── app.py              # Streamlit app
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## 🎉 You're All Set!

Once all three services are running, you can start chatting with your Research Assistant!

