# CodeMiner Frontend

This is a Vite + React + TypeScript frontend for the CodeMiner project. It provides a modern workspace UI for repository ingestion, chat, and analytics.

Quick start
```bash
cd "CodeMiner/frontend"
npm install
npm run dev
```

Run backend adapter (optional — provides REST endpoints mapping to the Streamlit internals):
```bash
# from repository root
python backend_api.py
# or run with uvicorn for production:
uvicorn backend_api:app --reload --host 127.0.0.1 --port 8000
```

API expectations
- `POST /api/auth/login` { email, password } → sign in or create a local fallback account
- `POST /api/auth/logout` → clear the session cookie
- `GET /api/auth/me` → current signed-in user
- `GET /api/auth/providers` → enabled auth providers
- `GET /api/auth/github/start` → begin GitHub OAuth
- `GET /api/sessions` → list of sessions (id, repoUrl, repoName, updatedAt, messageCount)
- `GET /api/repos` → tracked repositories for the current user
- `POST /api/process` { repoUrl } → starts processing, returns session id/status
- `GET /api/sessions/:id` → load a session (session payload)
- `DELETE /api/sessions/:id` → delete a session
- `GET /api/sessions/:id/stats` → repository analytics payload
- `POST /api/sessions/:id/chat` { prompt } → assistant reply containing sources
- `GET /api/sessions/:id/chunks` → list of retrieved source chunks
- `GET /api/sessions/:id/export?format=csv|json` → export stats
- `GET /api/provider/status` → provider/model availability info

Notes
- The FastAPI adapter exposes auth/session endpoints and scopes sessions/repos to the signed-in user. Repository analysis requires sign-in. The app uses `baseURL: /api` by default.

Full RAG behavior
- The FastAPI adapter can proxy retrieval and model calls to synthesize grounded answers. To enable high-quality LLM responses via OpenAI, set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) in your environment before starting the adapter. The adapter will attempt to call OpenAI's ChatCompletion with retrieved context and fall back to a snippet-based summary if the model call fails.
 - The FastAPI adapter supports provider fallbacks in this order: OpenRouter -> Groq -> Gemini (Google). Set the following environment variables to enable providers:
	 - `OPENROUTER_API_KEY` and optionally `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`
	 - `GROQ_API_KEY` and optionally `GROQ_MODEL`
	 - `GOOGLE_API_KEY` and optionally `GEMINI_MODEL_PRO`/`GEMINI_MODEL_FLASH`
 The adapter will try OpenRouter first (using OpenAI-compatible calls), then Groq via `langchain_groq` if available, then Gemini via `langchain_google_genai`. If none are available the adapter falls back to a snippet-based summary.
