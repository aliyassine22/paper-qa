"""
Corpus Expansion Tools - arXiv search and PDF download with automatic vectordb indexing.
"""
import os
import arxiv
import re
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# Max filename length - reduced to ensure total path stays under Windows 260 char limit
MAX_FILENAME_LENGTH = 100

# Hard Coded paths that won't work in case of bind mounting
# Paths relative to this file's location (RAG SETUP directory)
# BASE_DIR = Path(__file__).resolve().parent
# PAPERS_PATH = BASE_DIR / "Papers"
# VECTORDB_PATH = BASE_DIR / "VectorDB"

PAPERS_PATH = Path(os.getenv("PAPERS_DIR", Path(__file__).resolve().parent / "Papers"))
VECTORDB_PATH = Path(os.getenv("VECTORDB_DIR", Path(__file__).resolve().parent / "VectorDB"))


# ============== Pydantic Schemas ==============

class SearchArxivArgs(BaseModel):
    """Input arguments for arXiv search."""
    query: str = Field(..., description="Search query for finding papers")
    subject: Optional[str] = Field(default=None, description="Subject area (e.g., 'Artificial Intelligence')")
    topic: Optional[str] = Field(default=None, description="Topic within subject (e.g., 'Healthcare', 'NLP')")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results to return")


class DownloadPdfArgs(BaseModel):
    """Input arguments for PDF download."""
    pdf_url: str = Field(..., description="The PDF URL from the search results")
    title: str = Field(..., description="Title of the paper")
    year: Optional[int] = Field(default=None, description="Publication year")
    subject: Optional[str] = Field(default=None, description="Subject area for organizing the download")
    topic: Optional[str] = Field(default=None, description="Topic for organizing the download")
    add_to_vectordb: bool = Field(default=True, description="Whether to add the paper to the RAG vector database")


class PaperResult(BaseModel):
    """A single paper result from search."""
    source: str = "arxiv"
    id: str
    title: str
    abstract: str
    year: int
    venue: str = "arXiv"
    authors: List[str]
    citations: Optional[int] = None
    pdf_url: str
    landing_url: str
    subject: Optional[str] = None
    topic: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from arXiv search."""
    query: str
    subject: Optional[str]
    topic: Optional[str]
    count: int
    papers: List[Dict[str, Any]]


class DownloadResponse(BaseModel):
    """Response from PDF download."""
    success: bool
    file_path: Optional[str] = None
    vectordb_indexed: bool = False
    message: str


# ============== Helper Functions ==============

def sanitize_filename(name: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Remove invalid characters from filename and limit length."""
    # Remove characters not allowed in Windows filenames: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/:*?"<>|]', '', name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Trim and limit length
    return sanitized.strip()[:max_length]


def shorten_title(title: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Shorten a paper title intelligently.
    - If ≤ max_length: return as-is
    - If > max_length and has ':': use part before ':'
    - Otherwise: crop at max_length
    """
    if len(title) <= max_length:
        return title
    
    # Try to use the main title (before the colon)
    if ':' in title:
        main_title = title.split(':')[0].strip()
        if len(main_title) <= max_length and len(main_title) > 10:
            return main_title
    
    # Fallback: crop at max_length
    return title[:max_length].strip()


def _extract_paper_metadata(file_path: Path, base_path: Path) -> dict:
    """
    Extract metadata from a paper's file path.
    Expected structure: base_path/Subject/Topic/title - year.pdf
    """
    metadata = {
        "subject": "Unknown",
        "topic": "Unknown", 
        "paper_title": file_path.stem,
        "year": None,
        "file_name": file_path.name,
    }
    
    try:
        rel_path = file_path.relative_to(base_path)
        parts = rel_path.parts
        
        if len(parts) >= 3:
            metadata["subject"] = parts[0]
            metadata["topic"] = parts[1]
        elif len(parts) == 2:
            metadata["subject"] = parts[0]
            
        # Extract year from filename: "title - year.pdf"
        stem = file_path.stem
        if " - " in stem:
            title_part, year_part = stem.rsplit(" - ", 1)
            metadata["paper_title"] = title_part.strip()
            try:
                metadata["year"] = int(year_part.strip())
            except ValueError:
                pass
                
    except Exception:
        pass
    
    return metadata


def _add_to_vectordb(file_path: Path, papers_base_path: Path = PAPERS_PATH, vectordb_path: Path = VECTORDB_PATH) -> bool:
    """
    Add a downloaded PDF to the vector database.
    """
    try:
        # Load the PDF
        loader = PyMuPDFLoader(str(file_path))
        raw_docs = loader.load()
        
        # Extract and add metadata
        paper_metadata = _extract_paper_metadata(file_path, papers_base_path)
        for doc in raw_docs:
            doc.metadata.update(paper_metadata)
            doc.metadata.update({
                "doc_id": file_path.stem,
                "relpath": str(file_path.relative_to(papers_base_path)) if papers_base_path in file_path.parents or file_path.parent == papers_base_path else file_path.name
            })
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=250)
        split_docs = splitter.split_documents(raw_docs)
        
        # Load existing vectordb or create new one
        embeddings = OpenAIEmbeddings()
        
        if (vectordb_path / "chroma.sqlite3").exists():
            vectordb = Chroma(
                collection_name="research_papers",
                embedding_function=embeddings,
                persist_directory=str(vectordb_path),
            )
            vectordb.add_documents(split_docs)
        else:
            vectordb_path.mkdir(parents=True, exist_ok=True)
            Chroma.from_documents(
                documents=split_docs,
                embedding=embeddings,
                collection_name="research_papers",
                persist_directory=str(vectordb_path),
            )
        
        return True
    except Exception as e:
        print(f"Warning: Failed to add document to vectordb: {e}")
        return False


# ============== Main Tool Functions ==============

def search_arxiv(
    query: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search arXiv for papers.
    
    Args:
        query: Search query string
        subject: Subject area (e.g., 'Artificial Intelligence')
        topic: Topic within subject (e.g., 'Healthcare', 'NLP')
        max_results: Maximum number of results to return
        
    Returns:
        Dict with query info and list of papers
    """
    # Build enhanced query with subject/topic if provided
    full_query = query
    if subject:
        full_query = f"{subject} {full_query}"
    if topic:
        full_query = f"{topic} {full_query}"
    
    search = arxiv.Search(
        query=full_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    
    papers = []
    for result in search.results():
        papers.append({
            "source": "arxiv",
            "id": result.entry_id,
            "title": result.title,
            "abstract": result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
            "year": result.published.year,
            "venue": "arXiv",
            "authors": [a.name for a in result.authors[:5]],  # Limit authors for readability
            "pdf_url": result.pdf_url,
            "landing_url": result.entry_id,
            "subject": subject,
            "topic": topic,
        })
    
    return {
        "query": query,
        "subject": subject,
        "topic": topic,
        "count": len(papers),
        "papers": papers
    }


def download_pdf(
    pdf_url: str,
    title: str,
    year: Optional[int] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    add_to_vectordb: bool = True
) -> Dict[str, Any]:
    """
    Download PDF for a paper and optionally add it to the vector database.
    
    Args:
        pdf_url: URL to the PDF
        title: Title of the paper
        year: Publication year
        subject: Subject area for organizing the download
        topic: Topic for organizing the download
        add_to_vectordb: Whether to automatically add the paper to the vector DB
    
    Returns:
        Dict with download status and file path
    """
    if not pdf_url:
        return {
            "success": False,
            "file_path": None,
            "vectordb_indexed": False,
            "message": "No PDF URL provided"
        }
    
    try:
        # Build path: PAPERS_PATH/subject/topic/
        subject_val = subject or "General"
        topic_val = topic or "Uncategorized"
        
        # Sanitize directory names
        subject_dir = sanitize_filename(subject_val, max_length=50)
        topic_dir = sanitize_filename(topic_val, max_length=50)
        
        # Use pathlib for cross-platform path handling
        full_dir = PAPERS_PATH / subject_dir / topic_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        shortened = shorten_title(title)
        base_name = sanitize_filename(shortened)
        
        # Add year and .pdf extension
        filename = f"{base_name} - {year}.pdf" if year else f"{base_name}.pdf"
        file_path = full_dir / filename

        # Download the PDF
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)
        
        # Add to vector database if requested
        vectordb_indexed = False
        rag_reinitialized = False
        if add_to_vectordb:
            vectordb_indexed = _add_to_vectordb(file_path, papers_base_path=PAPERS_PATH)
            
            # If vectordb was updated, reinitialize the RAG tool to pick up new documents
            if vectordb_indexed:
                try:
                    from RagTool import rag_tool
                    rag_tool._initialize_components()
                    rag_reinitialized = True
                except Exception as e:
                    # If reinitialization fails, log but don't break the flow
                    print(f"Warning: RAG reinit failed: {e}")
        
        # Build result message
        message = f"Downloaded: {file_path}"
        if vectordb_indexed:
            message += " | Added to vector database ✓"
            if rag_reinitialized:
                message += " | RAG reinitialized ✓"
        
        return {
            "success": True,
            "file_path": str(file_path),
            "vectordb_indexed": vectordb_indexed,
            "message": message
        }
        
    except requests.RequestException as e:
        return {
            "success": False,
            "file_path": None,
            "vectordb_indexed": False,
            "message": f"Download failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "vectordb_indexed": False,
            "message": f"Error: {str(e)}"
        }