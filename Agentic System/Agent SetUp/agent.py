"""
Research Assistant Agent - LangGraph agent with MCP tools integration.

This module provides:
- Agent class: LangGraph-based agent with tool calling
- MCPConnectionManager: Manages connection to MCP server
- ResearchAssistant: High-level interface combining agent + MCP tools
"""

import operator
from typing import List, Annotated, TypedDict, Optional, Any
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from mcp import ClientSession
from mcp.client.sse import sse_client


# ============== Agent State & Class ==============

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


class Agent:
    """LangGraph-based agent with tool calling capabilities."""

    def __init__(self, model, tools, system=""):
        self.system = system
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm",
            self.exists_action,
            {True: "action", False: END}
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile()
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        want_tools = isinstance(result, AIMessage) and bool(getattr(result, "tool_calls", None))
        return want_tools

    async def call_openai(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = await self.model.ainvoke(messages)
        return {'messages': [message]}

    async def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            if t['name'] not in self.tools:
                print("\n ....bad tool name....")
                result = "bad tool name, retry"
            else:
                result = await self.tools[t['name']].ainvoke(t['args'])
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}


# ============== MCP Connection Manager ==============

class MCPConnectionManager:
    """Manages persistent connection to MCP server."""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8787/sse"):
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> ClientSession:
        """Initialize connection to MCP server. Returns existing session if already connected."""
        if self._initialized and self.session:
            return self.session

        self.client = sse_client(self.server_url)
        read_stream, write_stream = await self.client.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        self._initialized = True
        return self.session
    
    async def close(self):
        """Close the MCP connection."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self.client:
            await self.client.__aexit__(None, None, None)
        self._initialized = False
        self.session = None
    
    @property
    def is_connected(self) -> bool:
        return self._initialized and self.session is not None


# ============== Research Assistant ==============

# System prompt for the research assistant
RESEARCH_ASSISTANT_PROMPT = """You are a research assistant that helps users find information from academic papers.

You have access to these tools:
1. research_paper_probe - Search the local RAG knowledge base of research papers
2. search_arxiv - Search arXiv for new academic papers  
3. download_paper - Download papers from arXiv and add them to the knowledge base

WORKFLOW:
1. When a user asks about a topic, FIRST use research_paper_probe to check the local knowledge base.
2. If NO relevant results are found (low confidence or empty sources), inform the user and ASK if they want you to search arXiv for papers on this topic.
3. If the user says yes, use search_arxiv to find relevant papers. Present the results as a numbered list with title, authors, year, and a brief abstract summary.
4. Ask the user which papers (up to 3) they would like to add to the collection.
5. When the user selects papers, use download_paper for each selected paper to download and index them.
6. After downloading, use research_paper_probe again to answer the original question using the newly added papers.

Always cite your sources with paper titles and years."""


class ResearchAssistant:
    """
    High-level Research Assistant that combines LangGraph Agent with MCP tools.
    
    Usage:
        assistant = ResearchAssistant()
        await assistant.initialize()
        response = await assistant.chat("What are recent advances in LLMs?")
    """
    
    def __init__(
        self,
        mcp_server_url: str = "http://127.0.0.1:8787/sse",
        model_name: str = "gpt-4o-mini",
        system_prompt: str = RESEARCH_ASSISTANT_PROMPT
    ):
        self.mcp_server_url = mcp_server_url
        self.model_name = model_name
        self.system_prompt = system_prompt
        
        self.mcp_manager: Optional[MCPConnectionManager] = None
        self.session: Optional[ClientSession] = None
        self.agent: Optional[Agent] = None
        self.tools: List[StructuredTool] = []
        self.conversation_history: List[AnyMessage] = []
        self._initialized = False
    
    def _create_mcp_tool_wrapper(self, tool_name: str):
        """Create a closure to capture the tool name for async invocation."""
        async def mcp_tool_wrapper(**kwargs):
            if not self.session:
                return "Error: MCP session not initialized"
            result = await self.session.call_tool(tool_name, arguments=kwargs)
            if result.content:
                return result.content[0].text
            return "No content returned"
        return mcp_tool_wrapper
    
    async def initialize(self) -> bool:
        """
        Initialize the research assistant:
        1. Connect to MCP server
        2. Load tools from MCP
        3. Create the LangGraph agent
        
        Returns True if successful.
        """
        try:
            # Connect to MCP Server
            self.mcp_manager = MCPConnectionManager(self.mcp_server_url)
            self.session = await self.mcp_manager.initialize()
            print("✓ Connected to MCP Server")
            
            # Get tools from MCP
            tools_response = await self.session.list_tools()
            
            # Convert MCP tools to LangChain StructuredTools
            self.tools = []
            for tool in tools_response.tools:
                field_definitions = {}
                if tool.inputSchema and "properties" in tool.inputSchema:
                    for prop_name, prop_info in tool.inputSchema["properties"].items():
                        field_type = str if prop_info.get("type") == "string" else Any
                        required = prop_name in tool.inputSchema.get("required", [])
                        if required:
                            field_definitions[prop_name] = (
                                field_type, 
                                Field(description=prop_info.get("description", ""))
                            )
                        else:
                            field_definitions[prop_name] = (
                                Optional[field_type], 
                                Field(default=None, description=prop_info.get("description", ""))
                            )
                
                # Dynamically create Pydantic model for tool args
                ArgsModel = type(
                    f"{tool.name}Args", 
                    (BaseModel,), 
                    {
                        "__annotations__": {k: v[0] for k, v in field_definitions.items()}, 
                        **{k: v[1] for k, v in field_definitions.items()}
                    }
                )
                
                structured_tool = StructuredTool(
                    name=tool.name,
                    description=tool.description,
                    coroutine=self._create_mcp_tool_wrapper(tool.name),
                    args_schema=ArgsModel
                )
                self.tools.append(structured_tool)
            
            print(f"✓ Loaded {len(self.tools)} tools: {[t.name for t in self.tools]}")
            
            # Create LLM and Agent
            llm = ChatOpenAI(model=self.model_name)
            self.agent = Agent(llm, self.tools, system=self.system_prompt)
            print("✓ Agent created with workflow system prompt")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize: {e}")
            return False
    
    async def chat(self, message: str) -> str:
        """
        Send a message and get a response. Maintains conversation history.
        
        Args:
            message: User's message
            
        Returns:
            Agent's response as a string
        """
        if not self._initialized or not self.agent:
            return "Error: Assistant not initialized. Call initialize() first."
        
        # Add user message to history
        self.conversation_history.append(HumanMessage(content=message))
        
        # Invoke agent with full conversation history
        result = await self.agent.graph.ainvoke({"messages": self.conversation_history})
        
        # Update history with all new messages (including tool calls)
        self.conversation_history = result['messages']
        
        # Return the final response
        return result['messages'][-1].content
    
    async def chat_single(self, message: str) -> str:
        """
        Send a single message without conversation history.
        
        Args:
            message: User's message
            
        Returns:
            Agent's response as a string
        """
        if not self._initialized or not self.agent:
            return "Error: Assistant not initialized. Call initialize() first."
        
        result = await self.agent.graph.ainvoke({"messages": [HumanMessage(content=message)]})
        return result['messages'][-1].content
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    async def close(self):
        """Close connections and cleanup."""
        if self.mcp_manager:
            await self.mcp_manager.close()
        self._initialized = False
        self.agent = None
        self.tools = []
    
    @property
    def is_ready(self) -> bool:
        """Check if assistant is initialized and ready."""
        return self._initialized and self.agent is not None