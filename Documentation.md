# MCP Server Tools Documentation

## Introduction to Model Context Protocol (MCP)

### What is MCP?
The **Model Context Protocol (MCP)** is an open standard developed by Anthropic that enables seamless communication between AI applications and external tools, data sources, and services. It provides a standardized way for Large Language Models (LLMs) to interact with the outside world through a well-defined protocol.

MCP follows a **client-server architecture**:
- **MCP Server**: Exposes tools, resources, and prompts that can be consumed by AI agents
- **MCP Client**: Connects to MCP servers and makes tool capabilities available to the LLM

### Why Use an MCP Server for Agentic Systems?

| Advantage | Description |
|-----------|-------------|
| **Standardization** | A unified protocol means tools built once can work with any MCP-compatible agent (Claude, custom agents, etc.) |
| **Decoupling** | Tools are separate from the agent logic, allowing independent development, testing, and deployment |
| **Discoverability** | Agents can dynamically discover available tools and their schemas at runtime |
| **Scalability** | MCP servers can run on separate processes or machines, enabling distributed architectures |
| **Reusability** | The same MCP server can serve multiple agents or applications simultaneously |
| **Type Safety** | Tool schemas are defined with Pydantic models, ensuring type validation and clear contracts |
| **Maintainability** | Updates to tools don't require changes to the agent codebase |

### MCP in This Project

This Research Assistant system uses an MCP server to expose research tools:

```
┌─────────────────────────────────────────────────────────────────┐
│               FastAPI Backend (Agent Host)                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         LangGraph Agent (ResearchAssistant)             │   │
│   │         - Orchestrates tool calls                       │   │
│   │         - Maintains conversation state                  │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                          MCP Protocol
                           (SSE/HTTP)
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 MCP Server (FastMCP)                            │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐ │
│   │ research_     │ │ search_arxiv  │ │ download_paper        │ │
│   │ paper_probe   │ │               │ │                       │ │
│   └───────────────┘ └───────────────┘ └───────────────────────┘ │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                    generate_report                        │ │
│   └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

The agent connects to the MCP server via **Server-Sent Events (SSE)** transport, discovers available tools, and invokes them as needed during conversations.

---

## Available Tools

This document provides detailed documentation for each tool available in the Research Assistant MCP Server.

---

## Tool 1: `research_paper_probe`

### Purpose
Search and query the local RAG (Retrieval-Augmented Generation) knowledge base containing indexed research papers to answer questions about AI research.

### Functionality
1. Takes a natural language query and optional filters (topic, subject, year)
2. Searches the ChromaDB vector database for semantically relevant paper chunks
3. Uses an LLM to generate an answer based on retrieved context
4. Returns a structured response with the answer, sources, and confidence score

### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `str` | ✅ | - | Natural language question to search for |
| `topic` | `str` | ❌ | `None` | Filter by topic: `"Agentic AI"`, `"Finetuning"`, `"Hierarchical Reasoning Models"`, `"Deep Learning"`, `"Drug Discovery"`, `"Quantum ML"` |
| `subject` | `str` | ❌ | `None` | Filter by subject area (e.g., `"Artificial Intelligence"`) |
| `year` | `int` | ❌ | `None` | Filter by publication year (e.g., `2024`) |
| `k` | `int` | ❌ | `10` | Number of document chunks to retrieve |

### Response Schema
```python
{
    "topic": str,           # Topic searched or inferred
    "category": str,        # Category: topic name or "Not Found"
    "response": str,        # LLM-generated answer in markdown
    "sources": [            # List of source references
        {
            "paper_title": str,
            "year": int,
            "topic": str,
            "subject": str,
            "page": int
        }
    ],
    "confidence": float,    # 0.0-1.0 relevance score
    "query": str,           # Original query
    "filters_applied": {}   # Filters that were used
}
```

### Example Usage
```python
result = mcp_research_probe(
    query="What are the key components of transformer architecture?",
    topic="Deep Learning",
    year=2024,
    k=5
)
```

---

## Tool 2: `search_arxiv`

### Purpose
Search the arXiv preprint repository for academic papers matching a query. Used to discover new research papers that can then be downloaded and indexed.

### Functionality
1. Sends a search query to the arXiv API
2. Retrieves paper metadata (title, abstract, authors, PDF URL, publication date)
3. Attaches user-specified subject and topic for organization
4. Returns a structured list of papers ready for review or download

### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `str` | ✅ | - | Search query for arXiv (supports arXiv query syntax) |
| `subject` | `str` | ❌ | `None` | Subject category for organizing results (e.g., `"Artificial Intelligence"`) |
| `topic` | `str` | ❌ | `None` | Topic subcategory (e.g., `"Healthcare"`, `"Drug Discovery"`) |
| `max_results` | `int` | ❌ | `10` | Maximum number of papers to return |

### Response Schema
```python
{
    "success": bool,
    "query": str,
    "count": int,
    "papers": [
        {
            "title": str,           # Paper title
            "abstract": str,        # Paper abstract
            "authors": [str],       # List of author names
            "year": int,            # Publication year
            "pdf_url": str,         # Direct link to PDF
            "arxiv_url": str,       # arXiv page URL
            "subject": str,         # User-specified subject
            "topic": str            # User-specified topic
        }
    ]
}
```

### Example Usage
```python
result = mcp_search_arxiv(
    query="RAG retrieval augmented generation medical",
    subject="Artificial Intelligence",
    topic="Healthcare",
    max_results=5
)
```

---

## Tool 3: `download_paper`

### Purpose
Download a PDF paper from arXiv and automatically index it in the local vector database, making it immediately available for queries via `research_paper_probe`.

### Functionality
1. Downloads the PDF from the provided URL
2. Saves it to the organized folder structure: `Papers/{subject}/{topic}/{title} - {year}.pdf`
3. Loads and splits the PDF into text chunks
4. Generates embeddings and adds to ChromaDB
5. Reinitializes the RAG tool to include the new paper

### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pdf_url` | `str` | ✅ | - | Direct URL to the PDF file (from arXiv search results) |
| `title` | `str` | ✅ | - | Paper title (used for filename) |
| `year` | `int` | ❌ | `None` | Publication year (included in filename) |
| `subject` | `str` | ❌ | `None` | Subject folder (e.g., `"Artificial Intelligence"`) |
| `topic` | `str` | ❌ | `None` | Topic subfolder (e.g., `"Drug Discovery"`) |
| `add_to_vectordb` | `bool` | ❌ | `True` | Whether to index in vector database after download |

### Response Schema
```python
{
    "success": bool,
    "message": str,         # Status message with details
    "filepath": str,        # Full path to saved PDF
    "filename": str,        # Filename only
    "indexed": bool,        # Whether added to vectordb
    "error": str            # Error message if failed
}
```

### Example Message
```
"Downloaded: Attention Is All You Need - 2017.pdf | Added to vector database ✓ | RAG reinitialized ✓"
```

### Example Usage
```python
result = mcp_download_paper(
    pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
    title="Novel RAG Approach for Medical QA",
    year=2024,
    subject="Artificial Intelligence",
    topic="Healthcare",
    add_to_vectordb=True
)
```

---

## Tool 4: `generate_report`

### Purpose
Generate a professional PDF report from markdown content. Used to create research summaries, findings reports, or documentation based on conversation insights.

### Functionality
1. Takes markdown content and metadata (title, author)
2. Converts markdown to formatted PDF with proper styling
3. Optionally generates a table of contents
4. Saves to the `Reports/` directory with a sanitized filename

### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | `str` | ✅ | - | Title of the report (appears as header) |
| `content` | `str` | ✅ | - | Markdown content for the report body |
| `author` | `str` | ❌ | `"Research Assistant"` | Author name in PDF metadata |
| `filename` | `str` | ❌ | Auto-generated | Custom filename (without `.pdf` extension) |
| `include_toc` | `bool` | ❌ | `True` | Include table of contents |

### Response Schema
```python
{
    "success": bool,
    "message": str,         # Status message
    "filepath": str,        # Full path to generated PDF
    "filename": str,        # Filename with .pdf extension
    "title": str,           # Report title
    "error": str            # Error message if failed
}
```

### Supported Markdown Features
- **Headers**: `#`, `##`, `###` (up to 6 levels)
- **Emphasis**: `**bold**`, `*italic*`, `~~strikethrough~~`
- **Lists**: Ordered (`1.`) and unordered (`-`, `*`)
- **Tables**: Pipe-separated tables with headers
- **Code**: Inline `` `code` `` and fenced code blocks
- **Links**: `[text](url)`
- **Blockquotes**: `> quoted text`

### Example Usage
```python
result = mcp_generate_report(
    title="Quantum Machine Learning Research Summary",
    content="""
## Executive Summary
This report summarizes key findings from recent QML research papers.

## Key Findings
1. **Variational circuits** show promise for NISQ devices
2. **Error mitigation** techniques are critical for practical applications

## Conclusions
QML remains an active research area with growing practical applications.

## Sources
- Paper 1: "Generalization Error Bounds for QML" (2024)
- Paper 2: "Variational Quantum Classifiers" (2023)
""",
    author="Research Assistant",
    include_toc=True
)
```

---

## Tool Workflow Examples

### Workflow 1: Answer a question from existing knowledge
```
User: "What is attention mechanism?"
Agent: Uses research_paper_probe → Returns answer with citations
```

### Workflow 2: Topic not found → Search & Download → Answer
```
User: "Tell me about AI in drug discovery"
Agent: Uses research_paper_probe → No results found
Agent: "Would you like me to search arXiv for papers on this topic?"
User: "Yes"
Agent: Uses search_arxiv → Returns list of papers
User: "Download paper #1 and #3"
Agent: Uses download_paper (×2) → Papers indexed
Agent: Uses research_paper_probe → Returns answer from new papers
```

### Workflow 3: Generate a research report
```
User: "Generate a report summarizing our findings"
Agent: Uses generate_report → Creates PDF with conversation insights
Agent: "Report saved to Reports/Research_Summary_20241207.pdf"
```
