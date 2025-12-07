"""
Research Assistant Frontend - Streamlit UI
A beautiful, animated interface for the Research Assistant Agentic System.
"""

import streamlit as st
import requests
import json
import time
import uuid
from typing import Optional

# ============== Page Configuration ==============

st.set_page_config(
    page_title="Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Configuration ==============

API_BASE_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
STATUS_ENDPOINT = f"{API_BASE_URL}/status"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
CLEAR_ENDPOINT = f"{API_BASE_URL}/clear"

# ============== Custom CSS for Theme Support ==============

st.markdown("""
<style>
    /* ========== COLOR PALETTE ==========
       Using CSS media queries to support both light and dark browser themes
       
       DARK THEME:
       - Primary: #0f0f23, #1a1a2e, #16213e (deep navy backgrounds)
       - Secondary: #1e293b (cards/sidebar)
       - Accent: #00d4aa (teal)
       - Text: #ffffff (primary), #94a3b8 (muted)
       
       LIGHT THEME:
       - Primary: #f8fafc (light gray background)
       - Secondary: #ffffff (cards), #f1f5f9 (sidebar)
       - Accent: #5b6cff (blue-purple)
       - Text: #1e293b (primary), #64748b (muted)
    ================================== */
    
    /* ========== ANIMATIONS ========== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    /* ========== DARK THEME (Default) ========== */
    
    /* Main app styling */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        color: #ffffff;
    }
    
    .main .block-container {
        background: transparent;
        padding-top: 2rem;
    }
    
    /* Title styling */
    h1 {
        color: #5b6cff !important;
        text-align: center;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"], .stSidebar > div {
        background: #1a1a2e !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Sidebar headers */
    .stSidebar h1, .stSidebar h2, .stSidebar h3 {
        color: #5b6cff !important;
        text-align: left;
        margin-bottom: 0.75rem;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    
    .stSidebar p, .stSidebar .stMarkdown, .stSidebar .stMarkdown p {
        color: #ffffff !important;
    }
    
    /* Status indicators */
    .status-connected {
        color: #00d4aa !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    
    .status-disconnected {
        color: #ff6b6b !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    
    /* Status card styling */
    .status-card {
        background: #252542;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        animation: slideIn 0.5s ease-out;
    }
    
    /* Buttons styling */
    .stButton > button {
        background: #00d4aa !important;
        color: #0f0f23 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        background: #00b894 !important;
        transform: translateY(-1px) !important;
    }
    
    /* Warning message (sidebar) */
    .stWarning, [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentWarning"]) {
        background: rgba(255, 193, 7, 0.15) !important;
        border: 1px solid #ffc107 !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    /* Error message - Coral/salmon style */
    .stError, [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentError"]) {
        background: rgba(239, 118, 122, 0.2) !important;
        border: 1px solid #ef767a !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    /* Success message */
    .stSuccess {
        background: rgba(0, 212, 170, 0.15) !important;
        border: 1px solid #00d4aa !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    /* Info message - Blue style */
    .stInfo, [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentInfo"]) {
        background: rgba(91, 108, 255, 0.15) !important;
        border: 1px solid #5b6cff !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }
    
    /* Welcome container */
    .welcome-container {
        text-align: center;
        padding: 2.5rem 2rem;
        background: #1e293b;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 2rem 0;
        animation: fadeIn 0.6s ease-out;
    }
    
    .welcome-container h2 {
        color: #ffffff !important;
        margin-bottom: 0.75rem;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }
    
    .welcome-container p {
        color: #94a3b8 !important;
        font-size: 1rem;
    }
    
    /* Feature cards */
    .feature-card {
        background: #1e293b;
        padding: 1.5rem 1rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        border-color: #5b6cff;
        box-shadow: 0 0 20px rgba(91, 108, 255, 0.15);
        transform: translateY(-3px);
    }
    
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .feature-title {
        color: #ffffff !important;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }
    
    .feature-desc {
        color: #94a3b8 !important;
        font-size: 0.8rem;
    }
    
    /* Chat message containers */
    .stChatMessage {
        background: #1e293b !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin: 0.75rem 0 !important;
        color: #ffffff !important;
        animation: fadeIn 0.4s ease-out;
    }
    
    .stChatMessage .stMarkdown, .stChatMessage .stMarkdown p {
        color: #ffffff !important;
    }
    
    .stChatMessage .stMarkdown h1, .stChatMessage .stMarkdown h2,
    .stChatMessage .stMarkdown h3, .stChatMessage .stMarkdown h4 {
        color: #5b6cff !important;
    }
    
    /* User messages */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #2a4a6f 100%) !important;
        border: 1px solid rgba(91, 108, 255, 0.3) !important;
    }
    
    /* Assistant messages */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: #252542 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Chat input styling */
    [data-testid="stChatInput"] {
        background: transparent !important;
    }
    
    [data-testid="stChatInput"] > div {
        background: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }
    
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input {
        background: #1e293b !important;
        color: #ffffff !important;
        font-size: 15px !important;
        border: none !important;
        caret-color: #5b6cff !important;
    }
    
    [data-testid="stChatInput"] textarea::placeholder,
    [data-testid="stChatInput"] input::placeholder {
        color: #64748b !important;
    }
    
    [data-testid="stChatInput"] > div:focus-within {
        border-color: #5b6cff !important;
        box-shadow: 0 0 0 1px #5b6cff !important;
    }
    
    [data-testid="stChatInput"] button {
        background: transparent !important;
        border: none !important;
        color: #5b6cff !important;
    }
    
    [data-testid="stBottom"] {
        background: linear-gradient(180deg, transparent 0%, #0f0f23 20%) !important;
    }
    
    /* General text */
    .stMarkdown, .stMarkdown p, .stText,
    div[data-testid="stMarkdownContainer"], div[data-testid="stText"] {
        color: #ffffff !important;
    }
    
    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
        margin: 1rem 0 !important;
    }
    
    /* Caption */
    .stCaption {
        color: #94a3b8 !important;
    }
    
    /* Code blocks */
    code {
        background: rgba(91, 108, 255, 0.1) !important;
        color: #5b6cff !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: #00d4aa !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
    
    /* Spinner */
    .stSpinner, .stSpinner > div {
        color: #5b6cff !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
    }
    ::-webkit-scrollbar-thumb {
        background: #3a3a5a;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #4a4a6a;
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ========== LIGHT THEME (Browser Preference) ========== */
    @media (prefers-color-scheme: light) {
        .stApp {
            background: #f8fafc !important;
            color: #1e293b;
        }
        
        .css-1d391kg, [data-testid="stSidebar"], .stSidebar > div {
            background: #f1f5f9 !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        
        .stSidebar h1, .stSidebar h2, .stSidebar h3 {
            color: #5b6cff !important;
        }
        
        .stSidebar p, .stSidebar .stMarkdown, .stSidebar .stMarkdown p {
            color: #1e293b !important;
        }
        
        .status-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
        }
        
        .stButton > button {
            background: #f1f5f9 !important;
            color: #1e293b !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .stButton > button:hover {
            background: #e2e8f0 !important;
        }
        
        .stWarning {
            background: rgba(255, 193, 7, 0.1) !important;
            border: 1px solid #ffc107 !important;
            color: #92400e !important;
        }
        
        .stError {
            background: rgba(239, 118, 122, 0.15) !important;
            border: 1px solid #ef767a !important;
            color: #991b1b !important;
        }
        
        .stInfo {
            background: rgba(91, 108, 255, 0.1) !important;
            border: 1px solid #5b6cff !important;
            color: #1e40af !important;
        }
        
        .stSuccess {
            background: rgba(0, 212, 170, 0.1) !important;
            border: 1px solid #00d4aa !important;
            color: #065f46 !important;
        }
        
        .welcome-container {
            background: #ffffff;
            border: 1px solid #e2e8f0;
        }
        
        .welcome-container h2 {
            color: #1e293b !important;
        }
        
        .welcome-container p {
            color: #64748b !important;
        }
        
        .feature-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
        }
        
        .feature-title {
            color: #1e293b !important;
        }
        
        .feature-desc {
            color: #64748b !important;
        }
        
        .stChatMessage {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            color: #1e293b !important;
        }
        
        .stChatMessage .stMarkdown, .stChatMessage .stMarkdown p {
            color: #1e293b !important;
        }
        
        .stChatMessage[data-testid="stChatMessageUser"] {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
            border: 1px solid #bfdbfe !important;
        }
        
        .stChatMessage[data-testid="stChatMessageAssistant"] {
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        [data-testid="stChatInput"] > div {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] input {
            background: #ffffff !important;
            color: #1e293b !important;
        }
        
        [data-testid="stChatInput"] textarea::placeholder,
        [data-testid="stChatInput"] input::placeholder {
            color: #94a3b8 !important;
        }
        
        [data-testid="stBottom"] {
            background: linear-gradient(180deg, transparent 0%, #f8fafc 20%) !important;
        }
        
        .stMarkdown, .stMarkdown p, .stText,
        div[data-testid="stMarkdownContainer"], div[data-testid="stText"] {
            color: #1e293b !important;
        }
        
        hr {
            border-color: #e2e8f0 !important;
        }
        
        .stCaption {
            color: #64748b !important;
        }
        
        [data-testid="stMetricValue"] {
            color: #5b6cff !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: #64748b !important;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
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

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ============== Sidebar ==============

with st.sidebar:
    st.markdown("### CONTROL PANEL")
    
    # Status Section
    st.markdown("### SYSTEM STATUS")
    
    # Check health
    is_healthy = check_health()
    
    if is_healthy:
        st.markdown('<p class="status-connected"><span style="color: #00d4aa;">●</span> Connected</p>', unsafe_allow_html=True)
        
        # Get detailed status
        status = get_status()
        if status:
            st.session_state.status = status
            
            # Status metrics in a clean card
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                ready_status = "●" if status.get("is_ready") else "○"
                ready_color = "#00d4aa" if status.get("is_ready") else "#a0a0b0"
                st.markdown(f'<p style="color: #a0a0b0; font-size: 0.75rem; margin-bottom: 2px;">Ready</p><p style="color: {ready_color}; font-size: 1.1rem; font-weight: 600;">{ready_status}</p>', unsafe_allow_html=True)
            with col2:
                mcp_status = "●" if status.get("mcp_connected") else "○"
                mcp_color = "#00d4aa" if status.get("mcp_connected") else "#a0a0b0"
                st.markdown(f'<p style="color: #a0a0b0; font-size: 0.75rem; margin-bottom: 2px;">MCP</p><p style="color: {mcp_color}; font-size: 1.1rem; font-weight: 600;">{mcp_status}</p>', unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            with col3:
                st.markdown(f'<p style="color: #a0a0b0; font-size: 0.75rem; margin-bottom: 2px;">Tools</p><p style="color: #00d4aa; font-size: 1.1rem; font-weight: 600;">{status.get("tools_loaded", 0)}</p>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<p style="color: #a0a0b0; font-size: 0.75rem; margin-bottom: 2px;">Messages</p><p style="color: #00d4aa; font-size: 1.1rem; font-weight: 600;">{status.get("conversation_length", 0)}</p>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected"><span>●</span> Disconnected</p>', unsafe_allow_html=True)
        st.warning("Cannot connect to the API server.")
    
    st.markdown("---")
    
    # Actions Section
    st.markdown("### ACTIONS")
    
    if st.button("Clear Conversation", use_container_width=True):
        if clear_history():
            st.session_state.messages = []
            st.success("History cleared!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Failed to clear history.")
    
    if st.button("New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.success("New session started!")
        time.sleep(0.5)
        st.rerun()
    
    st.markdown("---")
    
    # Session Info
    st.markdown("### SESSION INFO")
    st.markdown(f"""
    <div class="status-card">
        <p style="font-size: 10px; word-break: break-all; color: #a0a0b0; font-family: monospace;">
            {st.session_state.session_id}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # About Section
    st.markdown("### ABOUT")
    st.markdown("""
    <div class="status-card">
        <p style="font-size: 13px; color: #ffffff; margin-bottom: 8px;">
            <strong>Research Assistant</strong>
        </p>
        <ul style="font-size: 12px; padding-left: 1.2rem; color: #a0a0b0; margin: 0;">
            <li>Search research papers</li>
            <li>Find papers on arXiv</li>
            <li>Download & index papers</li>
            <li>Get cited answers</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Made with ❤️ using Streamlit")

# ============== Main Content ==============

# Header
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; color: #ffffff !important;">Research Assistant</h1>
    <p style="color: #a0a0b0; font-size: 1.1rem;">
        Your AI-powered research companion — Ask questions, search papers, and get intelligent answers
    </p>
</div>
""", unsafe_allow_html=True)

# Check connection before allowing chat
if not is_healthy:
    st.markdown("""
    <div class="welcome-container" style="border-color: #ff6b6b;">
        <h2 style="color: #ff6b6b !important;">Cannot Connect to Backend</h2>
        <p>The backend server is not responding. Please start the servers.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    **To start the backend:**
    1. Open a terminal in the `Tools Server` directory
    2. Run: `python McpServer.py` (keep this running)
    3. Open another terminal in the `Agentic System` directory  
    4. Run: `python main.py` or `uvicorn main:app --reload`
    5. Wait for both servers to start, then refresh this page
    """)
    st.stop()

# Welcome message when no messages
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-container">
        <h2>Welcome to Research Assistant</h2>
        <p>I'm here to help you explore and understand research papers.</p>
        <p style="margin-top: 1rem; color: #a0a0b0;">Start by asking me a question below...</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature cards - Monochrome icons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <p class="feature-title">Search</p>
            <p class="feature-desc">Query the knowledge base</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📄</div>
            <p class="feature-title">Discover</p>
            <p class="feature-desc">Find papers on arXiv</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📥</div>
            <p class="feature-title">Download</p>
            <p class="feature-desc">Add papers to index</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <p class="feature-title">Chat</p>
            <p class="feature-desc">Get cited answers</p>
        </div>
        """, unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about research papers..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Researching..."):
            response = send_message(prompt)
        
        if response and response.get("success"):
            assistant_response = response.get("response", "No response received.")
            st.markdown(assistant_response)
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        else:
            error_msg = response.get("error", "Unknown error occurred.") if response else "No response from server."
            st.error(f"**Error:** {error_msg}")
            st.markdown("""
            <div class="status-card" style="margin-top: 1rem;">
                <p style="color: #ffffff; font-weight: 600; margin-bottom: 8px;">Tips:</p>
                <ul style="font-size: 13px; margin: 0; padding-left: 1.2rem; color: #a0a0b0;">
                    <li>Make sure the MCP server is running</li>
                    <li>Check that the agent is initialized</li>
                    <li>Try rephrasing your question</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 0.5rem;">
    <p style="color: #a0a0b0; font-size: 12px;">
        The assistant maintains conversation context. Ask follow-up questions naturally.
    </p>
</div>
""", unsafe_allow_html=True)

