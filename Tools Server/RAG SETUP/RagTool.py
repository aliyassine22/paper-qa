from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from pathlib import Path
from .Rag import RAGSearchTool

# Paths relative to this file's location (RAG SETUP directory)
base_dir = Path(__file__).resolve().parent
papers_path = base_dir / "Papers"
vectordb_path = base_dir / "VectorDB"

rag_tool = RAGSearchTool(
    default_papers_path=papers_path,
    persist_directory=vectordb_path,
    collection_name="research_papers"
)


class SourceReference(BaseModel):
    """A reference to a source document."""
    paper_title: Optional[str] = Field(None, description="Title of the research paper")
    year: Optional[int] = Field(None, description="Publication year")
    topic: Optional[str] = Field(None, description="Topic area")
    subject: Optional[str] = Field(None, description="Subject area")
    page: Optional[int] = Field(None, description="Page number")


class ResearchProbeResponse(BaseModel):
    """Structured response from the research RAG tool."""
    topic: str = Field(..., description="The searched topic")
    category: str = Field(default="General", description="Category: 'Agentic AI', 'Finetuning', 'Hierarchical Reasoning Models', 'General', or 'Not Found'")
    response: str = Field(..., description="Answer in markdown format")
    sources: List[SourceReference] = Field(default_factory=list, description="Source references")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score (0-1)")
    query: str = Field(..., description="Original query")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class ResearchProbeArgs(BaseModel):
    """Input arguments for the research paper probe tool."""
    query: str = Field(..., description="The research question to answer")
    topic: Optional[str] = Field(default=None, description="Topic filter: 'Agentic AI', 'Finetuning', 'Hierarchical Reasoning Models'")
    subject: Optional[str] = Field(default=None, description="Subject filter (e.g., 'Artificial Intelligence')")
    year: Optional[int] = Field(default=None, description="Publication year filter", ge=1900, le=2100)
    k: int = Field(default=10, ge=1, le=50, description="Number of documents to retrieve")



def _research_probe_fn(
    query: str,
    topic: Optional[str] = None,
    subject: Optional[str] = None,
    year: Optional[int] = None,
    k: int = 10
) -> Dict[str, Any]:
    """Search research papers and return structured response."""
    
    filters_applied = {key: val for key, val in [("topic", topic), ("subject", subject), ("year", year)] if val}
    category = topic if topic else "General"
    
    try:
        # Initialize and get docs directly from vector store
        rag_tool._initialize_components()
        metadata_filter = rag_tool._build_metadata_filter(subject, topic, year)
        
        if metadata_filter:
            docs = rag_tool._vectordb.similarity_search(query, k=k, filter=metadata_filter)
        else:
            docs = rag_tool._vectordb.similarity_search(query, k=k)
        
        # Generate answer
        answer = rag_tool._generate_answer_from_docs(query, docs)
        
        # Build sources directly from document metadata (no parsing!)
        sources = []
        for doc in docs:
            md = doc.metadata or {}
            sources.append(SourceReference(
                paper_title=md.get("paper_title"),
                year=md.get("year"),
                topic=md.get("topic"),
                subject=md.get("subject"),
                page=(md.get("page", 0) + 1) if md.get("page") is not None else None
            ))
            # Infer category from first source if not filtered
            if not topic and md.get("topic") and category == "General":
                category = md.get("topic")
        
        # Calculate confidence
        confidence = min(1.0, len(sources) * 0.1 + (0.3 if answer and "don't know" not in answer.lower() else 0.0))
        if not sources or "don't know" in answer.lower():
            category = "Not Found" if not topic else category
        
        # Format markdown response
        md_response = f"## Answer\n\n{answer or '*No answer available.*'}\n"
        if sources:
            md_response += "\n## Sources\n\n" + "\n".join(
                f"{i}. *{s.paper_title}* ({s.year}) p.{s.page} [{s.topic}]" 
                for i, s in enumerate(sources, 1) if s.paper_title
            )
        
        return ResearchProbeResponse(
            topic=query.split("?")[0][:50], category=category, response=md_response,
            sources=sources, confidence=confidence, query=query, filters_applied=filters_applied
        ).model_dump()
        
    except Exception as e:
        return ResearchProbeResponse(
            topic=query[:50], category="Not Found", response=f"## Error\n\n{str(e)}",
            sources=[], confidence=0.0, query=query, filters_applied=filters_applied
        ).model_dump()


research_probe = StructuredTool.from_function(
    name="research_paper_probe",
    description="""Search AI research papers to answer questions.

Filters:
- topic: 'Agentic AI', 'Finetuning', 'Hierarchical Reasoning Models'
- year: Publication year (e.g., 2024, 2025)
- subject: Subject area (e.g., 'Artificial Intelligence')

Returns: topic, category, response (markdown), sources, confidence (0-1)""",
    func=_research_probe_fn,
    args_schema=ResearchProbeArgs,
)
