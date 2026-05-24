"""CodeMiner home dashboard.

This page keeps the app focused on the two core workflows: Chatbot and
Repository Stats.
"""

from __future__ import annotations

import streamlit as st

from config import load_app_config
from repo_session_store import load_index, list_sessions
from ui import (
    apply_base_ui,
    render_dashboard_action,
    render_empty_state,
    render_feature_card,
    render_hero,
    render_info_card,
    render_metric_card,
    render_pill_row,
    render_sidebar_brand,
    render_sidebar_panel,
    section_header,
)

st.set_page_config(
    page_title="CodeMiner",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
active_session_id = saved_index.get("current_session_id")
active_session = next(
    (
        session
        for session in saved_sessions
        if session.get("session_id") == active_session_id
    ),
    None,
)
recent_session = active_session or (saved_sessions[0] if saved_sessions else None)

provider_bits: list[str] = []
if app_config.get("OPENROUTER_API_KEY"):
    provider_bits.append("OpenRouter")
if app_config.get("GEMINI_API_KEY"):
    provider_bits.append("Gemini")
if app_config.get("GROQ_API_KEY"):
    provider_bits.append("Groq")

apply_base_ui()
render_sidebar_brand("CodeMiner", "Repository intelligence workspace")

render_sidebar_panel("Navigate", "Jump directly to the two main workflows.")
nav_left, nav_right = st.sidebar.columns(2)
with nav_left:
    if st.button("Chatbot", use_container_width=True, type="primary"):
        st.switch_page("pages/3_💬_Chatbot.py")
with nav_right:
    if st.button("Stats", use_container_width=True):
        st.switch_page("pages/1_📊_Repository_Stats.py")

render_sidebar_panel("Workspace status", "Current state at a glance.")
st.sidebar.markdown(
    f"""
<div class="compact-meta">
  <span>Sessions: {len(saved_sessions)}</span>
  <span>Repo loaded: {'Yes' if st.session_state.repo_processed else 'No'}</span>
  <span>Models: {len(provider_bits) if provider_bits else 0}</span>
</div>
""",
    unsafe_allow_html=True,
)

if provider_bits:
    st.sidebar.markdown(
        f"""
<div style="margin-top:10px; font-size:12px; color:var(--muted); line-height:1.5;">
  Ready providers: <strong>{", ".join(provider_bits)}</strong>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.sidebar.warning("Add at least one API key to enable chat models.")

render_hero(
    "Repository Intelligence",
    "CodeMiner",
    "Turn a GitHub repository into grounded answers and fast analytics. Start in Chatbot, then return here when you want the stats view or a saved session.",
)

render_pill_row(["Chatbot", "Repository Stats", "Saved sessions", "Grounded answers"])

section_header(
    "Quick actions",
    "Pick the next step",
    "The homepage is a control surface, not documentation.",
)

action_left, action_right = st.columns(2)
with action_left:
    render_dashboard_action(
        "Chatbot",
        "Process a repository, ask technical questions, and inspect grounded answers with source context.",
        "💬",
        "Primary workflow",
    )
    if st.button("Open Chatbot", use_container_width=True, type="primary"):
        st.switch_page("pages/3_💬_Chatbot.py")

with action_right:
    render_dashboard_action(
        "Repository Stats",
        "Review files, chunks, language breakdowns, exports, and other repository analytics.",
        "📊",
        "Insights",
    )
    if st.button("Open Repository Stats", use_container_width=True):
        st.switch_page("pages/1_📊_Repository_Stats.py")

section_header(
    "Recent session",
    "Continue where you left off",
    "The latest repository is ready to reopen if one has already been processed.",
)

if recent_session:
    render_info_card(
        recent_session.get("repo_name", "Unknown repository"),
        f"Updated {recent_session.get('updated_at', '')[:19].replace('T', ' ')}",
        accent="Recent workspace",
    )
    if st.button("Continue in Chatbot", use_container_width=True):
        st.switch_page("pages/3_💬_Chatbot.py")
else:
    render_empty_state(
        "No saved session yet",
        "Process a repository in Chatbot to create a reusable workspace.",
        accent="Recent activity",
    )

section_header(
    "Workspace snapshot",
    "Current repository state",
    "A compact status view for the active repository.",
)

if st.session_state.repo_processed and st.session_state.repo_stats:
    stats = st.session_state.repo_stats
    snapshot_left, snapshot_right, snapshot_tail = st.columns(3)
    with snapshot_left:
        render_metric_card(
            "Repository", stats.get("repo_name", "Unknown"), "Current active repo"
        )
    with snapshot_right:
        render_metric_card(
            "Total Files", str(stats.get("total_files", 0)), "Parsed from the repo"
        )
    with snapshot_tail:
        render_metric_card(
            "Code Chunks", str(stats.get("total_chunks", 0)), "Ready for retrieval"
        )
else:
    render_empty_state(
        "Nothing loaded yet",
        "Use Chatbot to process a GitHub repository, then return here for the analytics overview.",
        accent="Workspace",
    )

section_header(
    "Product summary",
    "Built for focused code discovery",
    "Three small design choices keep the interface fast to scan and easy to use.",
)

summary_left, summary_mid, summary_right = st.columns(3)
with summary_left:
    render_feature_card(
        "Grounded answers",
        "Questions are answered from retrieved repository context instead of generic model output.",
        "💬",
    )
with summary_mid:
    render_feature_card(
        "Session continuity",
        "Saved sessions let you reopen a repository without repeating ingestion.",
        "🕘",
    )
with summary_right:
    render_feature_card(
        "Fast analytics",
        "Repository Stats surfaces the key metrics, charts, and exports in one place.",
        "📈",
    )

st.markdown(
    """
<div style="text-align:center; color:var(--muted); padding:20px 0 6px; font-size:13px;">
  CodeMiner keeps repository exploration organized, fast, and grounded in code context.
</div>
""",
    unsafe_allow_html=True,
)
