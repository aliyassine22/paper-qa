"""
Research Assistant API - FastAPI backend for the Research Assistant Agent.

Endpoints:
- POST /chat - Send a message and get a response (maintains conversation)
- POST /chat/single - Send a single message without history
- POST /clear - Clear conversation history
- GET /health - Health check
- GET /status - Get assistant status
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Add Agent SetUp to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Agent SetUp"))
from agent import ResearchAssistant


# ============== Global State ==============

assistant: Optional[ResearchAssistant] = None


# ============== Lifespan Management ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize assistant on startup, cleanup on shutdown."""
    global assistant
    
    print("🚀 Starting Research Assistant API...")
    
    # Initialize the research assistant
    assistant = ResearchAssistant(
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8787/sse"),
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini")
    )
    
    success = await assistant.initialize()
    if success:
        print("✓ Research Assistant ready!")
    else:
        print("⚠ Research Assistant failed to initialize - MCP server may not be running")
    
    yield  # App runs here
    
    # Cleanup on shutdown
    print("🛑 Shutting down Research Assistant API...")
    if assistant:
        await assistant.close()
    print("✓ Cleanup complete")


# ============== FastAPI App ==============

app = FastAPI(
    title="Research Assistant API",
    description="AI-powered research assistant with RAG and arXiv integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Request/Response Models ==============

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User's message to the assistant")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    is_ready: bool
    mcp_connected: bool
    tools_loaded: int
    conversation_length: int


# ============== Endpoints ==============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get the current status of the research assistant."""
    if not assistant:
        return StatusResponse(
            is_ready=False,
            mcp_connected=False,
            tools_loaded=0,
            conversation_length=0
        )
    
    return StatusResponse(
        is_ready=assistant.is_ready,
        mcp_connected=assistant.mcp_manager.is_connected if assistant.mcp_manager else False,
        tools_loaded=len(assistant.tools),
        conversation_length=len(assistant.conversation_history)
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the assistant (maintains conversation history).
    
    The assistant will:
    1. Check the local knowledge base first
    2. Search arXiv if needed
    3. Download papers on request
    4. Answer questions using available papers
    """
    if not assistant or not assistant.is_ready:
        raise HTTPException(
            status_code=503, 
            detail="Research Assistant not initialized. Make sure MCP server is running."
        )
    
    try:
        response = await assistant.chat(request.message)
        return ChatResponse(response=response, success=True)
    except Exception as e:
        return ChatResponse(
            response="",
            success=False,
            error=str(e)
        )


@app.post("/clear")
async def clear_history():
    """Clear the conversation history."""
    if assistant:
        assistant.clear_history()
    return {"message": "Conversation history cleared"}


# ============== Run with Uvicorn ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disabled for stability; enable for development
    )