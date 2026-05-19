"""
MULTIMODAL ADVANCED RAG GITHUB REPOSITORY CHATBOT
==================================================
Home Page / Landing Page

This application implements a production-grade Retrieval-Augmented Generation (RAG)
system for analyzing GitHub repositories using AI.

Author: RepoMiner
Date: March 2026
"""

import streamlit as st
import os
from repo_session_store import load_index, list_sessions
from config import load_app_config
from ui import (
    apply_base_ui,
    render_hero,
    section_header,
    render_info_card,
    render_pill_row,
)

# Page Configuration
st.set_page_config(
    page_title="Advanced RAG GitHub Chatbot - Home",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for shared data across pages
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "repo_processed" not in st.session_state:
    st.session_state.repo_processed = False

if "repo_stats" not in st.session_state:
    st.session_state.repo_stats = None

app_config = load_app_config()

saved_sessions = list_sessions()
saved_index = load_index()

apply_base_ui()

provider_bits = []
if app_config.get("OPENROUTER_API_KEY"):
    provider_bits.append("OpenRouter")
if app_config.get("GEMINI_API_KEY"):
    provider_bits.append("Gemini")
if app_config.get("GROQ_API_KEY"):
    provider_bits.append("Groq")

if not provider_bits:
    st.warning(
        "Add at least one of OPENROUTER_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY to your `.env`."
    )
else:
    st.info("Provider order: OpenRouter -> Gemini -> Groq")

render_hero(
    "Repository Intelligence",
    "Advanced RAG GitHub Repository Chatbot",
    "Understand any codebase through natural language conversations with grounded answers, clean source attribution, and a modern workflow built for fast exploration.",
)

render_pill_row(
    [
        "OpenRouter GPT",
        "Gemini",
        "Groq",
        "ChromaDB",
        "LangChain",
        "Semantic Search",
    ]
)

section_header(
    "Start Here",
    "Open the workflow that fits your task",
    "Jump into chat, review repository analytics, or follow the usage guide.",
)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    <div class="feature-card">
        <h3>💬 Chatbot</h3>
        <p>Process repositories and ask questions about the code.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Go to Chatbot ➡️", use_container_width=True, type="primary"):
        st.switch_page("pages/3_💬_Chatbot.py")

with col2:
    st.markdown(
        """
    <div class="feature-card">
        <h3>📊 Repository Stats</h3>
        <p>View detailed analytics about processed repositories</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("View Stats ➡️", use_container_width=True):
        st.switch_page("pages/1_📊_Repository_Stats.py")

with col3:
    st.markdown(
        """
    <div class="feature-card">
        <h3>📚 How to Use</h3>
        <p>Complete guide with examples and tips</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Learn More ➡️", use_container_width=True):
        st.switch_page("pages/2_📚_How_to_Use.py")

st.markdown("---")

if saved_sessions:
    section_header(
        "Recent",
        "Resume the last repository session",
        "Continue where you left off without reprocessing the repo.",
    )
    last_session = saved_sessions[0]
    render_info_card(
        f"Last repo: {last_session.get('repo_name', 'Unknown')}",
        f"Updated {last_session.get('updated_at', '')[:19].replace('T', ' ')}",
        accent="Saved session",
    )
    if st.button("Continue in Chatbot ➡️", use_container_width=True):
        st.switch_page("pages/3_💬_Chatbot.py")

    st.markdown("---")

section_header(
    "Overview",
    "What is RAG?",
    "A quick explanation of the retrieval and generation pipeline used in this app.",
)
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    **Retrieval-Augmented Generation (RAG)** combines the power of search and AI to provide 
    accurate, source-based answers.
    
    Traditional chatbots can hallucinate or provide outdated information. RAG solves this by:
    
    1. **📥 Ingesting** your codebase into a vector database
    2. **🔍 Retrieving** relevant code snippets for each question
    3. **🤖 Generating** answers grounded in actual code
    4. **💬 Remembering** conversation context for follow-ups
    """)

with col2:
    st.markdown("""
    ### How It Works:
    
    ```
    Your Question
         ↓
    [Vector Embedding]
         ↓
    [Similarity Search in ChromaDB]
         ↓
    [Retrieve Top 6 Code Chunks]
         ↓
    [Send to LLaMA 3 with Context]
         ↓
    ✨ AI-Generated Answer ✨
    ```
    
    **Result:** Accurate answers backed by real code!
    """)

st.markdown("---")

section_header(
    "Benefits",
    "Key features",
    "Minimal, practical capabilities designed for everyday repository analysis.",
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🎯 Intelligent Code Understanding
    - **Semantic Search**: Finds relevant code based on meaning, not just keywords
    - **Multi-Language Support**: JavaScript, Python, TypeScript, and more
    - **Context-Aware**: Maintains conversation history for follow-up questions
    
    ### ⚡ Blazing Fast Performance
    - **Groq LPU**: 10x faster than traditional GPU inference
    - **Efficient Embeddings**: 384-dim vectors for quick similarity search
    - **HNSW Indexing**: O(log n) retrieval time with ChromaDB
    """)

with col2:
    st.markdown("""
    ### 🔒 Accurate & Reliable
    - **Source Attribution**: Always references specific files
    - **No Hallucination**: Answers only from your codebase
    - **Transparent**: View retrieved code chunks for verification
    
    ### 🎨 User-Friendly Interface
    - **Dynamic Processing**: Load any public GitHub repo
    - **Clean Chat UI**: Natural conversation experience
    - **Detailed Stats**: View comprehensive repository analytics
    """)

st.markdown("---")

section_header(
    "Stack",
    "Technology stack",
    "The core tools powering the interface, retrieval, and model orchestration.",
)

st.markdown("""
This application is built with cutting-edge AI and database technologies:
""")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**Frontend**")
    render_pill_row(["Streamlit", "Python"])

with col2:
    st.markdown("**AI Models**")
    render_pill_row(["LLaMA 3.1-8B", "MiniLM-L6-v2"])

with col3:
    st.markdown("**Infrastructure**")
    render_pill_row(["Groq LPU", "ChromaDB"])

with col4:
    st.markdown("**Framework**")
    render_pill_row(["LangChain", "HuggingFace"])

st.markdown("---")

section_header(
    "Use Cases",
    "Where this app helps",
    "A few common ways teams use the chatbot for code understanding.",
)

use_cases = [
    ("🎓", "**Learning New Codebases**", "Quickly understand unfamiliar projects"),
    ("🔍", "**Code Review**", "Analyze architecture and design patterns"),
    ("📚", "**Documentation**", "Generate insights about code structure"),
    ("🐛", "**Debugging**", "Understand how different parts interact"),
    ("🚀", "**Onboarding**", "Help new team members get up to speed"),
    ("🔬", "**Research**", "Study open-source implementations"),
]

cols = st.columns(3)
for i, (icon, title, description) in enumerate(use_cases):
    with cols[i % 3]:
        st.markdown(
            f"""
        <div class="feature-card">
            <h3>{icon} {title}</h3>
            <p>{description}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("---")

section_header(
    "Quick Start",
    "Ready to explore code?",
    "Jump straight into the chatbot once a repository is processed.",
)

st.info("""
**Get started in 3 simple steps:**
1. Navigate to the **💬 Chatbot** page
2. Enter any public GitHub repository URL
3. Wait for processing, then ask questions!
""")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🎯 Start Chatting Now!", use_container_width=True, type="primary"):
        st.switch_page("pages/3_💬_Chatbot.py")

st.markdown("---")

if st.session_state.repo_processed and st.session_state.repo_stats:
    render_info_card(
        "A repository is loaded and ready",
        "Ask follow-up questions, inspect retrieved chunks, or switch to repository analytics.",
        accent="Live workspace",
    )
    stats = st.session_state.repo_stats

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Repository", stats.get("repo_name", "Unknown"), "Current active repo"
        )
    with col2:
        render_metric_card(
            "Total Files", str(stats.get("total_files", 0)), "Parsed from the repo"
        )
    with col3:
        render_metric_card(
            "Code Chunks", str(stats.get("total_chunks", 0)), "Ready for retrieval"
        )
    with col4:
        if st.button("View Details ➡️"):
            st.switch_page("pages/1_📊_Repository_Stats.py")
else:
    st.info("No repository loaded yet. Visit the Chatbot page to process one.")

st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #5d6b7f; padding: 20px;">
    <p><b>Advanced RAG GitHub Repository Chatbot</b></p>
    <p>Built with ❤️ by RepoMiner • March 2026</p>
    <p style="font-size: 12px;">Powered by Groq LLaMA 3.1-8B-Instant, ChromaDB, LangChain & Streamlit</p>
</div>
""",
    unsafe_allow_html=True,
)
