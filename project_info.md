# CodeMiner — Project Info

## Overview

CodeMiner is an advanced Retrieval-Augmented Generation (RAG) Streamlit app for exploring GitHub repositories. It ingests a repo, creates semantic embeddings, stores them in a local ChromaDB vector store, and provides a chat UI that answers user questions with source-backed code snippets.



## Viva Quick Notes (Section-wise, concise)

### File-wise Uses (root)

- `app.py`: Home page, navigation, and shared session initialization.
- `config.py`: Loads API keys/model config from environment and validates providers.
- `ingest.py`: Repository ingestion pipeline (clone, parse, chunk, embed, store, stats).
- `repo_session_store.py`: Saves/restores sessions and vectorstore snapshots.
- `ui.py`: Shared CSS/theme and reusable UI helper components.
- `requirements.txt`: Project dependencies.
- `README.md`: Setup and usage guide.
- `project_info.md`: Technical documentation.
- `viva_prep.md`: Viva-focused snippets and Q&A.

### Folder-wise Uses

- `pages/`: Streamlit multi-page app modules.
- `pages/3_💬_Chatbot.py`: Main chatbot + RAG execution + provider fallback.
- `pages/1_📊_Repository_Stats.py`: Repository analytics, exports, and lightweight scans.
- `pages/2_📚_How_to_Use.py`: User guide and troubleshooting.
- `chroma_db/`: Local ChromaDB persistence (embeddings + metadata/index files).
- `.codeminer_state/`: Local session JSON and vectorstore snapshot storage.
- `cloned_repo/`: Temporary local clone of the target GitHub repository.

### Complete Workflow After GitHub URL Is Sent

1. User enters GitHub URL in Chatbot sidebar and clicks Process.
2. Old `chroma_db` is cleared (if present).
3. Repository is cloned into `./cloned_repo`.
4. Files are discovered and filtered (code/docs/text; ignores noisy folders).
5. Code is syntax-chunked; docs/text are recursively split into chunks.
6. Each chunk is converted to an embedding vector (`all-MiniLM-L6-v2`).
7. Chunks + metadata + vectors are persisted in ChromaDB (`./chroma_db`).
8. Repo stats are computed and stored in session state.
9. User asks a question in chat.
10. Question is embedded and top-k similar chunks are retrieved from ChromaDB.
11. Retrieved chunks + chat history are sent to LLM chain.
12. Answer is shown; retrieved source chunks are shown for traceability.
13. Session + vectorstore snapshot are saved for resume.

### Chunking: Why, How, What It Stores

- Why needed: Full repositories are too large for direct prompting; chunking improves relevance and token efficiency.
- How it works:
   - Code: `LanguageParser` (structure-aware, prefers function/class boundaries).
   - Docs/text: `RecursiveCharacterTextSplitter` with overlap.
- What each chunk stores:
   - `page_content` (actual chunk text/code)
   - metadata (`source` file path, `chunk_id`, content type)

### Embeddings: Why, How, What It Stores

- What they are: Numeric vectors representing semantic meaning of chunks/questions.
- How they work:
   - Chunk text -> `all-MiniLM-L6-v2` -> 384-dimensional vector.
   - User query -> same model -> query vector.
   - Similarity search matches nearest chunk vectors.
- What is stored:
   - vector values,
   - linked chunk text,
   - chunk metadata (file path/type/id).

### What Is ChromaDB (simple viva explanation)

- ChromaDB is a local vector database used to store embeddings and run semantic similarity search.
- In this project it persists in `./chroma_db`:
   - `chroma.sqlite3` for persisted metadata/storage internals,
   - index folders for fast nearest-neighbor retrieval.
- During chat it returns top relevant chunks, which are passed to the LLM to generate grounded answers.
