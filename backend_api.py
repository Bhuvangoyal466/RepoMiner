import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import time
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import uvicorn

# Load .env (OPENROUTER_API_KEY, GOOGLE_API_KEY, GROQ_API_KEY, ...) before any
# os.getenv() calls below. Without this, the chat route silently skips every
# provider and falls back to the "configured model is needed" stub.
from config import load_app_config

_APP_CONFIG = load_app_config()

logging.basicConfig(
    level=os.getenv("CODEMINER_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("codeminer.backend")
logger.info(
    "Provider keys loaded: openrouter=%s gemini=%s groq=%s",
    bool(_APP_CONFIG.get("OPENROUTER_API_KEY")),
    bool(_APP_CONFIG.get("GEMINI_API_KEY")),
    bool(_APP_CONFIG.get("GROQ_API_KEY")),
)

from auth_store import (
    find_user_by_id,
    get_current_session_id,
    public_user,
    set_current_session,
    upsert_email_password_user,
    upsert_github_user,
    verify_email_password,
)
from repo_session_store import (
    list_tracked_repositories,
    list_sessions,
    load_session,
    save_session,
    delete_session,
    session_vectorstore_dir,
)
from ingest import process_repository
import openai
import json
import requests
import os

# Embeddings & vector store (used for similarity search)
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
except Exception:
    HuggingFaceEmbeddings = None
    Chroma = None

app = FastAPI()

SESSION_COOKIE_NAME = "codeminer_session"
GITHUB_STATE_COOKIE = "codeminer_github_state"
GITHUB_NEXT_COOKIE = "codeminer_github_next"


class LoginRequest(BaseModel):
    email: str
    password: str


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://127.0.0.1:5173/")


def _github_redirect_uri() -> str:
    return os.getenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:5173/api/auth/github/callback",
    )


def _auth_secret() -> bytes:
    return os.getenv("CODEMINER_SESSION_SECRET", "codeminer-dev-secret").encode(
        "utf-8"
    )


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


def _issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 24 * 7,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_auth_secret(), body.encode("utf-8"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def _verify_token(token: str | None) -> Dict[str, Any] | None:
    if not token or "." not in token:
        return None
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(
            _auth_secret(), body.encode("utf-8"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(signature)):
            return None
        payload = json.loads(_b64decode(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return find_user_by_id(user_id)
    except Exception:
        return None


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def _set_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        GITHUB_STATE_COOKIE,
        state,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=600,
        path="/api/auth/github",
    )


def _clear_state_cookie(response: Response) -> None:
    response.delete_cookie(GITHUB_STATE_COOKIE, path="/api/auth/github")


def _set_next_cookie(response: Response, next_path: str) -> None:
    response.set_cookie(
        GITHUB_NEXT_COOKIE,
        next_path,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=600,
        path="/api/auth/github",
    )


def _clear_next_cookie(response: Response) -> None:
    response.delete_cookie(GITHUB_NEXT_COOKIE, path="/api/auth/github")


def _current_user(request: Request) -> Dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    return _verify_token(token)


def _require_user(request: Request) -> Dict[str, Any]:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _resolve_session_id(session_id: str, user_id: str) -> str:
    if session_id != "active":
        return session_id
    current_session_id = get_current_session_id(user_id)
    if current_session_id:
        return current_session_id
    sessions = list_sessions(user_id=user_id)
    if sessions:
        return sessions[0].get("session_id")
    raise HTTPException(status_code=404, detail="No active session found")


def _github_enabled() -> bool:
    return bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"))


@app.get("/api/auth/providers")
def api_auth_providers():
    return {
        "github": _github_enabled(),
        "emailPassword": True,
    }


@app.get("/api/auth/me")
def api_auth_me(request: Request):
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return public_user(user)


@app.post("/api/auth/login")
def api_auth_login(body: LoginRequest, response: Response):
    try:
        user = upsert_email_password_user(body.email, body.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _issue_token(user["id"])
    _set_auth_cookie(response, token)
    return public_user(user)


@app.post("/api/auth/logout")
def api_auth_logout(response: Response):
    _clear_auth_cookie(response)
    return {"ok": True}


@app.get("/api/auth/github/start")
def api_auth_github_start(next: str = "/"):
    if not _github_enabled():
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    safe_next = next if isinstance(next, str) and next.startswith("/") and not next.startswith("//") else "/"

    state = secrets.token_urlsafe(24)
    params = urlencode(
        {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "redirect_uri": _github_redirect_uri(),
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "true",
        }
    )
    response = RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{params}", status_code=302
    )
    _set_state_cookie(response, state)
    _set_next_cookie(response, safe_next)
    return response


@app.get("/api/auth/github/callback")
def api_auth_github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    frontend_login = f"{_frontend_url().rstrip('/')}/login"
    if error or not code or not state:
        response = RedirectResponse(url=f"{frontend_login}?error=github_auth_failed")
        _clear_state_cookie(response)
        _clear_next_cookie(response)
        return response

    cookie_state = request.cookies.get(GITHUB_STATE_COOKIE)
    if not cookie_state or cookie_state != state:
        response = RedirectResponse(url=f"{frontend_login}?error=github_auth_failed")
        _clear_state_cookie(response)
        _clear_next_cookie(response)
        return response

    try:
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "code": code,
                "redirect_uri": _github_redirect_uri(),
                "state": state,
            },
            timeout=20,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError("Missing GitHub access token")

        user_response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            timeout=20,
        )
        user_response.raise_for_status()
        github_user = user_response.json()

        email = github_user.get("email")
        if not email:
            emails_response = requests.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
                timeout=20,
            )
            if emails_response.ok:
                emails = emails_response.json()
                for entry in emails:
                    if entry.get("primary") and entry.get("verified"):
                        email = entry.get("email")
                        break

        user = upsert_github_user(
            github_id=str(github_user.get("id")),
            github_login=github_user.get("login") or email or "github-user",
            name=github_user.get("name") or github_user.get("login"),
            email=email,
            avatar_url=github_user.get("avatar_url"),
        )

        next_path = request.cookies.get(GITHUB_NEXT_COOKIE) or "/"
        response = RedirectResponse(url=f"{_frontend_url().rstrip('/')}{next_path}", status_code=302)
        _set_auth_cookie(response, _issue_token(user["id"]))
        _clear_state_cookie(response)
        _clear_next_cookie(response)
        return response
    except Exception:
        response = RedirectResponse(url=f"{frontend_login}?error=github_auth_failed")
        _clear_state_cookie(response)
        _clear_next_cookie(response)
        return response


@app.get("/api/repos")
def api_list_repos(request: Request):
    user = _require_user(request)
    return list_tracked_repositories(user_id=user["id"])


class ProcessRequest(BaseModel):
    repoUrl: str


@app.get('/api/sessions')
def api_list_sessions(request: Request):
    user = _require_user(request)
    sessions = list_sessions(user_id=user["id"])
    # normalize keys to frontend expectations
    out = []
    for s in sessions:
        out.append({
            'id': s.get('session_id'),
            'repoUrl': s.get('repo_url'),
            'repoName': s.get('repo_name'),
            'updatedAt': s.get('updated_at'),
            'messageCount': s.get('message_count', 0),
        })
    return out


def _user_scoped_session_id(user_id: str, repo_name: str, repo_url: str) -> str:
    """Build a session_id namespaced to the user so two users analyzing the same repo
    do not overwrite each other's session file or vectorstore snapshot."""
    base = repo_name or (repo_url.rstrip('/').split('/')[-1] if repo_url else 'repo')
    safe_base = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in base).strip('_') or 'repo'
    user_tag = hashlib.sha256((user_id or 'anon').encode('utf-8')).hexdigest()[:8]
    return f"u{user_tag}-{safe_base}"


@app.post('/api/process')
def api_process(req: ProcessRequest, request: Request):
    user = _require_user(request)
    repo = req.repoUrl

    # Decide the session_id up front so we can ingest directly into the
    # per-session vectorstore directory. Writing to a session-scoped path
    # avoids the SQLITE_READONLY_DBMOVED race where a stale Chroma connection
    # to ./chroma_db (held by an in-flight chat request) blocks the writer.
    repo_name_guess = repo.rstrip('/').split('/')[-1] if repo else 'repo'
    scoped_session_id = _user_scoped_session_id(user["id"], repo_name_guess, repo)
    session_dir = session_vectorstore_dir(scoped_session_id)

    success, stats = process_repository(repo, persist_dir=session_dir)
    if not success:
        raise HTTPException(status_code=500, detail='Processing failed')

    repo_name = stats.get('repo_name') or repo_name_guess
    session_id = save_session(
        repo_name,
        repo,
        stats,
        messages=[],
        chat_history=[],
        user_id=user["id"],
        session_id=scoped_session_id,
    )
    set_current_session(user["id"], session_id)
    return {'sessionId': session_id, 'stats': stats}


@app.get('/api/sessions/{session_id}')
def api_get_session(session_id: str, request: Request):
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    payload = load_session(session_id, user_id=user["id"])
    if not payload:
        raise HTTPException(status_code=404, detail='Session not found')
    return payload


@app.delete('/api/sessions/{session_id}')
def api_delete_session(session_id: str, request: Request):
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    delete_session(session_id, user_id=user["id"])
    remaining_sessions = list_sessions(user_id=user["id"])
    set_current_session(
        user["id"],
        remaining_sessions[0].get("session_id") if remaining_sessions else None,
    )
    return {'ok': True}


@app.post('/api/sessions/{session_id}/activate')
def api_activate_session(session_id: str, request: Request):
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    payload = load_session(session_id, user_id=user["id"])
    if not payload:
        raise HTTPException(status_code=404, detail='Session not found')
    set_current_session(user["id"], session_id)
    return {'ok': True, 'sessionId': session_id}


@app.get('/api/sessions/{session_id}/stats')
def api_get_stats(session_id: str, request: Request):
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    payload = load_session(session_id, user_id=user["id"])
    if not payload:
        raise HTTPException(status_code=404, detail='Session not found')
    return payload.get('repo_stats', {})


@app.get('/api/sessions/{session_id}/chunks')
def api_get_chunks(session_id: str, request: Request, page: int = 1, per_page: int = 20):
    """Return paginated chunks from the session's per-session Chroma store.

    Opens the session's own persist directory directly and returns documents with
    path, content, score (omitted here), and inferred startLine/endLine where
    possible.
    """
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    session = load_session(session_id, user_id=user["id"])
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    session_dir = session_vectorstore_dir(session_id)
    if not (os.path.exists(session_dir) and os.listdir(session_dir)) or HuggingFaceEmbeddings is None or Chroma is None:
        return {"chunks": [], "page": page, "per_page": per_page, "total": 0}

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        vectorstore = Chroma(persist_directory=session_dir, embedding_function=embeddings)

        # Attempt to read all stored documents from the underlying collection
        docs_result = {}
        try:
            docs_result = vectorstore._collection.get(include=["documents", "metadatas"])
        except Exception:
            # Fallback to vectorstore.get if available
            try:
                docs_result = vectorstore.get(include=["documents", "metadatas"])
            except Exception:
                docs_result = {}

        documents = []
        docs_list = docs_result.get("documents") or []
        metadatas = docs_result.get("metadatas") or []
        for i, doc_text in enumerate(docs_list):
            meta = metadatas[i] if i < len(metadatas) else {}
            src = meta.get("source") or meta.get("source_path") or meta.get("path") or "unknown"
            documents.append({"id": f"chunk-{i}", "path": src, "content": doc_text, "score": None})

        total = len(documents)
        start = (page - 1) * per_page
        end = start + per_page
        page_docs = documents[start:end]

        # Infer startLine/endLine by searching snippet in file
        for d in page_docs:
            try:
                p = d["path"]
                if not p:
                    continue
                from pathlib import Path

                pth = Path(p)
                if not pth.exists():
                    pth = Path("cloned_repo") / p
                if pth.exists():
                    full_text = pth.read_text(encoding="utf-8", errors="ignore")
                    content_lines = d["content"].splitlines()
                    idx = -1
                    lines = full_text.splitlines()
                    if content_lines:
                        first = content_lines[0].strip()
                        for li in range(len(lines)):
                            if first and first in lines[li]:
                                idx = li
                                break
                    if idx >= 0:
                        d["startLine"] = max(1, idx + 1)
                        d["endLine"] = min(len(lines), idx + len(content_lines))
            except Exception:
                pass

        return {"chunks": page_docs, "page": page, "per_page": per_page, "total": total}

    except Exception as e:
        print("Chunk listing error:", e)
        raise HTTPException(status_code=500, detail="Failed to list chunks")


@app.post('/api/sessions/{session_id}/chat')
def api_chat(session_id: str, request: Request, body: Dict[str, Any]):
    """Perform a similarity search against the session vectorstore snapshot and return a concise grounded answer.

    The route restores the per-session vectorstore snapshot, retrieves the most relevant chunks for the prompt,
    and sends a compact context bundle to the provider so the returned answer stays short and specific.
    """
    user = _require_user(request)
    session_id = _resolve_session_id(session_id, user["id"])
    session = load_session(session_id, user_id=user["id"])
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    prompt = None
    history_payload: list = []
    if isinstance(body, dict):
        prompt = body.get('prompt')
        k = int(body.get('k', 6))
        raw_history = body.get('history') or []
        if isinstance(raw_history, list):
            history_payload = raw_history
    else:
        k = 6

    if not prompt:
        raise HTTPException(status_code=400, detail='Missing prompt')

    # Normalize prior turns into OpenAI-style messages. Accept either
    # {role: "user"|"assistant"|"human"|"ai", text|content: "..."}.
    def _normalize_history(items, max_turns: int = 12):
        normalized = []
        for item in items[-max_turns:]:
            if not isinstance(item, dict):
                continue
            role = (item.get('role') or '').lower()
            content = item.get('text') or item.get('content') or ''
            if not isinstance(content, str) or not content.strip():
                continue
            if role in ('user', 'human'):
                normalized.append({'role': 'user', 'content': content.strip()})
            elif role in ('assistant', 'ai', 'bot'):
                normalized.append({'role': 'assistant', 'content': content.strip()})
        return normalized

    history_messages = _normalize_history(history_payload)

    sources = []
    session_dir = session_vectorstore_dir(session_id)

    if os.path.exists(session_dir) and os.listdir(session_dir) and HuggingFaceEmbeddings is not None and Chroma is not None:
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            vectorstore = Chroma(persist_directory=session_dir, embedding_function=embeddings)
            docs_and_scores = vectorstore.similarity_search_with_score(prompt, k=k)
            for i, (doc, score) in enumerate(docs_and_scores):
                sources.append(
                    {
                        "id": f"src-{i}",
                        "path": doc.metadata.get("source", "unknown"),
                        "content": doc.page_content,
                        "score": float(score),
                    }
                )
        except Exception:
            logger.exception("Retrieval error for session %s", session_id)

    # Try to call the configured provider with a compact retrieved context bundle.
    reply_text = None
    # Provider fallback sequence: OpenRouter -> Groq -> Gemini
    def _extract_text_response(result):
        if result is None:
            return None
        if isinstance(result, str):
            text = result.strip()
            return text or None

        content = getattr(result, 'content', None)
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        elif content is not None:
            try:
                if isinstance(content, list):
                    pieces = []
                    for part in content:
                        if isinstance(part, dict):
                            pieces.append(str(part.get('text') or part.get('content') or ''))
                        else:
                            pieces.append(str(part))
                    text = ''.join(pieces).strip()
                    if text:
                        return text
            except Exception:
                pass
            text = str(content).strip()
            if text:
                return text

        if isinstance(result, dict):
            choices = result.get('choices')
            if choices:
                try:
                    message = choices[0].get('message') if isinstance(choices[0], dict) else None
                    if isinstance(message, dict):
                        text = (message.get('content') or '').strip()
                        if text:
                            return text
                except Exception:
                    pass

            text = (result.get('text') or result.get('output_text') or '').strip()
            if text:
                return text

        choices = getattr(result, 'choices', None)
        if choices:
            try:
                choice = choices[0]
                message = getattr(choice, 'message', None)
                if message is not None:
                    text = getattr(message, 'content', None)
                    if isinstance(text, str) and text.strip():
                        return text.strip()
                text = getattr(choice, 'text', None)
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except Exception:
                pass

        generations = getattr(result, 'generations', None)
        if generations:
            try:
                for generation_group in generations:
                    for generation in generation_group:
                        text = getattr(generation, 'text', None)
                        if isinstance(text, str) and text.strip():
                            return text.strip()
            except Exception:
                pass

        text = str(result).strip()
        if text and text not in {'{}', '[]'}:
            return text
        return None

    def call_providers_with_fallback(messages):
        attempts = []

        # 1) OpenRouter via OpenAI-compatible API
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_base = os.getenv("OPENROUTER_BASE_URL")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
        if openrouter_key:
            logger.info("Trying OpenRouter (model=%s base=%s)", openrouter_model, openrouter_base)
            try:
                client = openai.OpenAI(api_key=openrouter_key, base_url=openrouter_base) if openrouter_base else openai.OpenAI(api_key=openrouter_key)
                resp = client.chat.completions.create(model=openrouter_model, messages=messages, temperature=0.2, max_tokens=8192)
                text = _extract_text_response(resp)
                if text:
                    logger.info("OpenRouter returned %d chars", len(text))
                    return text
                attempts.append("openrouter: empty response")
                logger.warning("OpenRouter returned empty response: %r", resp)
            except Exception as e:
                attempts.append(f"openrouter: {e}")
                logger.exception("OpenRouter call failed")
        else:
            attempts.append("openrouter: no key")
            logger.info("Skipping OpenRouter — OPENROUTER_API_KEY not set")

        # 2) Groq via langchain_groq if available
        groq_key = os.getenv("GROQ_API_KEY")
        groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if groq_key:
            logger.info("Trying Groq (model=%s)", groq_model)
            try:
                from langchain_groq import ChatGroq

                groq_llm = ChatGroq(model=groq_model, groq_api_key=groq_key, temperature=0.2, max_tokens=8192)
                result = groq_llm.invoke(messages) if hasattr(groq_llm, "invoke") else groq_llm(messages)
                text = _extract_text_response(result)
                if text:
                    logger.info("Groq returned %d chars", len(text))
                    return text
                attempts.append("groq: empty response")
                logger.warning("Groq returned empty response: %r", result)
            except Exception as e:
                attempts.append(f"groq: {e}")
                logger.exception("Groq call failed")
        else:
            attempts.append("groq: no key")
            logger.info("Skipping Groq — GROQ_API_KEY not set")

        # 3) Gemini via langchain_google_genai if available
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL_PRO") or os.getenv("GEMINI_MODEL_FLASH", "gemini-2.5-pro")
        if gemini_key:
            logger.info("Trying Gemini (model=%s)", gemini_model)
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                gemini_llm = ChatGoogleGenerativeAI(model=gemini_model, google_api_key=gemini_key, temperature=0.2, max_output_tokens=8192)
                out = gemini_llm.invoke(messages) if hasattr(gemini_llm, "invoke") else gemini_llm(messages)
                text = _extract_text_response(out)
                if text:
                    logger.info("Gemini returned %d chars", len(text))
                    return text
                attempts.append("gemini: empty response")
                logger.warning("Gemini returned empty response: %r", out)
            except Exception as e:
                attempts.append(f"gemini: {e}")
                logger.exception("Gemini call failed")
        else:
            attempts.append("gemini: no key")
            logger.info("Skipping Gemini — GOOGLE_API_KEY/GEMINI_API_KEY not set")

        logger.error("All providers failed or returned empty. Attempts: %s", attempts)
        return None

    try:
        qa_system_prompt = (
            "You are a friendly senior engineer chatting with a teammate about a codebase. "
            "Use only the retrieved context below to answer.\n\n"
            "How to respond:\n"
            "- Reply in plain conversational English, like a chatbot. No markdown at all: "
            "no headings, no asterisks for bold or italics, no bullet points, no tables, no "
            "fenced code blocks. Write in natural sentences and short paragraphs.\n"
            "- Be concise. Aim for 3 to 6 sentences. Only go longer if the question truly "
            "needs it. Do not pad and do not restate the question.\n"
            "- When you mention a file or function, just write its name inline in the "
            "sentence (for example: the auth flow lives in backend_api.py). Do not wrap it "
            "in backticks or quotes.\n"
            "- Do not add a meta summary, do not describe the structure of your answer, do "
            "not announce what you are about to do.\n"
            "- If the retrieved context does not cover the question, say so in one sentence "
            "and mention which file would most likely have the answer.\n\n"
            "Retrieved Context:\n{context}"
        )
        context_lines = []
        for source in sources:
            content = source['content'].strip().replace('\r\n', '\n')
            context_lines.append(
                f"File: {source['path']}\nSimilarity: {source['score']:.4f}\nContent:\n{content}"
            )
        context_text = "\n\n---\n\n".join(context_lines) if context_lines else "No relevant context retrieved."
        system_message = qa_system_prompt.replace("{context}", context_text)

        messages = [{"role": "system", "content": system_message}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "Calling LLM provider chain (prompt_len=%d, sources=%d, history_turns=%d, context_chars=%d)",
            len(prompt), len(sources), len(history_messages), len(context_text),
        )
        reply_text = call_providers_with_fallback(messages)
    except Exception:
        logger.exception("Provider fallback error")
        reply_text = None

    # Fallback synthesized reply
    if not reply_text:
        if sources:
            top_paths = ", ".join([s["path"] for s in sources[:3]])
            reply_text = (
                f"I could not reach a configured LLM, so here is the raw context. "
                f"Most relevant files: {top_paths}. "
                "Check the backend logs for the provider chain errors."
            )
        else:
            reply_text = "I could not find relevant repository context for that question."

    created_at = datetime.utcnow().isoformat()
    user_message_id = "msg-" + secrets.token_hex(6)
    assistant_message_id = "msg-" + secrets.token_hex(6)

    # Persist this turn into the session so reopening the session in the UI
    # restores the conversation. Stored with both `text` (React) and `content`
    # (Streamlit) so either client can render it.
    try:
        prior_messages = list(session.get("messages") or [])
        prior_messages.append({
            "id": user_message_id,
            "role": "user",
            "text": prompt,
            "content": prompt,
            "createdAt": created_at,
        })
        prior_messages.append({
            "id": assistant_message_id,
            "role": "assistant",
            "text": reply_text,
            "content": reply_text,
            "createdAt": created_at,
            "sources": sources,
        })
        save_session(
            repo_name=session.get("repo_name") or "repo",
            repo_url=session.get("repo_url") or "",
            repo_stats=session.get("repo_stats") or {},
            messages=prior_messages,
            chat_history=session.get("chat_history") or [],
            user_id=user["id"],
            session_id=session_id,
        )
    except Exception:
        logger.exception("Failed to persist chat turn to session %s", session_id)

    return {
        "id": assistant_message_id,
        "role": "assistant",
        "text": reply_text,
        "createdAt": created_at,
        "sources": sources,
    }


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)
