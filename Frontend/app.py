"""
Research Assistant Frontend - Streamlit UI
A beautiful, animated interface for the Research Assistant Agentic System.
"""

import streamlit as st
import requests
import json
import time
from typing import Optional

# ============== Configuration ==============

API_BASE_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
STATUS_ENDPOINT = f"{API_BASE_URL}/status"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
CLEAR_ENDPOINT = f"{API_BASE_URL}/clear"

# ============== Page Configuration ==============

st.set_page_config(
    page_title="Research Assistant 🤖",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Custom CSS for Animations & Styling ==============

st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding-top: 2rem;
    }
    
    /* Chat message animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .stChatMessage {
        animation: fadeIn 0.3s ease-in;
    }
    
    /* Status indicator pulse animation */
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }
    
    .status-connected {
        color: #00ff00;
        animation: pulse 2s infinite;
    }
    
    .status-disconnected {
        color: #ff0000;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 100%);
    }
    
    /* Button hover effects */
    .stButton > button {
        transition: all 0.3s ease;
        border-radius: 10px;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Header styling */
    h1 {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Status card styling */
    .status-card {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# ============== Helper Functions ==============

def check_health() -> bool:
    """Check if the API is healthy."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=2)
        return response.status_code == 200
    except:
        return False

def get_status() -> Optional[dict]:
    """Get the current status of the assistant."""
    try:
        response = requests.get(STATUS_ENDPOINT, timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def send_message(message: str) -> Optional[dict]:
    """Send a message to the chat endpoint."""
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json={"message": message},
            timeout=120  # Long timeout for agent processing
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. The agent may be processing a complex query."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clear_history():
    """Clear the conversation history."""
    try:
        response = requests.post(CLEAR_ENDPOINT, timeout=5)
        return response.status_code == 200
    except:
        return False

# ============== Initialize Session State ==============

if "messages" not in st.session_state:
    st.session_state.messages = []

if "status" not in st.session_state:
    st.session_state.status = None

if "last_status_check" not in st.session_state:
    st.session_state.last_status_check = 0

# ============== Sidebar ==============

with st.sidebar:
    st.title("🔧 Control Panel")
    
    # Status Section
    st.markdown("### 📊 System Status")
    
    # Check health
    is_healthy = check_health()
    
    if is_healthy:
        st.markdown('<p class="status-connected">🟢 <strong>Connected</strong></p>', unsafe_allow_html=True)
        
        # Get detailed status
        status = get_status()
        if status:
            st.session_state.status = status
            
            # Status cards
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            st.metric("Assistant Ready", "✅ Yes" if status.get("is_ready") else "❌ No")
            st.metric("MCP Connected", "✅ Yes" if status.get("mcp_connected") else "❌ No")
            st.metric("Tools Loaded", status.get("tools_loaded", 0))
            st.metric("Conversation Length", status.get("conversation_length", 0))
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">🔴 <strong>Disconnected</strong></p>', unsafe_allow_html=True)
        st.warning("⚠️ Cannot connect to the API. Make sure the backend server is running on port 8000.")
    
    st.divider()
    
    # Actions Section
    st.markdown("### ⚙️ Actions")
    
    if st.button("🗑️ Clear History", use_container_width=True, type="secondary"):
        if clear_history():
            st.session_state.messages = []
            st.success("✅ History cleared!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Failed to clear history. Check API connection.")
    
    st.divider()
    
    # Info Section
    st.markdown("### ℹ️ About")
    st.info("""
    **Research Assistant** is an AI-powered chatbot that helps you:
    
    - 🔍 Search research papers in the knowledge base
    - 📚 Find papers on arXiv
    - 📥 Download and index new papers
    - 💬 Answer questions using available papers
    
    The assistant uses RAG (Retrieval-Augmented Generation) to provide accurate, cited answers.
    """)
    
    st.markdown("---")
    st.caption("Made with ❤️ using Streamlit & FastAPI")

# ============== Main Content ==============

# Header
st.title("🤖 Research Assistant")
st.markdown("**Your AI-powered research companion** - Ask questions, search papers, and get intelligent answers!")

# Check connection before allowing chat
if not is_healthy:
    st.error("🚫 **Cannot connect to the backend server.**")
    st.info("""
    **To start the backend:**
    1. Open a terminal in the `Tools Server` directory
    2. Run: `python McpServer.py` (keep this running)
    3. Open another terminal in the `Agentic System` directory  
    4. Run: `python main.py` or `uvicorn main:app --reload`
    5. Wait for both servers to start, then refresh this page
    """)
    st.stop()

# Chat Interface
st.markdown("---")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about research papers..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            response = send_message(prompt)
        
        if response and response.get("success"):
            assistant_response = response.get("response", "No response received.")
            st.markdown(assistant_response)
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        else:
            error_msg = response.get("error", "Unknown error occurred.") if response else "No response from server."
            st.error(f"❌ **Error:** {error_msg}")
            st.info("💡 **Tips:**\n- Make sure the MCP server is running\n- Check that the agent is initialized\n- Try rephrasing your question")

# Footer
st.markdown("---")
st.caption("💡 **Tip:** The assistant maintains conversation context. Ask follow-up questions naturally!")

# Auto-refresh status every 30 seconds
if time.time() - st.session_state.last_status_check > 30:
    st.session_state.last_status_check = time.time()
    st.rerun()

