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

    rel_files = {str(p.relative_to(repo_root)).replace("\\\\", "/"): p for p in files}

    edges: List[Tuple[str, str]] = []
    for f in files:
        rel = str(f.relative_to(repo_root)).replace("\\\\", "/")
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
                        rel_c = str(candidate.relative_to(repo_root)).replace("\\\\", "/")
                        if rel_c in rel_files or (repo_root / rel_c).is_file():
                            target = rel_c
                            break
                    except Exception:
                        continue

            edges.append((rel, target))

    return edges


def render_mermaid_import_graph(edges: List[Tuple[str, str]], *, max_edges: int = 800) -> str:
    """Render a Mermaid flowchart."""
    lines = ["flowchart LR"]
    for i, (a, b) in enumerate(edges[:max_edges]):
        lines.append(f"  \"{a}\" --> \"{b}\"")
    if len(edges) > max_edges:
        lines.append(f"  %% truncated: {len(edges) - max_edges} edges omitted")
    return "\n".join(lines) + "\n"


def generate_architecture_mermaid(repo_root: Path, *, max_files: int = 300) -> str:
    """Convenience wrapper that builds and renders the repository import graph."""

    edges = build_import_graph(repo_root, max_files=max_files)
    return render_mermaid_import_graph(edges)


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


def generate_summary_markdown(
    *,
    repo_name: str,
    repo_url: str,
    stats: Dict[str, Any] | None = None,
    complexity_rows: List[Dict[str, Any]] | None = None,
    coverage_rows: List[Dict[str, Any]] | None = None,
    hotspot_rows: List[Dict[str, Any]] | None = None,
    rag_eval_summary: Dict[str, Any] | None = None,
    mermaid_diagram: str | None = None,
) -> str:
    stats = stats or {}
    complexity_rows = complexity_rows or []
    coverage_rows = coverage_rows or []
    hotspot_rows = hotspot_rows or []
    rag_eval_summary = rag_eval_summary or {}

    def top(items: List[Dict[str, Any]], key: str, n: int = 8) -> List[Dict[str, Any]]:
        return sorted(items, key=lambda r: (r.get(key) is None, -(r.get(key) or 0)))[:n]

    top_complex = top(complexity_rows, "cc_max", 8)
    top_hot = top(hotspot_rows, "changed_lines", 8)

    cov_avg = None
    if coverage_rows:
        vals = [r.get("coverage_pct") for r in coverage_rows if isinstance(r.get("coverage_pct"), (int, float))]
        if vals:
            cov_avg = sum(vals) / len(vals)

    lines: List[str] = []
    lines += [
        f"# RepoMiner Summary: {repo_name}",
        "",
        f"URL: {repo_url}",
        "",
        "## Ingestion",
        f"- Files: {stats.get('total_files', 'N/A')}",
        f"- Chunks: {stats.get('total_chunks', 'N/A')}",
        "",
        "## Complexity",
    ]
    if top_complex:
        lines += ["| file | language | loc | cc_max | MI |", "|---|---:|---:|---:|---:|"]
        for r in top_complex:
            lines.append(f"| {r.get('file')} | {r.get('language')} | {r.get('loc')} | {r.get('cc_max')} | {r.get('maintainability_index')} |")
    else:
        lines += ["No complexity data."]

    lines += ["", "## Coverage"]
    if cov_avg is not None:
        lines += [f"- Average: {cov_avg:.2f}%"]
    else:
        lines += ["No coverage imported."]

    lines += ["", "## Evaluation"]
    if rag_eval_summary:
        lines += [
            f"- Cases: {_format_metric(rag_eval_summary.get('cases'))}",
            f"- Hit@k: {_format_metric(rag_eval_summary.get('hit_at_k'))}",
            f"- MRR: {_format_metric(rag_eval_summary.get('mrr'))}",
            f"- Precision@k: {_format_metric(rag_eval_summary.get('precision_at_k'))}",
            f"- Recall@k: {_format_metric(rag_eval_summary.get('recall_at_k'))}",
            f"- Avg retrieval latency (ms): {_format_metric(rag_eval_summary.get('avg_retrieval_ms'))}",
            f"- P95 retrieval latency (ms): {_format_metric(rag_eval_summary.get('p95_retrieval_ms'))}",
        ]
    else:
        lines += ["No RAG evaluation dataset imported."]

    lines += ["", "## Hotspots (churn)"]
    if top_hot:
        lines += ["| file | commits | insertions | deletions | changed |", "|---|---:|---:|---:|---:|"]
        for r in top_hot:
            lines.append(f"| {r.get('file')} | {r.get('commits_touched')} | {r.get('insertions')} | {r.get('deletions')} | {r.get('changed_lines')} |")
    else:
        lines += ["No git history."]

    if mermaid_diagram:
        lines += ["", "## Architecture", "```mermaid", mermaid_diagram.strip(), "```"]

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
    complexity_rows: List[Dict[str, Any]] | None = None,
    coverage_rows: List[Dict[str, Any]] | None = None,
    hotspot_rows: List[Dict[str, Any]] | None = None,
    rag_eval_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the complete report artifact set used by the UI and exports."""

    stats = stats or {}
    coverage_rows = coverage_rows or []
    complexity_rows = complexity_rows or []
    hotspot_rows = hotspot_rows or []
    rag_eval_summary = rag_eval_summary or {}

    mermaid_diagram = generate_architecture_mermaid(repo_root)
    onboarding_markdown = generate_onboarding_markdown(repo_root, stats)
    summary_markdown = generate_summary_markdown(
        repo_name=stats.get("repo_name") or repo_root.name,
        repo_url=stats.get("repo_url") or "",
        stats=stats,
        complexity_rows=complexity_rows,
        coverage_rows=coverage_rows,
        hotspot_rows=hotspot_rows,
        rag_eval_summary=rag_eval_summary,
        mermaid_diagram=mermaid_diagram,
    )
    summary_pdf = generate_summary_pdf(
        summary_markdown,
        title=f"RepoMiner Summary - {stats.get('repo_name') or repo_root.name}",
    )

    return {
        "mermaid_diagram": mermaid_diagram,
        "onboarding_markdown": onboarding_markdown,
        "summary_markdown": summary_markdown,
        "summary_pdf": summary_pdf,
    }
