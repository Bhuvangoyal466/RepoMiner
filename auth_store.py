"""Persistent user auth state for CodeMiner."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_DIR = Path(".codeminer_state")
AUTH_FILE = STATE_DIR / "auth.json"


def _ensure_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.utcnow().isoformat()


def _load_state() -> Dict[str, Any]:
    _ensure_dir()
    if AUTH_FILE.exists():
        try:
            state = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if isinstance(state, dict) and isinstance(state.get("users"), list):
                return state
        except Exception:
            pass
    return {"users": []}


def _save_state(state: Dict[str, Any]) -> None:
    _ensure_dir()
    AUTH_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_value.encode("utf-8"), 120_000
    ).hex()
    return salt_value, digest


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name") or user.get("github_login") or user.get("email"),
        "githubLogin": user.get("github_login"),
        "avatarUrl": user.get("avatar_url"),
        "authMethods": user.get("auth_methods", []),
        "currentSessionId": user.get("current_session_id"),
        "createdAt": user.get("created_at"),
    }


def _find_user_index(state: Dict[str, Any], predicate) -> int:
    for idx, user in enumerate(state.get("users", [])):
        if predicate(user):
            return idx
    return -1


def list_users() -> List[Dict[str, Any]]:
    return list(_load_state().get("users", []))


def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    for user in list_users():
        if user.get("id") == user_id:
            return user
    return None


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    normalized = _normalize_email(email)
    for user in list_users():
        if _normalize_email(user.get("email", "")) == normalized:
            return user
    return None


def find_user_by_github_id(github_id: str) -> Optional[Dict[str, Any]]:
    for user in list_users():
        if str(user.get("github_id")) == str(github_id):
            return user
    return None


def verify_email_password(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = find_user_by_email(email)
    if not user:
        return None

    password_hash = user.get("password_hash")
    password_salt = user.get("password_salt")
    if not password_hash or not password_salt:
        return None

    _, candidate_hash = _hash_password(password, password_salt)
    if candidate_hash != password_hash:
        return None
    return user


def upsert_email_password_user(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    normalized = _normalize_email(email)
    state = _load_state()
    users = state.get("users", [])

    index = _find_user_index(state, lambda user: _normalize_email(user.get("email", "")) == normalized)
    salt, password_hash = _hash_password(password)

    if index >= 0:
        user = users[index]
        existing_hash = user.get("password_hash")
        existing_salt = user.get("password_salt")
        if existing_hash and existing_salt:
            _, candidate_hash = _hash_password(password, existing_salt)
            if candidate_hash != existing_hash:
                raise ValueError("Invalid email or password")
        else:
            user["password_hash"] = password_hash
            user["password_salt"] = salt
        if name and not user.get("name"):
            user["name"] = name
        auth_methods = set(user.get("auth_methods", []))
        auth_methods.add("email")
        user["auth_methods"] = sorted(auth_methods)
        users[index] = user
        _save_state(state)
        return user

    user = {
        "id": secrets.token_hex(16),
        "email": normalized,
        "name": name or normalized.split("@")[0],
        "password_salt": salt,
        "password_hash": password_hash,
        "github_id": None,
        "github_login": None,
        "avatar_url": None,
        "auth_methods": ["email"],
        "current_session_id": None,
        "created_at": _now(),
    }
    users.append(user)
    _save_state(state)
    return user


def upsert_github_user(
    github_id: str,
    github_login: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Dict[str, Any]:
    state = _load_state()
    users = state.get("users", [])
    normalized_email = _normalize_email(email) if email else None

    index = _find_user_index(state, lambda user: str(user.get("github_id")) == str(github_id))
    if index < 0 and normalized_email:
        index = _find_user_index(
            state,
            lambda user: _normalize_email(user.get("email", "")) == normalized_email,
        )

    if index >= 0:
        user = users[index]
        user["github_id"] = str(github_id)
        user["github_login"] = github_login
        if name:
            user["name"] = name
        if email and not user.get("email"):
            user["email"] = normalized_email
        if avatar_url:
            user["avatar_url"] = avatar_url
        auth_methods = set(user.get("auth_methods", []))
        auth_methods.add("github")
        user["auth_methods"] = sorted(auth_methods)
        users[index] = user
        _save_state(state)
        return user

    user = {
        "id": secrets.token_hex(16),
        "email": normalized_email,
        "name": name or github_login,
        "password_salt": None,
        "password_hash": None,
        "github_id": str(github_id),
        "github_login": github_login,
        "avatar_url": avatar_url,
        "auth_methods": ["github"],
        "current_session_id": None,
        "created_at": _now(),
    }
    users.append(user)
    _save_state(state)
    return user


def set_current_session(user_id: str, session_id: Optional[str]) -> None:
    state = _load_state()
    index = _find_user_index(state, lambda user: user.get("id") == user_id)
    if index < 0:
        return
    state["users"][index]["current_session_id"] = session_id
    state["users"][index]["updated_at"] = _now()
    _save_state(state)


def get_current_session_id(user_id: str) -> Optional[str]:
    user = find_user_by_id(user_id)
    if not user:
        return None
    return user.get("current_session_id")


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return _public_user(user)
