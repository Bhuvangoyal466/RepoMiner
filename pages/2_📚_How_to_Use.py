"""
How to Use Page
===============
Modern guide for using the Advanced RAG GitHub Repository Chatbot.
"""

import streamlit as st

from ui import (
    apply_base_ui,
    render_hero,
    render_info_card,
    section_header,
    render_pill_row,
)

st.set_page_config(page_title="How to Use", page_icon="📚", layout="wide")
apply_base_ui()

render_hero(
    "Guide",
    "How to use the repository chatbot",
    "A concise walkthrough for processing repositories, asking better questions, and reading results with confidence.",
)

render_pill_row(
    ["Minimal workflow", "Semantic search", "Source-backed answers", "Responsive UI"]
)

section_header(
    "Overview",
    "What this app does",
    "A retrieval-augmented assistant for exploring GitHub repositories.",
)
st.markdown("""
This chatbot helps you understand any GitHub repository through natural language.
It combines intelligent code search, AI explanations, and conversation memory so you can move from overview to detail quickly.

- **Intelligent code search** finds relevant snippets using semantic similarity.
- **AI understanding** explains code in clear technical language.
- **Conversational memory** keeps the context for follow-up questions.
- **Multimodal support** can surface code, markdown, and images.
""")

section_header(
    "Workflow",
    "Step-by-step guide",
    "The fastest path from repository URL to useful answers.",
)
step_cols = st.columns(2)

with step_cols[0]:
    render_info_card(
        "Step 1: Open the Chatbot page",
        "Use the sidebar navigation to reach the main interface.",
        accent="Start here",
    )
    render_info_card(
        "Step 2: Paste a GitHub repository URL",
        "Use a full public repository URL like https://github.com/facebook/react.",
        accent="Input",
    )

with step_cols[1]:
    render_info_card(
        "Step 3: Process the repository",
        "The app clones the repo, chunks code, generates embeddings, and stores them in ChromaDB.",
        accent="Processing",
    )
    render_info_card(
        "Step 4: Ask a question",
        "Once processing completes, ask about architecture, functions, flows, or implementation details.",
        accent="Chat",
    )

section_header(
    "Examples",
    "Good questions to ask",
    "Use specific prompts to get better, more grounded answers.",
)
tab_arch, tab_frontend, tab_backend, tab_security = st.tabs(
    ["Architecture", "Frontend", "Backend", "Security"]
)

with tab_arch:
    st.markdown("""
        - What is the overall architecture of this project?
        - How is the codebase structured?
        - What design patterns are being used?
        - Explain the folder structure.
        """)

with tab_frontend:
    st.markdown("""
        - How does routing work?
        - What state management approach is used?
        - Explain the component hierarchy.
        - How are API calls made from the frontend?
        """)

with tab_backend:
    st.markdown("""
        - What database is being used?
        - How are models or schemas defined?
        - Explain the API endpoints.
        - How is error handling implemented?
        """)

with tab_security:
    st.markdown("""
        - How does authentication work?
        - Where are API keys stored?
        - What security measures are implemented?
        - How is data validation handled?
        """)

section_header(
    "Tips", "Best practices", "Use the app more effectively with a few simple habits."
)
tip_cols = st.columns(2)

with tip_cols[0]:
    render_info_card(
        "Do",
        "Be specific, ask follow-up questions, reference exact features, and ask about implementation details.",
        accent="Recommended",
    )

with tip_cols[1]:
    render_info_card(
        "Avoid",
        "Asking about code outside the repo, requesting unrelated new features, or using very vague prompts.",
        accent="Not ideal",
    )

section_header(
    "Reference", "Glossary", "Short definitions for the terms used throughout the app."
)
st.markdown("""
- **RAG**: Retrieval-Augmented Generation, combining search with an LLM for grounded answers.
- **Embedding**: Vector representation of code or text used for semantic search.
- **Chunk**: A meaningful piece of code, such as a function or class block.
- **ChromaDB**: Local vector database used to store embeddings.
- **Retriever**: Component that finds the most relevant chunks for a query.
""")

section_header(
    "Walkthroughs",
    "Short practical workflows",
    "Use these when you want a quick answer or a specific file path.",
)
st.markdown("""
### 1) Quick Architecture Summary
1. Process a repository from the Chatbot sidebar.
2. Ask: "What is the overall architecture of this project?"
3. Inspect the retrieved chunks to verify sources.

### 2) Find Authentication Code
1. Process the repository.
2. Ask: "Where is authentication implemented?" or "Show login flow".
3. Open any referenced chunks to view surrounding lines.

### 3) Dependency Check
1. Process the repo.
2. Ask: "List dependencies and their versions".
3. Use the Repository Stats export to download repo_stats.json for offline analysis.
""")

section_header(
    "Troubleshooting",
    "Common fixes",
    "Quick answers for the most common setup and runtime issues.",
)
with st.expander("No responses or empty answers"):
    st.markdown("""
1. Ensure the repository was processed successfully.
2. Large repositories may take several minutes.
3. Re-run processing if embeddings generation failed.
""")

with st.expander("API key or model errors"):
    st.markdown("""
- Verify your Groq or Gemini API key is set in the environment.
- Restart the Streamlit app after updating secrets.

```powershell
$env:GROQ_API_KEY = "your_groq_api_key_here"
streamlit run app.py
```
""")

with st.expander("ChromaDB or permission errors"):
    st.markdown("""
- On Windows you may see permission errors for ./chroma_db.
- Ensure the process has write permission or delete the folder and re-run processing.

```powershell
Remove-Item -Recurse -Force .\chroma_db
streamlit run app.py
```
""")

section_header(
    "Technical",
    "How the system works",
    "The core model and retrieval setup, summarized cleanly.",
)
tab1, tab2, tab3 = st.tabs(["AI Models", "RAG Flow", "Tech Stack"])

with tab1:
    st.markdown("""
        **Embedding model: all-MiniLM-L6-v2**
        - Converts code into 384-dimensional vectors.
        - Enables semantic similarity search.

        **Language model: LLaMA 3.1-8B-Instant**
        - Used through Groq for fast generation.
        - Generates technical answers grounded in the retrieved context.
        """)

with tab2:
    st.markdown("""
        1. Your question is embedded into a vector.
        2. ChromaDB finds the top matching code chunks.
        3. Retrieved context is added to the prompt.
        4. The model generates an answer with file references.
        """)

with tab3:
    st.markdown("""
        - **Frontend**: Streamlit
        - **Vector DB**: ChromaDB
        - **Embeddings**: HuggingFace sentence transformers
        - **LLM**: Groq + LLaMA 3
        - **Framework**: LangChain
        - **Language**: Python 3.10+
        """)

section_header(
    "FAQ",
    "Frequently asked questions",
    "A few quick answers before you start using the app.",
)
with st.expander("Is this free to use?"):
    st.markdown("""
        The application is open source. Groq and Hugging Face have free tiers, while ChromaDB runs locally.
        """)

with st.expander("Can I use private repositories?"):
    st.markdown("""
        Currently, the app is designed for public repositories.
        """)

st.success("You're all set. Head over to the Chatbot page to start exploring code.")
st.caption("Tip: Open Repository Stats after processing to see detailed analytics.")
