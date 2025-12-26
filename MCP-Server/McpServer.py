"""
MCP Server for Research Assistant Multi-Agent System

Provides the following tools:
1. research_paper_probe - Search and query research papers in the RAG database
2. search_arxiv - Search arXiv for academic papers
3. download_paper - Download PDF papers and auto-index them in the vector database
4. generate_report - Generate a PDF report from markdown content
"""
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError, BaseModel, Field
from markdown_pdf import MarkdownPdf, Section

# Setup environment
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Add RAG SETUP to path for imports
rag_setup_path = Path(__file__).resolve().parent / "RAG SETUP"
sys.path.insert(0, str(rag_setup_path))
sys.path.append('../..')

# Import our tools from RAG SETUP
from RagTool import (
    ResearchProbeArgs,
    ResearchProbeResponse,
    _research_probe_fn,
    rag_tool  # Import the rag_tool instance for startup initialization
)
from corpus_expansion import (
    SearchArxivArgs,
    DownloadPdfArgs,
    search_arxiv,
    download_pdf
)

import openai
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Initialize MCP Server
mcp = FastMCP(
    name="research_assistant_mcp",
    host="0.0.0.0",
    port=8787
)


# ============== Startup Initialization ==============

def initialize_rag_on_startup():
    """
    Initialize the RAG system at server startup.
    This ensures:
    1. VectorDB is loaded or created before any queries
    2. Any new PDFs in the Papers folder are indexed
    """
    print("\n" + "="*60)
    print("🔧 Initializing RAG Knowledge Base...")
    print("="*60)
    
    try:
        # Force initialization of RAG components
        rag_tool._initialize_components()
        
        # Get stats about the knowledge base
        if rag_tool._vectordb is not None:
            try:
                collection = rag_tool._vectordb._collection
                count = collection.count()
                print(f"✓ VectorDB loaded with {count} document chunks")
                
                # Get unique papers
                result = collection.get(include=["metadatas"])
                unique_papers = set()
                for metadata in result.get("metadatas", []):
                    if metadata and "paper_title" in metadata:
                        unique_papers.add(metadata["paper_title"])
                print(f"✓ {len(unique_papers)} unique papers indexed")
                
            except Exception as e:
                print(f"✓ VectorDB initialized (could not get stats: {e})")
        else:
            print("⚠ VectorDB is None after initialization")
            
        print("="*60)
        print("✓ RAG Knowledge Base ready!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"✗ Failed to initialize RAG: {e}")
        print("  The system will attempt lazy initialization on first query.")
        print("="*60 + "\n")


# ============== Tool 1: Research Paper Probe (RAG) ==============

@mcp.tool(
    name="research_paper_probe",
    description=(
        "Search AI research papers in the knowledge base to answer questions. "
        "Filters available: topic ('Agentic AI', 'Finetuning', 'Hierarchical Reasoning Models', 'Deep Learning'), "
        "year (publication year), subject (e.g., 'Artificial Intelligence'). "
        "Returns: topic, category, response (markdown), sources with paper titles and pages, confidence score."
    ),
)
def mcp_research_probe(
    query: str,
    topic: Optional[str] = None,
    subject: Optional[str] = None,
    year: Optional[int] = None,
    k: int = 10,
) -> Dict[str, Any]:
    """
    Search research papers and return structured response.
    """
    try:
        args = ResearchProbeArgs(
            query=query,
            topic=topic,
            subject=subject,
            year=year,
            k=k
        )
    except ValidationError as e:
        return {"error": "validation_error", "details": e.errors()}

    return _research_probe_fn(**args.model_dump(exclude_none=True))


# ============== Tool 2: Search arXiv ==============

@mcp.tool(
    name="search_arxiv",
    description=(
        "Search arXiv for academic papers. "
        "Returns a list of papers with title, abstract, authors, year, pdf_url, subject, and topic. "
        "Use subject and topic to organize results (e.g., subject='Artificial Intelligence', topic='Healthcare')."
    ),
)
def mcp_search_arxiv(
    query: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Search arXiv for papers matching the query.
    """
    try:
        args = SearchArxivArgs(
            query=query,
            subject=subject,
            topic=topic,
            max_results=max_results
        )
    except ValidationError as e:
        return {"error": "validation_error", "details": e.errors()}

    return search_arxiv(**args.model_dump())


# ============== Tool 3: Download Paper ==============

@mcp.tool(
    name="download_paper",
    description=(
        "Download a PDF paper from arXiv and automatically add it to the RAG vector database. "
        "Use the pdf_url and title from search_arxiv results. "
        "Papers are saved to: Papers/subject/topic/title - year.pdf and indexed for future queries."
    ),
)
def mcp_download_paper(
    pdf_url: str,
    title: str,
    year: Optional[int] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    add_to_vectordb: bool = True,
) -> Dict[str, Any]:
    """
    Download a PDF paper and optionally index it in the vector database.
    """
    try:
        args = DownloadPdfArgs(
            pdf_url=pdf_url,
            title=title,
            year=year,
            subject=subject,
            topic=topic,
            add_to_vectordb=add_to_vectordb
        )
    except ValidationError as e:
        return {"error": "validation_error", "details": e.errors()}

    return download_pdf(**args.model_dump())


# ============== Tool 4: Generate PDF Report ==============


# Output directory for generated reports ( Hard coded)
# REPORTS_PATH = Path(__file__).resolve().parent.parent / "Reports"
REPORTS_PATH = Path(os.getenv("REPORTS_DIR", Path(__file__).resolve().parent.parent / "Reports"))

class GenerateReportArgs(BaseModel):
    """Arguments for generating a PDF report."""
    title: str = Field(..., description="Title of the report")
    content: str = Field(..., description="Markdown content for the report body")
    author: Optional[str] = Field(default="Research Assistant", description="Author name")
    filename: Optional[str] = Field(default=None, description="Custom filename (without .pdf extension)")
    include_toc: bool = Field(default=True, description="Include table of contents")


@mcp.tool(
    name="generate_report",
    description=(
        "Generate a PDF report from markdown content. "
        "Use this to create research reports, summaries, or documentation. "
        "Supports markdown formatting: headers, bold, italic, lists, tables, code blocks. "
        "Reports are saved to the Reports/ folder."
    ),
)
def mcp_generate_report(
    title: str,
    content: str,
    author: Optional[str] = "Research Assistant",
    filename: Optional[str] = None,
    include_toc: bool = True,
) -> Dict[str, Any]:
    """
    Generate a PDF report from markdown content.
    """
    try:
        args = GenerateReportArgs(
            title=title,
            content=content,
            author=author,
            filename=filename,
            include_toc=include_toc
        )
    except ValidationError as e:
        return {"error": "validation_error", "details": e.errors()}

    try:
        # Create reports directory if it doesn't exist
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if args.filename:
            safe_filename = "".join(c if c.isalnum() or c in " -_" else "_" for c in args.filename)
        else:
            # Use title + timestamp
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in args.title)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{safe_title}_{timestamp}"
        
        output_path = REPORTS_PATH / f"{safe_filename}.pdf"
        
        # Create PDF
        pdf = MarkdownPdf()
        pdf.meta["title"] = args.title
        pdf.meta["author"] = args.author or "Research Assistant"
        
        # Add title header to content
        full_content = f"# {args.title}\n\n{args.content}"
        
        # Add section with optional TOC
        pdf.add_section(Section(full_content, toc=args.include_toc))
        
        # Save PDF
        pdf.save(str(output_path))
        
        return {
            "success": True,
            "message": f"Report generated successfully",
            "filepath": str(output_path),
            "filename": f"{safe_filename}.pdf",
            "title": args.title
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate report: {str(e)}"
        }


# ============== Server Entry Point ==============

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting Research Assistant MCP Server...")
    print("="*60)
    print("\nAvailable tools:")
    print("  1. research_paper_probe - Query the RAG knowledge base")
    print("  2. search_arxiv - Search arXiv for papers")
    print("  3. download_paper - Download and index papers")
    print("  4. generate_report - Generate PDF reports from markdown")
    print()
    
    # Initialize RAG system BEFORE starting the server
    # This ensures all PDFs are indexed before accepting queries
    initialize_rag_on_startup()
    
    print("🌐 Server starting on http://0.0.0.0:8787")
    print("="*60 + "\n")
    
    mcp.run(transport="sse")