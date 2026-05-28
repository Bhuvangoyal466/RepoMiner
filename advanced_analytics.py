"""Language analytics helpers for RepoMiner.

Read-only scans of a cloned repo to derive language composition signals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".codeminer_state", ".repominer_state", ".streamlit",
}

CODE_EXTS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java",
    ".go": "Go", ".cpp": "C++", ".c": "C", ".cs": "C#",
}


def _is_excluded(path: Path, excludes: set[str]) -> bool:
    return any(part in excludes for part in path.parts)


def iter_repo_files(
    repo_root: Path,
    *,
    include_exts: Optional[set[str]] = None,
    excludes: set[str] = DEFAULT_EXCLUDES,
    max_files: int = 5000,
) -> List[Path]:
    files: List[Path] = []
    include_exts = include_exts or set()

    for p in repo_root.rglob("*"):
        if len(files) >= max_files:
            break
        if not p.is_file():
            continue
        if _is_excluded(p, excludes):
            continue
        if include_exts and p.suffix not in include_exts:
            continue
        files.append(p)

    return files


def compute_language_insights(repo_root: Path, max_files: int = 15000) -> Dict[str, Any]:
    """Return language-level insights based on file extensions."""
    files = iter_repo_files(repo_root, include_exts=None, max_files=max_files)

    ext_counts: Dict[str, int] = {}
    dir_counts: Dict[str, int] = {}

    for f in files:
        ext = f.suffix.lower() or "(no-ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        parts = f.relative_to(repo_root).parts
        top_dir = parts[0] if parts else "."
        dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

    language_counts: Dict[str, int] = {}
    for ext, count in ext_counts.items():
        human = CODE_EXTS.get(ext)
        if human:
            language_counts[human] = language_counts.get(human, 0) + count

    return {
        "total_files_scanned": len(files),
        "extension_counts": dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)[:40]),
        "language_counts": dict(sorted(language_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "top_directories": dict(sorted(dir_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]),
    }


def summarize_language_insights(language_insights: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the language insight payload for reports."""

    language_counts = language_insights.get("language_counts") or {}
    if not isinstance(language_counts, dict):
        language_counts = {}

    dominant_language = None
    if language_counts:
        dominant_language = max(language_counts.items(), key=lambda kv: kv[1])[0]

    return {
        "files_scanned": int(language_insights.get("total_files_scanned") or 0),
        "language_count": len(language_counts),
        "dominant_language": dominant_language,
        "top_directories": language_insights.get("top_directories") or {},
        "language_counts": language_counts,
        "extension_counts": language_insights.get("extension_counts") or {},
    }
