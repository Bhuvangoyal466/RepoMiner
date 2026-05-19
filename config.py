"""Simple configuration loader for environment variables.

Behavior:
- Attempts to load local `.env` files via `python-dotenv` if available.
- Supports OpenRouter first, Gemini second, and Groq third.
- Allows any configured provider to satisfy startup validation.
- Exposes helpers for startup validation and quick debugging.

Usage:
        from config import load_app_config, ensure_required_keys
        cfg = load_app_config()
        ensure_required_keys(cfg)

"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List

try:
    # Optional dependency: if installed, load .env automatically
    from dotenv import load_dotenv

    load_dotenv(override=True)
    load_dotenv(".env.local", override=True)
except Exception:
    # dotenv not installed — fall back to environment variables
    pass


REQUIRED_KEYS: List[str] = ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"]


def _first_present(keys: Iterable[str]) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if _is_real_value(value):
            return value
    return None


def _is_real_value(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    if normalized.startswith("your_"):
        return False
    if "placeholder" in normalized:
        return False
    if normalized in {"changeme", "replace_me", "replace-me", "todo"}:
        return False
    return True


def _is_enabled(value: str | None) -> bool:
    if not _is_real_value(value):
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_app_config() -> Dict[str, str | None]:
    """Load and normalize environment variables used by the app."""
    openrouter_key = _first_present(["OPENROUTER_API_KEY"])
    gemini_key = _first_present(["GEMINI_API_KEY", "GOOGLE_API_KEY"])
    groq_key = _first_present(["GROQ_API_KEY"])

    gemini_backup_flag = os.getenv("ENABLE_GEMINI_BACKUP")
    gemini_backups_enabled = (
        True if gemini_backup_flag is None else _is_enabled(gemini_backup_flag)
    )

    if openrouter_key:
        os.environ.setdefault("OPENROUTER_API_KEY", openrouter_key)
    else:
        os.environ.pop("OPENROUTER_API_KEY", None)

    if gemini_key and gemini_backups_enabled:
        os.environ.setdefault("GEMINI_API_KEY", gemini_key)
        os.environ.setdefault("GOOGLE_API_KEY", gemini_key)
    else:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)

    if groq_key:
        os.environ.setdefault("GROQ_API_KEY", groq_key)
    else:
        os.environ.pop("GROQ_API_KEY", None)

    return {
        "OPENROUTER_API_KEY": openrouter_key,
        "OPENROUTER_MODEL": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
        "OPENROUTER_BASE_URL": os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        "GROQ_API_KEY": groq_key,
        "GROQ_MODEL": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "ENABLE_GEMINI_BACKUP": "true" if gemini_backups_enabled else None,
        "GEMINI_API_KEY": (
            os.getenv("GEMINI_API_KEY")
            if _is_real_value(os.getenv("GEMINI_API_KEY"))
            else gemini_key
        ),
        "GEMINI_MODEL_FLASH": os.getenv("GEMINI_MODEL_FLASH", "gemini-2.5-flash"),
        "GEMINI_MODEL_PRO": os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro"),
        "GOOGLE_API_KEY": (
            os.getenv("GOOGLE_API_KEY")
            if _is_real_value(os.getenv("GOOGLE_API_KEY"))
            else gemini_key
        ),
    }


def ensure_required_keys(config: Dict[str, str | None] | None = None) -> None:
    """Raise RuntimeError if the required runtime env vars are missing.

    At least one provider must be configured so the chatbot can build a
    fallback chain.
    """
    current = config or load_app_config()
    providers = ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"]
    available = [k for k in providers if _is_real_value(current.get(k))]
    if not available:
        example = "\n# .env example\n" + "\n".join(
            [
                "OPENROUTER_API_KEY=your_openrouter_key",
                "GEMINI_API_KEY=your_gemini_key",
                "GROQ_API_KEY=your_groq_key",
            ]
        )
        raise RuntimeError(
            "Missing required environment variables: configure at least one of "
            + ", ".join(providers)
            + ".\nCreate a .env or export them in your shell. Example:"
            + example
        )


def ensure_keys(required_keys: List[str] | None = None) -> None:
    """Backward-compatible wrapper for older imports."""
    if required_keys:
        missing = [k for k in required_keys if not _is_real_value(os.getenv(k))]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return
    ensure_required_keys()


def get_config() -> Dict[str, str | None]:
    """Backward-compatible config accessor."""
    return load_app_config()


def _mask(value: str | None, keep: int = 4) -> str:
    if not value:
        return "(missing)"
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "..." + value[-keep:]


if __name__ == "__main__":
    cfg = load_app_config()
    print("Configuration quick-check:")
    for k, v in cfg.items():
        status = "SET" if _is_real_value(v) else "MISSING"
        masked = _mask(v)
        print(f"- {k}: {status} — {masked}")
