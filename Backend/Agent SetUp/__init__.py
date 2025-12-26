"""Agent SetUp package - Research Assistant Agent with MCP integration."""

from .agent import (
    Agent,
    AgentState,
    MCPConnectionManager,
    ResearchAssistant,
    RESEARCH_ASSISTANT_PROMPT
)

__all__ = [
    "Agent",
    "AgentState", 
    "MCPConnectionManager",
    "ResearchAssistant",
    "RESEARCH_ASSISTANT_PROMPT"
]
