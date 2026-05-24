"""Local persistence for repository chat sessions and stats.

Stores each analyzed repository as a JSON file so the app can restore the
previous repo's chat history and metadata across Streamlit restarts.
"""

from __future__ import annotations

import json
from datetime import datetime
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

STATE_DIR = Path(".codeminer_state")
SESSIONS_DIR = STATE_DIR / "sessions"
VECTORSTORE_DIR = STATE_DIR / "vectorstores"
INDEX_FILE = STATE_DIR / "index.json"


def _ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


def _slugify_repo(repo_name: str) -> str:
    cleaned = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in repo_name.strip()
    )
    return cleaned.strip("_") or "repo"


def _session_path(session_id: str) -> Path:
    _ensure_dirs()
    return SESSIONS_DIR / f"{session_id}.json"


def _vectorstore_path(session_id: str) -> Path:
    _ensure_dirs()
    return VECTORSTORE_DIR / session_id


def session_vectorstore_dir(session_id: str) -> str:
    """Return the per-session ChromaDB persist directory as a string path.

    Each session has its own directory under `.codeminer_state/vectorstores/<session_id>/`.
    Routes that read or write the vectorstore should pass this to Chroma directly
    instead of staging through the shared `./chroma_db` directory.
    """
    return str(_vectorstore_path(session_id))


def load_index() -> Dict[str, Any]:
    _ensure_dirs()
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"current_session_id": None, "sessions": []}


def save_index(index: Dict[str, Any]) -> None:
    _ensure_dirs()
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def list_sessions(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    index = load_index()
    sessions = index.get("sessions", [])
    if not isinstance(sessions, list):
        return []
    if user_id is None:
        return sessions
    return [session for session in sessions if session.get("user_id") == user_id]


def save_session(
    repo_name: str,
    repo_url: str,
    repo_stats: Dict[str, Any],
    messages: List[Dict[str, str]],
    chat_history: List[Dict[str, str]],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    _ensure_dirs()

    resolved_session_id = session_id or _slugify_repo(repo_name or repo_url)
    payload = {
        "session_id": resolved_session_id,
        "user_id": user_id,
        "repo_name": repo_name,
        "repo_url": repo_url,
        "repo_stats": repo_stats,
        "messages": messages,
        "chat_history": chat_history,
        "active_model_name": st.session_state.get(
            "active_model_name", "openrouter-openai/gpt-oss-20b:free"
        ),
        "updated_at": datetime.utcnow().isoformat(),
    }

    _session_path(resolved_session_id).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    index = load_index()
    sessions = [
        s
        for s in index.get("sessions", [])
        if s.get("session_id") != resolved_session_id
    ]
    sessions.insert(
        0,
        {
            "session_id": resolved_session_id,
            "user_id": user_id,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "updated_at": payload["updated_at"],
            "message_count": len(messages),
        },
    )
    index["sessions"] = sessions[:20]
    index["current_session_id"] = resolved_session_id
    save_index(index)
    return resolved_session_id


def save_vectorstore_snapshot(session_id: str, source_dir: str = "./chroma_db") -> None:
    """Copy the active vector store to a per-session snapshot directory."""
    src = Path(source_dir)
    if not src.exists():
        return

    dest = _vectorstore_path(session_id)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)


def restore_vectorstore_snapshot(
    session_id: str, target_dir: str = "./chroma_db"
) -> bool:
    """Restore a per-session vector store snapshot into the active chroma_db dir."""
    src = _vectorstore_path(session_id)
    if not src.exists():
        return False

    target = Path(target_dir)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(src, target)
    return True


def load_session(session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if user_id is not None and payload.get("user_id") not in {None, user_id}:
            return None
        return payload
    except Exception:
        return None


def list_tracked_repositories(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sessions = list_sessions(user_id=user_id)
    repos: Dict[str, Dict[str, Any]] = {}
    for session in sessions:
        repo_key = session.get("repo_url") or session.get("repo_name") or session.get("session_id")
        if not repo_key:
            continue
        current = repos.get(repo_key)
        candidate = {
            "repoUrl": session.get("repo_url"),
            "repoName": session.get("repo_name"),
            "lastUpdatedAt": session.get("updated_at"),
            "sessionCount": 1,
        }
        if current:
            current["sessionCount"] = int(current.get("sessionCount", 1)) + 1
            if candidate.get("lastUpdatedAt") and candidate.get("lastUpdatedAt") > current.get("lastUpdatedAt", ""):
                current["lastUpdatedAt"] = candidate["lastUpdatedAt"]
            if candidate.get("repoName") and not current.get("repoName"):
                current["repoName"] = candidate["repoName"]
        else:
            repos[repo_key] = candidate
    return sorted(repos.values(), key=lambda repo: repo.get("lastUpdatedAt") or "", reverse=True)


def delete_session(session_id: str, user_id: Optional[str] = None) -> None:
    path = _session_path(session_id)
    if path.exists():
        if user_id is not None:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("user_id") not in {None, user_id}:
                    return
            except Exception:
                return
        path.unlink()

    index = load_index()
    sessions = [
        s for s in index.get("sessions", []) if s.get("session_id") != session_id
    ]
    index["sessions"] = sessions
    if index.get("current_session_id") == session_id:
        index["current_session_id"] = sessions[0]["session_id"] if sessions else None
    save_index(index)

    vector_dir = _vectorstore_path(session_id)
    if vector_dir.exists():
        shutil.rmtree(vector_dir, ignore_errors=True)
