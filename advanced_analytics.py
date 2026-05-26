"""Advanced analytics helpers for CodeMiner/RepoMiner.

Goals:
- Provide deeper analytics (complexity, hotspots-over-time, language insights)
- Be safe on large repos (limits + caching-friendly)
- Never mutate the repo; read-only analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import re


@dataclass(frozen=True)
class RepoContext:
    repo_root: Path
    git_dir: Path


DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".codeminer_state", ".repominer_state", ".streamlit",
}

CODE_EXTS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java",
    ".go": "Go", ".cpp": "C++", ".c": "C", ".cs": "C#",
}


def get_repo_context(clone_dir: str = "./cloned_repo") -> RepoContext:
    repo_root = Path(clone_dir).resolve()
    return RepoContext(repo_root=repo_root, git_dir=repo_root / ".git")


def _is_excluded(path: Path, excludes: set[str]) -> bool:
    for part in path.parts:
        if part in excludes:
            return True
    return False


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
    """Return language-level insights based on file extensions and a few heuristics."""
    files = iter_repo_files(repo_root, include_exts=None, max_files=max_files)

    ext_counts: Dict[str, int] = {}
    dir_counts: Dict[str, int] = {}

    for f in files:
        ext = f.suffix.lower() or "(no-ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        top_dir = f.relative_to(repo_root).parts[0] if f.relative_to(repo_root).parts else "."
        dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

    language_counts: Dict[str, int] = {}
    for ext, count in ext_counts.items():
        human = CODE_EXTS.get(ext, None)
        if human:
            language_counts[human] = language_counts.get(human, 0) + count

    return {
        "total_files_scanned": len(files),
        "extension_counts": dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)[:40]),
        "language_counts": dict(sorted(language_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "top_directories": dict(sorted(dir_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]),
    }


def _safe_read_text(path: Path, max_bytes: int = 500_000) -> str:
    try:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _simple_symbol_counts(text: str, ext: str) -> Tuple[int, int]:
    if ext == ".py":
        return text.count("\ndef "), text.count("\nclass ")
    funcs = len(re.findall(r"\bfunction\b", text)) + text.count("=>")
    classes = len(re.findall(r"\bclass\b", text))
    return funcs, classes


def compute_complexity_metrics(
    repo_root: Path,
    *,
    max_files: int = 400,
    include_exts: Optional[set[str]] = None,
) -> List[Dict[str, Any]]:
    """Compute complexity metrics using optional deps (radon, lizard)."""

    include_exts = include_exts or set(CODE_EXTS.keys())
    files = iter_repo_files(repo_root, include_exts=include_exts, max_files=max_files)

    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit
    except Exception:
        cc_visit = None
        mi_visit = None

    try:
        import lizard
    except Exception:
        lizard = None

    rows: List[Dict[str, Any]] = []

    for f in files:
        ext = f.suffix.lower()
        lang = CODE_EXTS.get(ext, ext.lstrip(".") or "Other")
        text = _safe_read_text(f)
        if not text.strip():
            continue
        loc = len(text.splitlines())
        func_count, class_count = _simple_symbol_counts(text, ext)

        cc_avg = None
        cc_max = None
        mi = None

        if ext == ".py" and cc_visit and mi_visit:
            try:
                blocks = cc_visit(text)
                complexities = [b.complexity for b in blocks] if blocks else []
                if complexities:
                    cc_avg = sum(complexities) / len(complexities)
                    cc_max = max(complexities)
                mi = mi_visit(text, True)
            except Exception:
                pass
        elif lizard:
            try:
                analysis = lizard.analyze_source_code(str(f), text)
                fn_ccs = [fn.cyclomatic_complexity for fn in analysis.function_list]
                if fn_ccs:
                    cc_avg = sum(fn_ccs) / len(fn_ccs)
                    cc_max = max(fn_ccs)
            except Exception:
                pass

        rows.append({
            "file": str(f.relative_to(repo_root)),
            "language": lang,
            "loc": loc,
            "functions": func_count,
            "classes": class_count,
            "cc_avg": round(cc_avg, 2) if isinstance(cc_avg, (int, float)) else None,
            "cc_max": cc_max,
            "maintainability_index": round(mi, 2) if isinstance(mi, (int, float)) else None,
        })

    return rows


def compute_hotspots_over_time(
    repo_root: Path,
    *,
    since_days: int = 180,
    granularity: str = "month",
    top_n: int = 12,
    max_commits: int = 4000,
) -> Dict[str, Any]:
    """Compute churn hotspots grouped over time using git history."""

    try:
        from git import Repo
    except Exception:
        return {"error": "GitPython not available"}

    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return {"error": "No .git directory"}

    repo = Repo(str(repo_root))
    since_dt = datetime.now(timezone.utc) - timedelta(days=since_days)

    file_totals: Dict[str, Dict[str, int]] = {}
    bucket_totals: Dict[str, int] = {}
    bucket_file: Dict[str, Dict[str, int]] = {}

    def _bucket(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if granularity == "week":
            year, week, _ = dt.isocalendar()
            return f"{year}-W{week:02d}"
        return dt.strftime("%Y-%m")

    seen = 0
    for commit in repo.iter_commits(max_count=max_commits):
        seen += 1
        cdt = commit.committed_datetime
        if cdt.tzinfo is None:
            cdt = cdt.replace(tzinfo=timezone.utc)
        if cdt < since_dt:
            break

        b = _bucket(cdt)
        stats = commit.stats.files
        for path, stat in stats.items():
            ins = int(stat.get("insertions", 0) or 0)
            dele = int(stat.get("deletions", 0) or 0)
            changed = ins + dele

            ft = file_totals.get(path)
            if not ft:
                ft = {"commits_touched": 0, "insertions": 0, "deletions": 0, "changed_lines": 0}
                file_totals[path] = ft
            ft["commits_touched"] += 1
            ft["insertions"] += ins
            ft["deletions"] += dele
            ft["changed_lines"] += changed

            bucket_totals[b] = bucket_totals.get(b, 0) + changed
            bucket_file.setdefault(b, {})[path] = bucket_file.setdefault(b, {}).get(path, 0) + changed

    top_files = sorted(file_totals.items(), key=lambda kv: kv[1].get("changed_lines", 0), reverse=True)[:top_n]
    top_set = {path for path, _ in top_files}

    top_files_timeline: Dict[str, Dict[str, int]] = {}
    for b, files in bucket_file.items():
        top_files_timeline[b] = {p: c for p, c in files.items() if p in top_set}

    summary = [
        {"file": p, **totals}
        for p, totals in sorted(file_totals.items(), key=lambda kv: kv[1]["changed_lines"], reverse=True)[: max(top_n, 50)]
    ]

    return {
        "commits_scanned": seen,
        "since_days": since_days,
        "granularity": granularity,
        "summary": summary,
        "timeline": dict(sorted(bucket_totals.items())),
        "top_files": [p for p, _ in top_files],
        "top_files_timeline": dict(sorted(top_files_timeline.items())),
    }


def summarize_complexity_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize complexity rows for dashboards and reports."""

    if not rows:
        return {
            "files": 0,
            "loc_total": 0,
            "functions_total": 0,
            "classes_total": 0,
            "cc_max": None,
            "cc_avg": None,
            "maintainability_index_avg": None,
        }

    loc_total = sum(int(row.get("loc") or 0) for row in rows)
    functions_total = sum(int(row.get("functions") or 0) for row in rows)
    classes_total = sum(int(row.get("classes") or 0) for row in rows)
    cc_values = [row.get("cc_max") for row in rows if isinstance(row.get("cc_max"), (int, float))]
    avg_values = [row.get("cc_avg") for row in rows if isinstance(row.get("cc_avg"), (int, float))]
    mi_values = [row.get("maintainability_index") for row in rows if isinstance(row.get("maintainability_index"), (int, float))]

    return {
        "files": len(rows),
        "loc_total": loc_total,
        "functions_total": functions_total,
        "classes_total": classes_total,
        "cc_max": max(cc_values) if cc_values else None,
        "cc_avg": round(sum(avg_values) / len(avg_values), 2) if avg_values else None,
        "maintainability_index_avg": round(sum(mi_values) / len(mi_values), 2) if mi_values else None,
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
