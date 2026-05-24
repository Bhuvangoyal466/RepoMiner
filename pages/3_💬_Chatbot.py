"""
Chatbot Page
============
Main interactive page for processing repositories and asking questions about code.
Includes the full RAG pipeline with conversational memory.
"""

import os
import warnings
import shutil
from pathlib import Path

from config import ensure_required_keys, load_app_config

# CRITICAL: Suppress parallelism warnings from HuggingFace tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*torch.*")

import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import logging
from ingest import process_repository, get_repo_stats, safe_rmtree
from repo_session_store import (
    load_index,
    list_sessions,
    load_session,
    save_session,
    save_vectorstore_snapshot,
    restore_vectorstore_snapshot,
)
from ui import (
    apply_base_ui,
    render_sidebar_brand,
    render_hero,
    render_info_card,
    render_pill_row,
    section_header,
    render_sidebar_panel,
    render_empty_state,
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Page Configuration (must be first Streamlit command)
st.set_page_config(
    page_title="CodeMiner Chatbot",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_ui()
render_sidebar_brand("CodeMiner", "Repository intelligence workspace")

APP_CONFIG = load_app_config()
try:
    ensure_required_keys(APP_CONFIG)
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

OPENROUTER_API_KEY = APP_CONFIG["OPENROUTER_API_KEY"] or ""
OPENROUTER_MODEL = APP_CONFIG["OPENROUTER_MODEL"] or "openai/gpt-oss-20b:free"
OPENROUTER_BASE_URL = (
    APP_CONFIG["OPENROUTER_BASE_URL"] or "https://openrouter.ai/api/v1"
)
GROQ_API_KEY = APP_CONFIG["GROQ_API_KEY"] or ""
GROQ_MODEL = APP_CONFIG["GROQ_MODEL"] or "llama-3.3-70b-versatile"
GOOGLE_API_KEY = APP_CONFIG["GOOGLE_API_KEY"] or ""
ENABLE_GEMINI_BACKUP = APP_CONFIG.get("ENABLE_GEMINI_BACKUP") != "false"
GEMINI_MODEL_FLASH = APP_CONFIG["GEMINI_MODEL_FLASH"] or "gemini-2.5-flash"
GEMINI_MODEL_PRO = APP_CONFIG["GEMINI_MODEL_PRO"] or "gemini-2.5-pro"

if OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
if GOOGLE_API_KEY and ENABLE_GEMINI_BACKUP:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# ==============================================================================
# CORE RAG PIPELINE
# ==============================================================================


def _build_rag_chain(llm):
    """Build a retrieval chain for a specific language model."""

    # Embeddings Model
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # ChromaDB Vector Store
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

    # Retriever Configuration
    retriever = vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": 6}
    )

    # Contextualize Question Prompt
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    # History-Aware Retriever
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    # Main System Prompt
    qa_system_prompt = (
        "You are a Senior Staff Engineer with 10+ years of experience explaining "
        "a codebase to a junior developer. Use the following retrieved code context "
        "to answer questions. Always reference specific file paths when explaining "
        "implementations. If you don't know the answer based on the provided context, "
        "clearly state that. Keep explanations technical but accessible.\n\n"
        "Retrieved Context:\n{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    # Question-Answer Chain
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    # Final Retrieval Chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    return rag_chain, vectorstore


@st.cache_resource
def load_rag_pipeline(
    _openrouter_api_key: str,
    _groq_api_key: str,
    _google_api_key: str,
    _openrouter_base_url: str,
    _openrouter_model: str,
    _groq_model: str,
    _gemini_model_flash: str,
    _gemini_model_pro: str,
):
    """
    Initializes the complete RAG (Retrieval-Augmented Generation) pipeline.
    Cached to avoid reloading on every interaction.
    Note: underscore-prefixed parameters are excluded from caching hash.
    """

    logging.basicConfig(level=logging.INFO)
    logging.info("Initializing RAG pipeline — checking configured providers")

    providers = []
    vectorstore = None

    def _register_provider(model_name, llm):
        nonlocal vectorstore
        logging.info("Registering provider: %s", model_name)
        try:
            chain, store = _build_rag_chain(llm)
        except Exception as exc:
            logging.exception("Failed to build RAG chain for provider %s: %s", model_name, exc)
            return
        if vectorstore is None:
            vectorstore = store
        providers.append((model_name, chain))

    if _openrouter_api_key:
        try:
            openrouter_llm = ChatOpenAI(
                model=_openrouter_model,
                temperature=0.2,
                max_tokens=8192,
                api_key=_openrouter_api_key,
                base_url=_openrouter_base_url,
            )
        except TypeError:
            openrouter_llm = ChatOpenAI(
                model=_openrouter_model,
                temperature=0.2,
                max_tokens=8192,
                openai_api_key=_openrouter_api_key,
                openai_api_base=_openrouter_base_url,
            )
        _register_provider(f"openrouter-{_openrouter_model}", openrouter_llm)

    gemini_flash_llm = None
    gemini_pro_llm = None
    if _google_api_key and ENABLE_GEMINI_BACKUP:
        try:
            logging.info("Attempting to initialize Gemini flash model: %s", _gemini_model_flash)
            gemini_flash_llm = ChatGoogleGenerativeAI(
                model=_gemini_model_flash,
                temperature=0.2,
                google_api_key=_google_api_key,
                max_output_tokens=8192,
            )
        except Exception as exc:
            gemini_flash_llm = None
            logging.exception("Gemini flash init failed: %s", exc)

        try:
            logging.info("Attempting to initialize Gemini pro model: %s", _gemini_model_pro)
            gemini_pro_llm = ChatGoogleGenerativeAI(
                model=_gemini_model_pro,
                temperature=0.2,
                google_api_key=_google_api_key,
                max_output_tokens=8192,
            )
        except Exception as exc:
            gemini_pro_llm = None
            logging.exception("Gemini pro init failed: %s", exc)

    if gemini_flash_llm is not None:
        _register_provider(f"gemini-{_gemini_model_flash}", gemini_flash_llm)

    if gemini_pro_llm is not None:
        _register_provider(f"gemini-{_gemini_model_pro}", gemini_pro_llm)

    if _groq_api_key:
        groq_llm = ChatGroq(
            model=_groq_model,
            temperature=0.2,
            max_tokens=8192,
            groq_api_key=_groq_api_key,
        )
        _register_provider(f"groq-{_groq_model}", groq_llm)

    logging.info("Providers registered: %s", [p[0] for p in providers])
    if not providers:
        logging.error("No LLM providers were configured — raising RuntimeError")
        raise RuntimeError("No LLM providers are configured.")

    return {
        "providers": providers,
        "primary": providers[0],
        "backups": providers[1:],
        "vectorstore": vectorstore,
    }


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "repo_processed" not in st.session_state:
    st.session_state.repo_processed = False

if "repo_stats" not in st.session_state:
    st.session_state.repo_stats = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "active_model_name" not in st.session_state:
    st.session_state.active_model_name = f"openrouter-{OPENROUTER_MODEL}"


def _serialize_chat_history(chat_history):
    serialized = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            serialized.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            serialized.append({"role": "ai", "content": msg.content})
    return serialized


def _deserialize_chat_history(items):
    history = []
    for item in items or []:
        role = item.get("role")
        content = item.get("content", "")
        if role == "human":
            history.append(HumanMessage(content=content))
        elif role == "ai":
            history.append(AIMessage(content=content))
    return history


def _apply_session_payload(payload):
    if not payload:
        return False
    st.session_state.messages = payload.get("messages", []) or []
    st.session_state.chat_history = _deserialize_chat_history(
        payload.get("chat_history", [])
    )
    st.session_state.repo_stats = payload.get("repo_stats")
    st.session_state.repo_processed = bool(st.session_state.repo_stats)
    st.session_state.current_session_id = payload.get("session_id")
    st.session_state.active_model_name = payload.get(
        "active_model_name", st.session_state.active_model_name
    )
    return True


def _save_current_session():
    if not st.session_state.get("repo_stats"):
        return None

    repo_stats = st.session_state.repo_stats or {}
    repo_name = repo_stats.get("repo_name") or "repo"
    repo_url = repo_stats.get("repo_url") or ""
    session_id = save_session(
        repo_name=repo_name,
        repo_url=repo_url,
        repo_stats=repo_stats,
        messages=st.session_state.messages,
        chat_history=_serialize_chat_history(st.session_state.chat_history),
        session_id=st.session_state.get("current_session_id"),
    )
    st.session_state.current_session_id = session_id
    try:
        save_vectorstore_snapshot(session_id)
    except Exception:
        pass
    return session_id


def _load_session_by_id(session_id):
    payload = load_session(session_id)
    if not payload:
        return False
    restored = restore_vectorstore_snapshot(session_id)
    if restored:
        try:
            if "rag_bundle" in st.session_state:
                del st.session_state["rag_bundle"]
            if "vectorstore" in st.session_state:
                del st.session_state["vectorstore"]
            st.cache_resource.clear()
        except Exception:
            pass
    return _apply_session_payload(payload)


def _invoke_with_fallback(bundle, user_query, chat_history):
    attempts = [bundle.get("primary")] + bundle.get("backups", [])
    last_error = None

    for model_name, chain in attempts:
        logging.info("Attempting model: %s", model_name)
        if chain is None:
            logging.warning("Skipping model %s because chain is None", model_name)
            continue
        try:
            response = chain.invoke({"input": user_query, "chat_history": chat_history})
            logging.info("Model %s returned a response", model_name)
            return response, model_name, None
        except Exception as exc:
            last_error = exc
            logging.exception("Model %s failed with exception: %s", model_name, exc)

    raise last_error or RuntimeError("No model available for inference")


# Restore last active session on first load
if st.session_state.current_session_id is None:
    index = load_index()
    current_id = index.get("current_session_id")
    if current_id:
        _load_session_by_id(current_id)
    elif list_sessions():
        _load_session_by_id(list_sessions()[0].get("session_id"))


# ==============================================================================
# SIDEBAR: Repository Processing
# ==============================================================================

st.sidebar.title("Workspace")
st.sidebar.caption(
    "CodeMiner control panel for repository input, sessions, and chat settings."
)
st.sidebar.markdown("---")

render_sidebar_panel(
    "Repository input", "Paste a public GitHub URL to process a repository."
)
github_url = st.sidebar.text_input(
    "GitHub repository URL",
    placeholder="https://github.com/username/repo",
    help="Enter the full URL of a public GitHub repository to analyze",
)

render_sidebar_panel("Saved sessions", "Return to a previously processed repository.")
sessions = list_sessions()
selected_session_id = None
if sessions:
    session_ids = [None] + [s["session_id"] for s in sessions if s.get("session_id")]
    session_labels = {
        s[
            "session_id"
        ]: f"{s.get('repo_name', 'Unknown')} • {s.get('updated_at', '')[:19].replace('T', ' ')}"
        for s in sessions
        if s.get("session_id")
    }
    current_session = st.session_state.get("current_session_id")
    current_index = (
        session_ids.index(current_session) if current_session in session_ids else 0
    )
    selected_session_id = st.sidebar.selectbox(
        "Open previous repo session",
        options=session_ids,
        format_func=lambda sid: (
            "Current / New Repo" if sid is None else session_labels.get(sid, sid)
        ),
        index=current_index,
    )
    if selected_session_id and selected_session_id != st.session_state.get(
        "current_session_id"
    ):
        if _load_session_by_id(selected_session_id):
            st.rerun()
else:
    st.sidebar.caption("No saved sessions yet.")

render_sidebar_panel(
    "Processing actions", "Adjust retrieval depth and process the current repository."
)
k = st.sidebar.slider("Retrieved chunks (k)", min_value=1, max_value=12, value=6)

if st.sidebar.button("Process repository", type="primary", use_container_width=True):
    if not github_url:
        st.sidebar.error("Please enter a GitHub URL.")
    elif not github_url.startswith("https://github.com/"):
        st.sidebar.error("Enter a valid public GitHub repository URL.")
    else:
        try:
            _save_current_session()
        except Exception:
            pass

        if os.path.exists("./chroma_db"):
            with st.sidebar.status("Cleaning previous data..."):
                safe_rmtree("./chroma_db")
                st.session_state.repo_processed = False
                st.session_state.repo_stats = None
                st.session_state.messages = []
                st.session_state.chat_history = []
                st.session_state.active_model_name = f"openrouter-{OPENROUTER_MODEL}"

                if "rag_bundle" in st.session_state:
                    del st.session_state["rag_bundle"]
                st.cache_resource.clear()

        with st.sidebar.status("Processing repository...", expanded=True) as status:
            try:
                st.write("Downloading files from GitHub...")
                st.write("Analyzing code structure...")
                st.write("Generating embeddings...")
                st.write("Storing results in the vector database...")

                success, stats = process_repository(github_url)

                if success:
                    st.session_state.repo_processed = True
                    st.session_state.repo_stats = stats
                    if "repo_url" not in st.session_state.repo_stats:
                        st.session_state.repo_stats["repo_url"] = github_url
                    repo_name = st.session_state.repo_stats.get("repo_name")
                    if not repo_name:
                        repo_name = github_url.rstrip("/").split("/")[-1]
                        st.session_state.repo_stats["repo_name"] = repo_name

                    st.session_state.messages = []
                    st.session_state.chat_history = []
                    st.session_state.current_session_id = save_session(
                        repo_name=st.session_state.repo_stats.get(
                            "repo_name", repo_name
                        ),
                        repo_url=github_url,
                        repo_stats=st.session_state.repo_stats,
                        messages=st.session_state.messages,
                        chat_history=[],
                    )
                    save_vectorstore_snapshot(st.session_state.current_session_id)

                    status.update(
                        label="Repository processed successfully.", state="complete"
                    )
                    st.sidebar.success(f"Processed {stats['total_chunks']} code chunks")
                    st.sidebar.info(
                        "Open Repository Stats for the full analytics view."
                    )
                else:
                    status.update(label="Processing failed.", state="error")
                    st.sidebar.error(
                        "Failed to process repository. Check console for details."
                    )

            except Exception as e:
                st.sidebar.error(f"Error: {str(e)}")
                status.update(label="Error occurred.", state="error")

render_sidebar_panel("Quick stats", "Current repository summary.")
if st.session_state.repo_stats:
    stats = st.session_state.repo_stats
    quick_left, quick_right = st.sidebar.columns(2)
    with quick_left:
        st.metric("Files", stats.get("total_files", 0))
    with quick_right:
        st.metric("Chunks", stats.get("total_chunks", 0))
    if st.sidebar.button("Open Repository Stats", use_container_width=True):
        st.switch_page("pages/1_📊_Repository_Stats.py")
else:
    st.sidebar.caption("Process a repository to populate the quick stats panel.")

render_sidebar_panel(
    "Helpful tips", "Ask short, code-focused questions for the best results."
)
st.sidebar.markdown("""
- Ask about a file, function, or flow.
- Reopen a saved session when you want to continue.
- Use Repository Stats for exports and charts.

Example prompts:
- What does the authentication flow do?
- Which files define the API routes?
- How is repository state stored?
""")

if st.session_state.repo_processed and st.session_state.messages:
    if st.sidebar.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        try:
            _save_current_session()
        except Exception:
            pass
        st.rerun()


# ==============================================================================
# MAIN PANEL: Chat Interface
# ==============================================================================

render_hero(
    "Repository Q&A",
    "CodeMiner Chatbot",
    "Ask grounded questions about a processed repository. Keep queries specific to files, functions, or system behavior.",
)
render_pill_row(
    ["OpenRouter GPT", "Gemini", "Groq", "ChromaDB", "Source-backed answers"]
)

# Check if repository has been processed
if not st.session_state.repo_processed:
    render_empty_state(
        "No repository loaded",
        "Paste a GitHub URL in the sidebar, process it, and then ask grounded questions here.",
        accent="Start here",
    )

else:
    # Repository is processed - show chat interface

    # Display current repository
    if st.session_state.repo_stats and "repo_name" in st.session_state.repo_stats:
        render_info_card(
            f"Currently analyzing: {st.session_state.repo_stats['repo_name']}",
            "Ask follow-up questions, then inspect retrieved chunks below when you want source context.",
            accent="Active repo",
        )

        # Load RAG pipeline (cached)
        if "rag_bundle" not in st.session_state:
            with st.spinner("🔄 Loading AI models..."):
                rag_bundle = load_rag_pipeline(
                    OPENROUTER_API_KEY,
                    GROQ_API_KEY,
                    GOOGLE_API_KEY,
                    OPENROUTER_BASE_URL,
                    OPENROUTER_MODEL,
                    GROQ_MODEL,
                    GEMINI_MODEL_FLASH,
                    GEMINI_MODEL_PRO,
                )
                st.session_state.rag_bundle = rag_bundle
                st.session_state.vectorstore = rag_bundle["vectorstore"]

        else:
            # ensure vectorstore exists in session (in case of refresh)
            if "vectorstore" not in st.session_state:
                rag_bundle = load_rag_pipeline(
                    OPENROUTER_API_KEY,
                    GROQ_API_KEY,
                    GOOGLE_API_KEY,
                    OPENROUTER_BASE_URL,
                    OPENROUTER_MODEL,
                    GROQ_MODEL,
                    GEMINI_MODEL_FLASH,
                    GEMINI_MODEL_PRO,
                )
                st.session_state.rag_bundle = rag_bundle
                st.session_state.vectorstore = rag_bundle["vectorstore"]

        active_model_name = st.session_state.get(
            "active_model_name", f"openrouter-{OPENROUTER_MODEL}"
        )
        st.caption(f"Active model: {active_model_name}")

    section_header(
        "Conversation",
        "Chat history",
        "Review the thread before asking the next question.",
    )

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if user_query := st.chat_input(
        "Ask about the codebase (e.g., 'How does routing work?')"
    ):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching codebase and generating answer..."):
                try:
                    # Invoke providers in configured order: OpenRouter, Gemini, Groq.
                    response, active_model_name, _ = _invoke_with_fallback(
                        st.session_state.rag_bundle,
                        user_query,
                        st.session_state.chat_history,
                    )
                    st.session_state.active_model_name = active_model_name

                    answer = response["answer"]

                    # Display answer
                    st.markdown(answer)

                    # Update chat history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.session_state.chat_history.append(
                        HumanMessage(content=user_query)
                    )
                    st.session_state.chat_history.append(AIMessage(content=answer))
                    try:
                        _save_current_session()
                    except Exception:
                        pass

                    # Display retrieved source chunks (with similarity scores)
                    try:
                        docs_and_scores = (
                            st.session_state.vectorstore.similarity_search_with_score(
                                user_query, k=k
                            )
                        )
                    except Exception:
                        docs_and_scores = []

                    with st.expander("📄 View Retrieved Code Chunks"):
                        if docs_and_scores:
                            for i, (doc, score) in enumerate(docs_and_scores):
                                src = doc.metadata.get("source", "Unknown")
                                st.markdown(
                                    f"**Chunk {i+1}** | Source: `{src}` | Similarity: **{score:.4f}**"
                                )

                                # Show snippet and provide surrounding lines if possible
                                st.code(doc.page_content, language=None)

                                # Try to show surrounding lines from the original file if path is available
                                source_path = src
                                try:
                                    from pathlib import Path

                                    p = Path(source_path)
                                    if not p.exists():
                                        # Try relative to cloned repo
                                        p = Path("cloned_repo") / source_path

                                    if p.exists():
                                        full_text = p.read_text(
                                            encoding="utf-8", errors="ignore"
                                        )
                                        snippet = doc.page_content.strip().splitlines()
                                        # find first line of snippet in file
                                        content = full_text.splitlines()
                                        idx = -1
                                        for line in range(len(content)):
                                            if (
                                                snippet
                                                and snippet[0].strip() in content[line]
                                            ):
                                                idx = line
                                                break
                                        if idx >= 0:
                                            start = max(0, idx - 3)
                                            end = min(
                                                len(content), idx + len(snippet) + 3
                                            )
                                            surrounding = "\n".join(content[start:end])
                                            with st.expander("Show surrounding lines"):
                                                st.code(surrounding, language=None)
                                except Exception:
                                    pass

                                st.markdown("---")
                        else:
                            st.write("No retrieved chunks available to display.")

                except Exception as e:
                    st.error(f"❌ Error generating response: {str(e)}")
                    st.info(
                        "💡 Try rephrasing your question or check if the repository was processed correctly."
                    )

# Footer
st.markdown("---")
st.caption("Powered by OpenRouter, Gemini, and Groq • ChromaDB • LangChain • Streamlit")
