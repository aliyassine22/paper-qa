import os
import re
import shutil
import threading
from pathlib import Path
from typing import Any, List, Optional, Sequence, Type, Union, Annotated
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.conversational_retrieval.base import BaseConversationalRetrievalChain
from langchain.chains.query_constructor.base import AttributeInfo
from pydantic import BaseModel, Field 
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.tools import BaseTool


def educated_retriever(
    llm: BaseLanguageModel,
    metadata_field_info: Sequence[Union[AttributeInfo, dict]],
    document_content: str,
    vectordb: VectorStore,
    chain_type: str = "stuff",
) -> BaseConversationalRetrievalChain:
    """
    Builds a conversational retrieval QA pipeline by combining a SelfQueryRetriever
    with a ConversationalRetrievalChain.
    """
    retriever = SelfQueryRetriever.from_llm(
        llm,
        vectordb,
        document_contents=document_content,
        metadata_field_info=metadata_field_info,
        verbose=True,
    )
    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        chain_type=chain_type,
        return_source_documents=True,
    )
    return qa


class RAGSearchInput(BaseModel):
    """Input schema for the RAG search tool"""
    query: str = Field(..., description="The query to search for in the research papers")
    papers_path: Optional[str] = Field(default=None, description="Path to the research papers directory")
    subject: Optional[str] = Field(default=None, description="Subject area (e.g., 'Artificial Intelligence')")
    topic: Optional[str] = Field(default=None, description="Topic within the subject (e.g., 'Agentic AI', 'Finetuning')")
    year: Optional[int] = Field(default=None, description="Publication year of the paper")
    chain_type: Optional[str] = Field(default="stuff", description="Chain type for the QA system")
    
    
class RAGSearchTool(BaseTool):
    name: Annotated[str, Field(description="Name of the tool")] = "research_paper_search"
    description: Annotated[str, Field(description="Description of the tool")] = """
    Search through research papers using an educated RAG approach.
    Uses metadata filtering (subject, topic, year, paper_title) and conversational capabilities 
    to provide relevant information from AI research papers.
    """
    args_schema: Type[BaseModel] = RAGSearchInput
    default_papers_path: Path
    persist_directory: Path
    collection_name: str = "research_papers"

    _qa_chain: Any = None
    _vectordb: Any = None
    _embeddings: Any = None
    _init_lock: Any = None
    _llm: Any = None

    def __init__(
        self,
        default_papers_path: Optional[Path] = None,
        persist_directory: Optional[Path] = None,
        collection_name: str = "research_papers",
    ):
        # Use paths relative to this file if not provided
        base_dir = Path(__file__).resolve().parent
        final_papers_path = Path(default_papers_path).resolve() if default_papers_path else base_dir / "Papers"
        final_persist_dir = Path(persist_directory).resolve() if persist_directory else base_dir / "VectorDB"
        super().__init__(
            default_papers_path=final_papers_path,
            persist_directory=final_persist_dir,
            collection_name=collection_name
        )

        self._embeddings = OpenAIEmbeddings()
        self._init_lock = threading.Lock()

    def _extract_paper_metadata(self, file_path: Path, base_path: Path) -> dict:
        """
        Extract metadata from research paper filename and path.
        Expected filename format: {paper_title} - {year} - {description}.pdf
        Expected path structure: Papers/Subject/Topic/filename.pdf
        """
        metadata = {
            "subject": "Artificial Intelligence",  # Default for now
            "topic": None,
            "paper_title": None,
            "year": None,
            "file_name": file_path.name,
            "file_path": str(file_path),
        }
        
        # Extract subject and topic from directory structure
        try:
            rel_path = file_path.relative_to(base_path)
            parts = rel_path.parts
            # Expected: Subject/Topic/filename.pdf
            if len(parts) >= 2:
                metadata["subject"] = parts[0]  # e.g., "Artificial Intelligence"
            if len(parts) >= 3:
                metadata["topic"] = parts[1]  # e.g., "Agentic AI", "Finetuning"
        except ValueError:
            pass
        
        # Parse filename: {title} - {year} - {description}.pdf
        filename_stem = file_path.stem  # Remove .pdf extension
        
        # Split by " - " to get parts
        parts = [p.strip() for p in filename_stem.split(" - ")]
        
        if len(parts) >= 1:
            metadata["paper_title"] = parts[0]
        
        if len(parts) >= 2:
            # Try to extract year from second part
            year_match = re.search(r"(\d{4})", parts[1])
            if year_match:
                metadata["year"] = int(year_match.group(1))
            else:
                # If no year in second part, it might be part of title or description
                metadata["paper_title"] = f"{parts[0]} - {parts[1]}"
        
        return metadata

    def _get_indexed_papers(self) -> set:
        """Get the set of paper file paths already indexed in the VectorDB."""
        if self._vectordb is None:
            return set()
        
        try:
            # Get all documents from the collection
            collection = self._vectordb._collection
            result = collection.get(include=["metadatas"])
            
            # Extract unique file paths from metadata
            indexed_paths = set()
            for metadata in result.get("metadatas", []):
                if metadata and "file_path" in metadata:
                    indexed_paths.add(metadata["file_path"])
            
            return indexed_paths
        except Exception as e:
            print(f"Warning: Could not get indexed papers: {e}")
            return set()

    def _get_all_pdfs_in_papers_dir(self) -> set:
        """Get the set of all PDF file paths in the Papers directory."""
        pdf_paths = set()
        for pdf_file in self.default_papers_path.rglob("*.pdf"):
            pdf_paths.add(str(pdf_file.resolve()))
        return pdf_paths

    def _index_missing_papers(self, missing_paths: set):
        """Index papers that are in the Papers directory but not in VectorDB."""
        if not missing_paths:
            return
        
        print(f"📄 Found {len(missing_paths)} new paper(s) to index...")
        
        # Batch size for embedding to avoid OpenAI token limits
        BATCH_SIZE = 400
        
        for pdf_path in missing_paths:
            try:
                pdf_file = Path(pdf_path)
                print(f"  → Indexing: {pdf_file.name}")
                
                # Load the PDF
                loader = PyMuPDFLoader(str(pdf_file))
                raw_docs = loader.load()
                
                # Extract and add metadata
                paper_metadata = self._extract_paper_metadata(pdf_file, self.default_papers_path)
                for d in raw_docs:
                    d.metadata.update(paper_metadata)
                    d.metadata.update({
                        "doc_id": pdf_file.stem,
                        "relpath": str(pdf_file.relative_to(self.default_papers_path)) 
                            if self.default_papers_path in pdf_file.parents or pdf_file.parent == self.default_papers_path 
                            else pdf_file.name
                    })
                
                # Split into chunks
                splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=250)
                split_docs = splitter.split_documents(raw_docs)
                
                # Add to vectordb in batches to avoid token limits
                total_chunks = len(split_docs)
                if total_chunks > BATCH_SIZE:
                    print(f"    Large paper: {total_chunks} chunks, indexing in batches...")
                    for i in range(0, total_chunks, BATCH_SIZE):
                        batch = split_docs[i:i + BATCH_SIZE]
                        self._vectordb.add_documents(batch)
                    print(f"    ✓ Added {total_chunks} chunks in {(total_chunks + BATCH_SIZE - 1) // BATCH_SIZE} batches")
                else:
                    self._vectordb.add_documents(split_docs)
                    print(f"    ✓ Added {total_chunks} chunks")
                
            except Exception as e:
                print(f"    ✗ Failed to index {pdf_path}: {e}")
        
        print(f"✓ Finished indexing new papers")

    def _check_and_index_missing_papers(self):
        """Check for papers in Papers directory that are not indexed and index them."""
        if self._vectordb is None:
            return
            
        indexed_papers = self._get_indexed_papers()
        all_pdfs = self._get_all_pdfs_in_papers_dir()
        missing_papers = all_pdfs - indexed_papers
        
        if missing_papers:
            self._index_missing_papers(missing_papers)
        else:
            print("✓ All papers in Papers directory are already indexed")

    def _load_or_build_vectordb(self):
        db_file = self.persist_directory / "chroma.sqlite3"
        if db_file.exists() and self._vectordb is None:
            self._vectordb = Chroma(
                persist_directory=str(self.persist_directory),
                collection_name=self.collection_name,
                embedding_function=self._embeddings,
            )
            # Check for new papers that need to be indexed
            self._check_and_index_missing_papers()
            return

        if self._vectordb is not None:
            return

        loader = DirectoryLoader(
            str(self.default_papers_path),
            glob="**/*.pdf",
            loader_cls=PyMuPDFLoader,
        )
        raw_docs = loader.load()

        for d in raw_docs:
            p = Path(d.metadata["source"])
            
            # Extract research paper metadata
            paper_metadata = self._extract_paper_metadata(p, self.default_papers_path)
            d.metadata.update(paper_metadata)
            
            # Add additional useful metadata
            d.metadata.update({
                "doc_id": p.stem,
                "relpath": str(p.relative_to(self.default_papers_path)) if self.default_papers_path in p.parents or p.parent == self.default_papers_path else p.name
            })

        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=250)
        split_docs = splitter.split_documents(raw_docs)

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Batch documents to avoid OpenAI token limits (max 300k tokens per request)
        # Estimate ~500 tokens per chunk on average, so batch ~400 docs at a time to be safe
        BATCH_SIZE = 400
        total_docs = len(split_docs)
        
        print(f"Indexing {total_docs} document chunks in batches of {BATCH_SIZE}...")
        
        for i in range(0, total_docs, BATCH_SIZE):
            batch = split_docs[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"  → Batch {batch_num}/{total_batches}: Embedding {len(batch)} chunks...")
            
            if i == 0:
                # First batch: create the vectordb
                self._vectordb = Chroma.from_documents(
                    documents=batch,
                    embedding=self._embeddings,
                    collection_name=self.collection_name,
                    persist_directory=str(self.persist_directory),
                )
            else:
                # Subsequent batches: add to existing vectordb
                self._vectordb.add_documents(batch)
        
        print(f"✓ Successfully indexed {total_docs} chunks from {len(raw_docs)} pages")

    def _initialize_components(self):
        """Initialize the RAG components if not already initialized."""
        if self._qa_chain is not None:
            return
        with self._init_lock:
            if self._qa_chain is not None:
                return
            self._load_or_build_vectordb()
            metadata_field_info = [
                AttributeInfo(
                    name="subject", 
                    type="string", 
                    description="Subject area of the research paper (e.g., 'Artificial Intelligence', 'Communication Systems', 'Security')"
                ),
                AttributeInfo(
                    name="topic", 
                    type="string", 
                    description="Specific topic within the subject (e.g., 'Agentic AI', 'Finetuning', 'Hierarchical Reasoning Models')"
                ),
                AttributeInfo(
                    name="paper_title", 
                    type="string", 
                    description="Title of the research paper"
                ),
                AttributeInfo(
                    name="year", 
                    type="integer", 
                    description="Publication year of the research paper"
                ),
                AttributeInfo(
                    name="file_name", 
                    type="string", 
                    description="The filename of the PDF document"
                ),
            ]
            self._llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")
            self._qa_chain = educated_retriever(
                llm=self._llm,
                metadata_field_info=metadata_field_info,
                document_content="Research papers on Artificial Intelligence topics including Agentic AI, Finetuning, and Hierarchical Reasoning Models",
                vectordb=self._vectordb,
                chain_type="stuff",
            )

    def _build_metadata_filter(self, subject: Optional[str], topic: Optional[str], year: Optional[int]) -> Optional[dict]:
        """
        Build a Chroma-compatible metadata filter from the provided parameters.
        Uses $and to combine multiple conditions.
        """
        conditions = []
        
        if subject:
            conditions.append({"subject": {"$eq": subject}})
        if topic:
            conditions.append({"topic": {"$eq": topic}})
        if year:
            conditions.append({"year": {"$eq": year}})
        
        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _generate_answer_from_docs(self, query: str, docs: List) -> str:
        """Generate an answer from retrieved documents using the LLM."""
        if not docs:
            return "No documents found matching the specified filters."
        
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        
        from langchain_core.prompts import ChatPromptTemplate
        
        prompt = ChatPromptTemplate.from_template(
            """Use the following pieces of context to answer the question at the end. 
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Question: {question}

Answer:"""
        )
        
        chain = prompt | self._llm
        response = chain.invoke({"context": context, "question": query})
        return response.content.strip()

    def _format_sources(self, docs: List) -> List[str]:
        """Format source documents into a list of source strings."""
        sources = []
        for i, doc in enumerate(docs, 1):
            md = doc.metadata or {}
            parts = [f"[{i}]"]
            
            if md.get("paper_title"):
                parts.append(f"'{md.get('paper_title')}'")
            if md.get("year"):
                parts.append(f"({md.get('year')})")
            if md.get("topic"):
                parts.append(f"[{md.get('topic')}]")
            if md.get("subject"):
                parts.append(f"- {md.get('subject')}")
            
            page = md.get("page")
            if page is not None:
                parts.append(f"p.{page + 1}")
            
            sources.append(" ".join(parts))
        return sources

    def _run(
        self,
        query: str,
        papers_path: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        year: Optional[int] = None,
        k: int = 10,
    ) -> str:
        """
        Executes the RAG search by applying explicit metadata filters
        to ensure accurate filtering by subject, topic, and year.
        When explicit filters are provided, uses direct vector store retrieval
        instead of SelfQueryRetriever to guarantee filter accuracy.
        """
        if papers_path:
            new_path = Path(papers_path)
            if self.default_papers_path != new_path:
                self.default_papers_path = new_path
                self._qa_chain = None
                self._vectordb = None
                if self.persist_directory.exists():
                    shutil.rmtree(self.persist_directory)

        self._initialize_components()

        # Build explicit metadata filter for Chroma
        metadata_filter = self._build_metadata_filter(subject, topic, year)

        try:
            # If explicit filters are provided, bypass SelfQueryRetriever
            # and use direct vector store retrieval with guaranteed filters
            if metadata_filter:
                # Use direct similarity search with explicit filter
                docs = self._vectordb.similarity_search(
                    query,
                    k=k,
                    filter=metadata_filter
                )
                
                answer = self._generate_answer_from_docs(query, docs)
                sources = self._format_sources(docs)
                
                return f"Answer: {answer}\n\nSources:\n" + ("\n".join(sources) if sources else "(none)")
            
            else:
                # No explicit filters - use the SelfQueryRetriever for intelligent querying
                retr = self._qa_chain.retriever
                orig_kwargs = retr.search_kwargs.copy()
                try:
                    retr.search_kwargs["k"] = k
                    response = self._qa_chain({"question": query, "chat_history": []})

                    answer = (response.get("answer") or "").strip()
                    sources = self._format_sources(response.get("source_documents", []) or [])

                    return f"Answer: {answer}\n\nSources:\n" + ("\n".join(sources) if sources else "(none)")
                finally:
                    if self._qa_chain:
                        self._qa_chain.retriever.search_kwargs = orig_kwargs
                        
        except Exception as e:
            return f"Error: {e!r}"