# 🐳 Dockerization Guide: Research Assistant Multi-Agent System

> A comprehensive tutorial on containerizing a multi-service AI application with persistent data handling.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Design](#2-architecture-design)
3. [Pre-Dockerization Preparation](#3-pre-dockerization-preparation)
4. [Requirements Management Strategy](#4-requirements-management-strategy)
5. [Data Persistence Strategy](#5-data-persistence-strategy)
6. [Dockerfiles Deep Dive](#6-dockerfiles-deep-dive)
7. [Docker Compose Configuration](#7-docker-compose-configuration)
8. [Environment Variables](#8-environment-variables)
9. [Running the Application](#9-running-the-application)
10. [Development Workflow](#10-development-workflow)
11. [Troubleshooting](#11-troubleshooting)
12. [Best Practices & Lessons Learned](#12-best-practices--lessons-learned)

---

## 1. Project Overview

### What We're Dockerizing

The **Research Assistant** is a multi-agent AI system consisting of three main components:

| Service | Technology | Purpose |
|---------|------------|---------|
| **Frontend** | Streamlit | User interface for interacting with the research assistant |
| **Backend** | FastAPI + LangGraph | Agent orchestration, conversation management |
| **MCP Server** | FastMCP | Tools server providing RAG queries, paper downloads, report generation |

### Data Requirements

The system works with three types of persistent data:

- **Papers/** - Research papers organized hierarchically by topic (read + write)
- **VectorDB/** - ChromaDB embeddings for semantic search (read + write)
- **Reports/** - Generated PDF reports (write by MCP, read by user)

---

## 2. Architecture Design

### Container Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Docker Network                                  │
│                        (research-network)                               │
│                                                                          │
│   ┌──────────────┐    REST API    ┌──────────────┐    SSE      ┌──────────────┐
│   │   Frontend   │ ─────────────▶ │   Backend    │ ─────────▶  │  MCP Server  │
│   │  (Streamlit) │                │  (FastAPI)   │             │  (FastMCP)   │
│   │   :8501      │                │   :8000      │             │   :8787      │
│   └──────────────┘                └──────────────┘             └──────────────┘
│         │                                                            │
│         │                                                            │
└─────────│────────────────────────────────────────────────────────────│──┘
          │                                                            │
          ▼                                                            ▼
    ┌───────────┐                                         ┌─────────────────────┐
    │  Reports  │◄────────────────────────────────────────│   Papers + VectorDB │
    │  (read)   │                                         │   (read + write)    │
    └───────────┘                                         └─────────────────────┘
          │                                                            │
          └────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Host File System   │
                         │    (Bind Mounts)    │
                         └─────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **3 separate containers** | Independent scaling, isolation, single responsibility |
| **Shared Docker network** | Inter-service communication by service name |
| **Bind mounts for data** | User can access/modify files on host system |
| **Health checks** | Proper startup ordering with `depends_on: condition: service_healthy` |

---

## 3. Pre-Dockerization Preparation

### 3.1 Path Refactoring

**Problem:** Hardcoded paths like `Path(__file__).resolve().parent / "Papers"` don't work in containers with bind mounts.

**Solution:** Use environment variables with fallbacks for local development.

```python
# Before (hardcoded - won't work in Docker)
PAPERS_PATH = Path(__file__).resolve().parent / "Papers"

# After (flexible - works everywhere)
import os
from pathlib import Path

PAPERS_PATH = Path(os.getenv("PAPERS_DIR", Path(__file__).resolve().parent / "Papers"))
VECTORDB_PATH = Path(os.getenv("VECTORDB_DIR", Path(__file__).resolve().parent / "VectorDB"))
REPORTS_PATH = Path(os.getenv("REPORTS_DIR", Path(__file__).resolve().parent / "Reports"))
```

### 3.2 Service URL Configuration

Make inter-service URLs configurable:

```python
# Backend - connecting to MCP Server
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8787/sse")

# Frontend - connecting to Backend
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

### 3.3 Folder Naming

**Important:** Avoid spaces in folder names. They cause issues in Docker `COPY` commands.

```
# Problematic
Agentic System/
Tools Server/
Agent SetUp/

# Recommended
Backend/
MCP-Server/
agent_setup/
```

---

## 4. Requirements Management Strategy

### The Challenge

One monolithic `requirements.txt` means every container installs everything, even unused packages.

### Our Solution: Split Requirements

```
requirements/
├── base.txt          # Shared: openai, pydantic, requests, python-dotenv
├── frontend.txt      # Streamlit only
├── backend.txt       # FastAPI, LangGraph, MCP client
└── mcp-server.txt    # ChromaDB, LangChain, PyMuPDF, arxiv
```

### File Structure

**requirements/base.txt**
```
# Shared across all services
python-dotenv==1.0.0
pydantic==2.12.5
pydantic-settings==2.12.0
requests==2.32.4
openai==1.99.1
```

**requirements/frontend.txt**
```
-r base.txt
streamlit==1.42.2
```

**requirements/backend.txt**
```
-r base.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
langgraph==0.6.3
mcp==1.12.3
langchain-core==0.3.72
langchain-openai==0.3.28
langchain-community==0.3.27
```

**requirements/mcp-server.txt**
```
-r base.txt
mcp==1.12.3
fastapi==0.109.0
uvicorn[standard]==0.27.0
chromadb==1.3.5
langchain==0.3.27
langchain-core==0.3.72
langchain-openai==0.3.28
langchain-community==0.3.27
arxiv==2.3.1
PyMuPDF==1.26.6
markdown-pdf==1.10
lark==1.3.1
tqdm==4.67.1
```

### Benefits

| Metric | Monolithic | Split |
|--------|------------|-------|
| Frontend image size | ~2GB | ~500MB |
| Backend image size | ~2GB | ~800MB |
| MCP Server image size | ~2GB | ~1.5GB |
| Build time | Same for all | Faster for frontend/backend |

---

## 5. Data Persistence Strategy

### Bind Mounts vs Named Volumes

| Feature | Bind Mounts | Named Volumes |
|---------|-------------|---------------|
| User can see files on host | ✅ Yes | ❌ No |
| User can pre-populate data | ✅ Easy | ⚠️ Complex |
| Portable across machines | ⚠️ Path-dependent | ✅ Docker-managed |
| Our choice | ✅ **Selected** | - |

### Why Bind Mounts?

Our use case requires:
1. Users to add their own research papers
2. Downloaded papers to be visible on the host
3. Generated reports to be accessible outside Docker
4. VectorDB to persist between container restarts

### Mount Configuration

```yaml
volumes:
  # Host path : Container path
  - ${PAPERS_DIR:-./data/Papers}:/data/Papers
  - ${VECTORDB_DIR:-./data/VectorDB}:/data/VectorDB
  - ${REPORTS_DIR:-./data/Reports}:/data/Reports
```

The `${VAR:-default}` syntax means:
- Use `$PAPERS_DIR` if set in `.env`
- Otherwise, default to `./data/Papers`

---

## 6. Dockerfiles Deep Dive

### 6.1 Frontend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements/base.txt requirements/frontend.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/frontend.txt

# Copy application code
COPY Frontend/app.py .

# Expose Streamlit port
EXPOSE 8501

# Health check (using Python since curl not available in slim image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health', timeout=5)" || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Key Points:**
- Uses `python:3.11-slim` for smaller image size
- Health check uses Python (not curl) because slim images don't include curl
- `--server.address=0.0.0.0` allows external access

### 6.2 Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements/base.txt requirements/backend.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/backend.txt

# Copy application code
COPY Backend/ .

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.3 MCP Server Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/mcp-server.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/mcp-server.txt

# Copy application code
COPY MCP-Server/ .

# Create data directories (will be overwritten by mounts)
RUN mkdir -p /data/Papers /data/VectorDB /data/Reports

# Expose MCP server port
EXPOSE 8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8787/sse', timeout=5)" || exit 1

# Run the MCP server
CMD ["python", "McpServer.py"]
```

**Key Points:**
- Installs `libmupdf-dev` for PyMuPDF PDF processing
- Creates data directories (overwritten by bind mounts at runtime)
- Longer `start-period` for health check (RAG initialization takes time)

---

## 7. Docker Compose Configuration

### docker-compose.yml

```yaml
services:
  # ============== MCP Server ==============
  mcp-server:
    build:
      context: .
      dockerfile: MCP-Server/DockerFile
    container_name: research-mcp-server
    ports:
      - "8787:8787"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PAPERS_DIR=/data/Papers
      - VECTORDB_DIR=/data/VectorDB
      - REPORTS_DIR=/data/Reports
    volumes:
      - ${PAPERS_DIR:-./data/Papers}:/data/Papers
      - ${VECTORDB_DIR:-./data/VectorDB}:/data/VectorDB
      - ${REPORTS_DIR:-./data/Reports}:/data/Reports
    restart: unless-stopped
    networks:
      - research-network

  # ============== Backend (Agent) ==============
  backend:
    build:
      context: .
      dockerfile: Backend/DockerFile
    container_name: research-backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MCP_SERVER_URL=http://mcp-server:8787/sse
      - MODEL_NAME=${MODEL_NAME:-gpt-4o-mini}
    depends_on:
      mcp-server:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - research-network

  # ============== Frontend ==============
  frontend:
    build:
      context: .
      dockerfile: Frontend/DockerFile
    container_name: research-frontend
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - research-network

networks:
  research-network:
    driver: bridge
```

### Key Configuration Explained

| Setting | Purpose |
|---------|---------|
| `context: .` | Build context is project root (access to all files) |
| `depends_on: condition: service_healthy` | Wait for dependency to be healthy before starting |
| `http://mcp-server:8787` | Service name as hostname (Docker DNS) |
| `research-network` | Isolated network for inter-service communication |
| `restart: unless-stopped` | Auto-restart on failure, but not after manual stop |

---

## 8. Environment Variables

### .env.example (Template for Users)

```env
# ============== API Keys ==============
OPENAI_API_KEY=""

# ============== Service URLs (Docker Internal) ==============
# These are set automatically in docker-compose.yml
# Only override if running services manually outside Docker
# MCP_SERVER_URL=http://mcp-server:8787/sse
# API_BASE_URL=http://backend:8000

# ============== Model Configuration ==============
MODEL_NAME=gpt-4o-mini

# ============== Data Paths (Optional) ==============
# Override these to use custom directories on your host machine
# If not set, defaults to ./data/* in the project directory
# PAPERS_DIR=C:/Users/YourName/Research/Papers
# VECTORDB_DIR=C:/Users/YourName/Research/VectorDB
# REPORTS_DIR=C:/Users/YourName/Research/Reports
```

### How Environment Variables Flow

```
.env file (host)
      │
      ▼
docker-compose.yml (interpolates ${VAR})
      │
      ▼
Container environment
      │
      ▼
Python os.getenv("VAR")
```

### Important Notes on .env Files

1. **Automatic Loading:** Docker Compose automatically reads `.env` from the same directory as `docker-compose.yml`

2. **Using a Different File:** To use a differently named file (e.g., `.env.production`):
   ```bash
   docker compose --env-file .env.production up -d
   ```

3. **Verify Variables Are Loaded:**
   ```bash
   docker compose config
   # This prints the resolved config with actual values substituted
   ```

4. **Security:**
   - Never commit `.env` to version control (add to `.gitignore`)
   - Only commit `.env.example` as a template
   - Each user creates their own `.env` with their API keys

---

## 9. Running the Application

### Running with Pre-Built Images (For End Users)

If the Docker images are already pushed to a registry, users don't need the source code—just the compose file and their own `.env`.

**What users need:**

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestration file with image references |
| `.env` | User's own API keys and configuration |

**Quick setup for users:**

```bash
# 1. Download the compose file (or copy from repo)
curl -O https://raw.githubusercontent.com/<your-repo>/main/docker-compose.yml

# 2. Create .env with your API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "MODEL_NAME=gpt-4o-mini" >> .env

# 3. Create data folders
mkdir -p data/Papers data/VectorDB data/Reports

# 4. Pull and run (no --build needed!)
docker compose up -d
```

> **Note:** Docker Compose automatically reads the `.env` file from the same directory as `docker-compose.yml`. No extra flags needed.

### First-Time Setup (Building from Source)

```bash
# 1. Clone the repository
git clone <repo-url>
cd "Research Assistant Multi Agent System"

# 2. Create your .env file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Ensure data directory exists
mkdir -p data/Papers data/VectorDB data/Reports

# 4. Build and start all services
docker compose up -d --build
```

### Verify Everything is Running

```bash
# Check container status
docker compose ps

# Expected output:
# NAME                  STATUS              PORTS
# research-mcp-server   Up (healthy)        0.0.0.0:8787->8787/tcp
# research-backend      Up (healthy)        0.0.0.0:8000->8000/tcp
# research-frontend     Up (healthy)        0.0.0.0:8501->8501/tcp
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:8501 |
| Backend API Docs | http://localhost:8000/docs |
| MCP Server | http://localhost:8787/sse |

### Understanding Network Addresses

When you see `0.0.0.0:8501->8501/tcp` in `docker compose ps`, here's what it means:

| Address | What It Means |
|---------|---------------|
| `0.0.0.0` | **Bind address** — Docker listens on *all* network interfaces (not a URL you visit) |
| `127.0.0.1` / `localhost` | Loopback — only accessible from the same machine |
| Your IPv4 (e.g., `192.168.x.x`) | Your machine's actual IP on the local network |

**How to access the application:**

| From | Use |
|------|-----|
| Same machine | `http://localhost:8501` or `http://127.0.0.1:8501` |
| Another device on network | `http://<your-ipv4>:8501` (e.g., `http://192.168.1.100:8501`) |
| Remote server (cloud) | `http://<public-ip>:8501` (ensure port 8501 is open in firewall) |

**Finding your IPv4 address (Windows):**
```bash
ipconfig
# Look for "IPv4 Address" under your active adapter
```

### Common Commands

```bash
# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f mcp-server

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes VectorDB!)
docker compose down -v

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d

# Restart a specific service
docker compose restart backend
```

---

## 10. Development Workflow

### docker-compose.override.yml

For development, this file enables hot reload:

```yaml
# Development overrides - enables hot reload
services:
  mcp-server:
    volumes:
      - "./MCP-Server:/app:ro"
    environment:
      - PYTHONDONTWRITEBYTECODE=1

  backend:
    volumes:
      - "./Backend:/app:ro"
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  frontend:
    volumes:
      - ./Frontend:/app:ro
```

### How It Works

1. Docker automatically merges `docker-compose.yml` + `docker-compose.override.yml`
2. Source code is mounted read-only (`:ro`) into containers
3. Uvicorn's `--reload` flag watches for file changes
4. Changes to Python files trigger automatic restart

### Development Cycle

```bash
# Start in development mode (override is applied automatically)
docker compose up -d

# Make code changes in your IDE
# → Backend/Frontend auto-reload
# → MCP Server requires manual restart:
docker compose restart mcp-server
```

### Production Mode (Ignore Override)

```bash
# Explicitly use only the main compose file
docker compose -f docker-compose.yml up -d
```

---

## 11. Troubleshooting

### Container Won't Start

```bash
# Check logs for the failing service
docker compose logs mcp-server

# Common issues:
# - Missing OPENAI_API_KEY → Add to .env file
# - Port already in use → Stop other services or change port
# - Missing data directory → Create ./data/Papers, etc.
```

### Health Check Failing

```bash
# Check if service is actually running
docker compose exec backend python -c "import requests; print(requests.get('http://localhost:8000/health').status_code)"

# Increase health check start-period if service needs more init time
```

### Permission Issues (Linux/Mac)

```bash
# Container writes files as root, you can't edit them
# Solution: Run container with your user ID
# Add to docker-compose.yml:
services:
  mcp-server:
    user: "${UID}:${GID}"
```

### VectorDB Corruption

```bash
# If ChromaDB gets corrupted, reset it:
rm -rf data/VectorDB/*
docker compose restart mcp-server
# RAG will re-index all papers on startup
```

### Windows Path Issues

```bash
# Windows paths in .env need forward slashes or escaped backslashes:
PAPERS_DIR=C:/Users/YourName/Papers
# OR
PAPERS_DIR=C:\\Users\\YourName\\Papers
```

---

## 12. Best Practices & Lessons Learned

### ✅ Do's

1. **Use environment variables for all paths and URLs**
   - Makes the app portable across environments

2. **Split requirements by service**
   - Smaller images, faster builds

3. **Use health checks with `depends_on: condition: service_healthy`**
   - Ensures proper startup order

4. **Use `.dockerignore`**
   - Speeds up builds, reduces image size

5. **Use bind mounts for user data**
   - Users can see and modify files on their host

6. **Document everything**
   - Future you will thank present you

### ❌ Don'ts

1. **Don't use spaces in folder names**
   - Causes issues in Docker COPY commands

2. **Don't hardcode `localhost` URLs**
   - In Docker, services are referenced by service name

3. **Don't use `curl` in health checks with slim images**
   - Slim images don't include curl; use Python instead

4. **Don't bake data into images**
   - Use volumes for persistence

5. **Don't expose unnecessary ports**
   - Only expose ports that need external access

---

## Quick Reference Card

```bash
# Start everything
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop everything
docker compose down

# Rebuild single service
docker compose build backend
docker compose up -d backend

# Enter container shell
docker compose exec mcp-server bash

# View resource usage
docker stats
```

---

## File Structure Summary

```
Research Assistant Multi Agent System/
├── docker-compose.yml           # Main orchestration
├── docker-compose.override.yml  # Development overrides
├── .env                         # Your secrets (gitignored)
├── .env.example                 # Template for users
├── .dockerignore                # Exclude files from build
│
├── requirements/
│   ├── base.txt                 # Shared dependencies
│   ├── frontend.txt             # Streamlit
│   ├── backend.txt              # FastAPI, LangGraph
│   └── mcp-server.txt           # ChromaDB, LangChain
│
├── Frontend/
│   ├── DockerFile
│   └── app.py
│
├── Backend/
│   ├── DockerFile
│   ├── main.py
│   └── Agent SetUp/
│
├── MCP-Server/
│   ├── DockerFile
│   ├── McpServer.py
│   └── RAG SETUP/
│
└── data/                        # Persistent data (bind mounted)
    ├── Papers/
    ├── VectorDB/
    └── Reports/
```

---

*Document created: December 26, 2025*
*Last updated: December 26, 2025*
