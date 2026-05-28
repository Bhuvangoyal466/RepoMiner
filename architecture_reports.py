"""Architecture outputs and report generation.

This module produces:
- Mermaid diagrams (import/dependency graph)
- Onboarding docs (Markdown)
- Summary reports (Markdown + optional PDF)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import ast
import re
import textwrap


DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".codeminer_state", ".repominer_state",
}


def _is_excluded(path: Path, excludes: set[str]) -> bool:
    return any(part in excludes for part in path.parts)


def _safe_read_text(path: Path, max_bytes: int = 500_000) -> str:
    try:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _python_imports(source: str) -> Set[str]:
    out: Set[str] = set()
    try:
        tree = ast.parse(source)
    except Exception:
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    out.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


_IMPORT_RE = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.M)
_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _js_imports(source: str) -> Set[str]:
    out = set(_IMPORT_RE.findall(source))
    out |= set(_REQUIRE_RE.findall(source))
    return out


def build_import_graph(
    repo_root: Path,
    *,
    max_files: int = 300,
    include_exts: Optional[Set[str]] = None,
    excludes: set[str] = DEFAULT_EXCLUDES,
) -> List[Tuple[str, str]]:
    """Return edges (from_file, to_module_or_file)."""

    include_exts = include_exts or {".py", ".js", ".jsx", ".ts", ".tsx"}

    files: List[Path] = []
    for p in repo_root.rglob("*"):
        if len(files) >= max_files:
            break
        if not p.is_file() or p.suffix.lower() not in include_exts:
            continue
        if _is_excluded(p, excludes):
            continue
        files.append(p)

    rel_files = {str(p.relative_to(repo_root)).replace("\\", "/"): p for p in files}

    edges: List[Tuple[str, str]] = []
    for f in files:
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        src = _safe_read_text(f)
        if not src.strip():
            continue

        if f.suffix.lower() == ".py":
            imports = _python_imports(src)
        else:
            imports = _js_imports(src)

        for imp in sorted(imports):
            target = imp

            if imp.startswith("."):
                base = f.parent
                for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".py"):
                    candidate = (base / (imp + ext)).resolve()
                    try:
                        rel_c = str(candidate.relative_to(repo_root)).replace("\\", "/")
                        if rel_c in rel_files or (repo_root / rel_c).is_file():
                            target = rel_c
                            break
                    except Exception:
                        continue

            edges.append((rel, target))

    return edges


_ID_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]")


def _node_id(label: str, cache: Dict[str, str]) -> str:
    if label in cache:
        return cache[label]
    base = _ID_SANITIZE_RE.sub("_", label).strip("_") or "n"
    if base[0].isdigit():
        base = "n_" + base
    nid = base
    i = 2
    used = set(cache.values())
    while nid in used:
        nid = f"{base}_{i}"
        i += 1
    cache[label] = nid
    return nid


def render_mermaid_import_graph(
    edges: List[Tuple[str, str]],
    *,
    max_edges: int = 250,
    internal_only: bool = True,
    known_files: Optional[Set[str]] = None,
) -> str:
    """Render a Mermaid flowchart with valid node IDs and deduplicated edges."""

    lines: List[str] = ["flowchart LR"]

    seen: Set[Tuple[str, str]] = set()
    filtered: List[Tuple[str, str]] = []
    for a, b in edges:
        if a == b:
            continue
        if internal_only and known_files is not None and b not in known_files:
            continue
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(key)

    truncated = max(0, len(filtered) - max_edges)
    filtered = filtered[:max_edges]

    if not filtered:
        lines.append("  empty[\"No internal imports detected\"]")
        return "\n".join(lines) + "\n"

    id_cache: Dict[str, str] = {}
    declared: Set[str] = set()
    for a, b in filtered:
        for label in (a, b):
            nid = _node_id(label, id_cache)
            if nid not in declared:
                safe_label = label.replace('"', "'")
                lines.append(f"  {nid}[\"{safe_label}\"]")
                declared.add(nid)

    for a, b in filtered:
        lines.append(f"  {id_cache[a]} --> {id_cache[b]}")

    if truncated:
        lines.append(f"  %% truncated: {truncated} edges omitted")
    return "\n".join(lines) + "\n"


def generate_architecture_mermaid(repo_root: Path, *, max_files: int = 300) -> str:
    """Convenience wrapper that builds and renders the repository import graph."""

    edges = build_import_graph(repo_root, max_files=max_files)
    include_exts = {".py", ".js", ".jsx", ".ts", ".tsx"}
    known_files: Set[str] = set()
    module_to_file: Dict[str, str] = {}
    for p in repo_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in include_exts:
            continue
        if _is_excluded(p, DEFAULT_EXCLUDES):
            continue
        rel = str(p.relative_to(repo_root)).replace("\\", "/")
        known_files.add(rel)
        mod_dotted = rel.rsplit(".", 1)[0].replace("/", ".")
        module_to_file.setdefault(mod_dotted, rel)
        module_to_file.setdefault(p.stem, rel)

    resolved_edges: List[Tuple[str, str]] = []
    for a, b in edges:
        if b in known_files:
            resolved_edges.append((a, b))
            continue
        top = b.split(".")[0]
        if b in module_to_file:
            resolved_edges.append((a, module_to_file[b]))
        elif top in module_to_file:
            resolved_edges.append((a, module_to_file[top]))

    return render_mermaid_import_graph(resolved_edges, known_files=known_files)


def _tree(repo_root: Path, depth: int = 2) -> str:
    lines: List[str] = []

    def walk(dir_path: Path, prefix: str, level: int) -> None:
        if level > depth:
            return
        items = [p for p in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))]
        items = [p for p in items if not _is_excluded(p, DEFAULT_EXCLUDES)]
        for idx, p in enumerate(items):
            last = idx == len(items) - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + p.name)
            if p.is_dir():
                extension = "    " if last else "│   "
                walk(p, prefix + extension, level + 1)

    lines.append(repo_root.name)
    try:
        walk(repo_root, "", 1)
    except Exception:
        pass
    return "\n".join(lines)


def generate_onboarding_markdown(repo_root: Path, stats: Dict[str, Any] | None = None) -> str:
    """Generate a pragmatic onboarding doc."""

    stats = stats or {}
    has_py = (repo_root / "requirements.txt").is_file() or any(p.suffix == ".py" for p in repo_root.rglob("*.py"))
    has_node = (repo_root / "package.json").is_file()

    setup_bits: List[str] = []
    if has_py:
        setup_bits += [
            "### Python setup",
            "```bash",
            "python -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
            "```",
        ]
    if has_node:
        setup_bits += [
            "### Node setup",
            "```bash",
            "npm install",
            "npm run dev",
            "```",
        ]

    tree = _tree(repo_root, depth=2)

    return "\n".join([
        "# Repository Onboarding",
        "",
        "Auto-generated by RepoMiner to help engineers get productive quickly.",
        "",
        "## Quick facts",
        f"- Total files: {stats.get('total_files', 'N/A')}",
        f"- Total chunks: {stats.get('total_chunks', 'N/A')}",
        "",
        "## Folder structure",
        "```text",
        tree,
        "```",
        "",
        "## Setup",
        *setup_bits,
        "",
        "## Suggested first reads",
        "- README.md",
        "- package.json / requirements.txt",
        "- Main entrypoints (main.py/app.py/src/index.tsx)",
        "",
    ]) + "\n"


def _format_metric(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _detect_entrypoints(repo_root: Path) -> List[str]:
    candidates = [
        "main.py", "app.py", "manage.py", "run.py", "server.py",
        "index.js", "index.ts", "src/index.tsx", "src/index.ts",
        "src/main.ts", "src/main.tsx", "src/App.tsx",
    ]
    found: List[str] = []
    for c in candidates:
        if (repo_root / c).is_file():
            found.append(c)
    return found


def _detect_stack(repo_root: Path) -> List[str]:
    markers = {
        "Python": "requirements.txt",
        "Python (pyproject)": "pyproject.toml",
        "Node.js": "package.json",
        "TypeScript": "tsconfig.json",
        "Docker": "Dockerfile",
        "Docker Compose": "docker-compose.yml",
        "Make": "Makefile",
        "Poetry": "poetry.lock",
        "Pipenv": "Pipfile",
        "Go": "go.mod",
        "Rust": "Cargo.toml",
        "Java (Maven)": "pom.xml",
        "Java (Gradle)": "build.gradle",
    }
    return [label for label, fname in markers.items() if (repo_root / fname).is_file()]


def _module_breakdown(repo_root: Path, *, top_n: int = 10) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    include_exts = {".py", ".js", ".jsx", ".ts", ".tsx"}
    for p in repo_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in include_exts:
            continue
        if _is_excluded(p, DEFAULT_EXCLUDES):
            continue
        rel = p.relative_to(repo_root)
        top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        counts[top] = counts.get(top, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]


def generate_summary_markdown(
    *,
    repo_name: str,
    repo_url: str,
    repo_root: Path | None = None,
    stats: Dict[str, Any] | None = None,
    mermaid_diagram: str | None = None,
    **_legacy: Any,
) -> str:
    """Produce a concise, section-wise architecture report in Markdown."""

    stats = stats or {}

    language_summary = stats.get("language_insights_summary") or {}
    dominant_lang = language_summary.get("dominant_language") or "N/A"
    lang_counts = language_summary.get("language_counts") or {}
    top_languages = sorted(lang_counts.items(), key=lambda kv: -kv[1])[:5] if isinstance(lang_counts, dict) else []

    stack = _detect_stack(repo_root) if repo_root else []
    entrypoints = _detect_entrypoints(repo_root) if repo_root else []
    modules = _module_breakdown(repo_root) if repo_root else []

    lines: List[str] = []

    # 1. Header
    lines += [f"# Architecture Report — {repo_name}", ""]
    if repo_url:
        lines += [f"**Source:** {repo_url}", ""]

    # 2. Overview
    lines += [
        "## 1. Overview",
        "",
        f"- **Files analyzed:** {stats.get('total_files', 'N/A')}",
        f"- **Code chunks:** {stats.get('total_chunks', 'N/A')}",
        f"- **Dominant language:** {dominant_lang}",
        f"- **Languages detected:** {language_summary.get('language_count', len(top_languages))}",
        "",
    ]

    # 3. Tech stack
    lines += ["## 2. Tech Stack", ""]
    if stack:
        lines += [f"- {item}" for item in stack]
    else:
        lines += ["No standard build/manifest files detected."]
    lines += [""]

    # 4. Language composition
    lines += ["## 3. Language Composition", ""]
    if top_languages:
        lines += ["| Language | Files |", "|---|---:|"]
        lines += [f"| {lang} | {count} |" for lang, count in top_languages]
    else:
        lines += ["No language signal available."]
    lines += [""]

    # 5. Module structure
    lines += ["## 4. Module Structure", "",
              "Top-level directories by file count:", ""]
    if modules:
        lines += ["| Module | Files |", "|---|---:|"]
        lines += [f"| {name} | {count} |" for name, count in modules]
    else:
        lines += ["No modules detected."]
    lines += [""]

    # 6. Entry points
    lines += ["## 5. Entry Points", ""]
    if entrypoints:
        lines += [f"- `{ep}`" for ep in entrypoints]
    else:
        lines += ["No conventional entry points identified."]
    lines += [""]

    # 7. Architecture diagram
    lines += ["## 6. Import Graph", ""]
    if mermaid_diagram and mermaid_diagram.strip():
        lines += [
            "Internal module dependencies (truncated for readability):",
            "",
            "```mermaid",
            mermaid_diagram.strip(),
            "```",
        ]
    else:
        lines += ["No internal import edges detected."]
    lines += [""]

    return "\n".join(lines) + "\n"


def generate_summary_pdf(markdown_text: str, title: str = "RepoMiner Summary") -> bytes:
    """Render a simple PDF summary from Markdown text.

    Uses matplotlib's PDF backend so we do not need a heavyweight PDF dependency.
    """

    import io

    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        return b""

    lines = markdown_text.splitlines() or [title]
    wrapped: List[str] = []
    for raw in lines:
        if not raw.strip():
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(raw, width=95) or [raw])

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        page_size = 55
        for start in range(0, len(wrapped), page_size):
            chunk = wrapped[start : start + page_size]
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.patch.set_facecolor("white")
            fig.text(0.06, 0.97, title, fontsize=14, weight="bold", va="top")
            fig.text(0.06, 0.94, f"Page {start // page_size + 1}", fontsize=9, color="#666666", va="top")
            y = 0.90
            for line in chunk:
                fig.text(0.06, y, line or " ", fontsize=9, family="monospace", va="top")
                y -= 0.015
            plt.axis("off")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    return buffer.getvalue()


def build_report_bundle(
    *,
    repo_root: Path,
    stats: Dict[str, Any] | None = None,
    **_legacy: Any,
) -> Dict[str, Any]:
    """Build the complete report artifact set used by the UI and exports."""

    stats = stats or {}

    mermaid_diagram = generate_architecture_mermaid(repo_root)
    onboarding_markdown = generate_onboarding_markdown(repo_root, stats)
    summary_markdown = generate_summary_markdown(
        repo_name=stats.get("repo_name") or repo_root.name,
        repo_url=stats.get("repo_url") or "",
        repo_root=repo_root,
        stats=stats,
        mermaid_diagram=mermaid_diagram,
    )
    summary_pdf = generate_summary_pdf(
        summary_markdown,
        title=f"Architecture Report - {stats.get('repo_name') or repo_root.name}",
    )

    return {
        "mermaid_diagram": mermaid_diagram,
        "onboarding_markdown": onboarding_markdown,
        "summary_markdown": summary_markdown,
        "summary_pdf": summary_pdf,
    }
