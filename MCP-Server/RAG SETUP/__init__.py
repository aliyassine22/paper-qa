"""
RAG SETUP Package

Provides tools for:
1. RAG-based research paper search (RagTool)
2. Corpus expansion via arXiv (corpus_expansion)
"""

from .Rag import RAGSearchTool
from .RagTool import (
    research_probe,
    ResearchProbeArgs,
    ResearchProbeResponse,
    SourceReference,
    _research_probe_fn
)
from .corpus_expansion import (
    search_arxiv,
    download_pdf,
    SearchArxivArgs,
    DownloadPdfArgs,
    PAPERS_PATH,
    VECTORDB_PATH
)

__all__ = [
    # RAG Search
    "RAGSearchTool",
    "research_probe",
    "ResearchProbeArgs", 
    "ResearchProbeResponse",
    "SourceReference",
    "_research_probe_fn",
    # Corpus Expansion
    "search_arxiv",
    "download_pdf",
    "SearchArxivArgs",
    "DownloadPdfArgs",
    "PAPERS_PATH",
    "VECTORDB_PATH",
]
