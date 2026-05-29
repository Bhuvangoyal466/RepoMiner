"""
Repository Statistics Page
===========================
Displays detailed statistics about the processed GitHub repository including:
- Total files and code chunks
- Technology stack (complete, scrollable list)
- Images processed
- Additional metadata
"""

import streamlit as st
from ingest import get_repo_stats
import os
import pandas as pd
import json
from pathlib import Path
from git import Repo
from architecture_reports import build_report_bundle
from ui import (
    apply_base_ui,
    render_sidebar_brand,
    render_hero,
    render_info_card,
    render_metric_card,
    section_header,
    render_pill_row,
    render_empty_state,
)


def _rows_from_stats(stats: dict, key: str) -> list[dict]:
    rows = (stats.get(key) or []) if isinstance(stats, dict) else []
    return [row for row in rows if isinstance(row, dict)]


# Page Configuration
st.set_page_config(
    page_title="RepoMiner Repository Stats", page_icon="📊", layout="wide"
)

apply_base_ui()
render_sidebar_brand("RepoMiner", "Repository intelligence workspace")

render_hero(
    "Repository Stats",
    "RepoMiner analytics",
    "A compact view of the processed repository with metrics, stacks, exports, and deeper signals.",
)

section_header(
    "Analytics",
    "Repository Statistics",
    "The data behind retrieval, presented as a quick scan instead of a report.",
)

# Check if repository has been processed
if not st.session_state.get("repo_processed", False):
    render_empty_state(
        "No repository processed yet",
        "Process a GitHub repository in Chatbot first. The stats view unlocks after ingestion completes.",
        accent="Setup",
    )
    if st.button("Open Chatbot", use_container_width=True):
        st.switch_page("pages/3_💬_Chatbot.py")

elif st.session_state.get("repo_stats"):
    stats = st.session_state.repo_stats

    section_header(
        "Overview", "Key metrics", "A quick summary of the processed repository."
    )
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Total Files", str(stats.get("total_files", 0)), "Total analyzed files"
        )

    with col2:
        render_metric_card(
            "Code Chunks", str(stats.get("total_chunks", 0)), "Semantic chunks created"
        )

    with col3:
        render_metric_card(
            "Images",
            str(stats.get("images_processed", 0)),
            "Images and diagrams processed",
        )

    with col4:
        # Calculate average chunk size if available
        avg_chunk = "N/A"
        if stats.get("total_chunks", 0) > 0 and stats.get("total_files", 0) > 0:
            avg_chunk = f"{stats['total_chunks'] // stats['total_files']}"
        render_metric_card("Avg Chunks/File", avg_chunk, "Average chunk density")

    st.markdown("---")

    section_header(
        "Stack",
        "Technology stack",
        "All programming languages and file types detected in the repository.",
    )

    # Display tech stack in a scrollable, well-formatted container
    tech_stack = stats.get("languages", None)

    # Normalize languages data: accept list, dict, or comma-separated string
    languages = []
    if isinstance(tech_stack, dict):
        languages = list(tech_stack.keys())
    elif isinstance(tech_stack, list):
        languages = tech_stack
    elif isinstance(tech_stack, str):
        languages = [lang.strip() for lang in tech_stack.split(",") if lang.strip()]

    if languages:

        render_pill_row(languages[:10])

        # Also display as expandable text for copy-paste
        with st.expander("📋 View as Text (Click to Copy)"):
            try:
                st.code(json.dumps(languages, indent=2), language=None)
            except Exception:
                st.code(str(languages), language=None)
    else:
        render_empty_state(
            "No technology stack information available",
            "The current repository stats payload did not include language metadata.",
            accent="Stack",
        )

    section_header("Export", "Download stats", "Save the analytics for offline review.")
    try:
        export_data = {
            "repo_name": stats.get("repo_name"),
            "repo_url": stats.get("repo_url"),
            "total_files": stats.get("total_files"),
            "total_chunks": stats.get("total_chunks"),
            "images_processed": stats.get("images_processed"),
            "languages": languages,
        }

        df = pd.DataFrame(
            [
                {
                    "metric": k,
                    "value": json.dumps(v) if isinstance(v, (list, dict)) else v,
                }
                for k, v in export_data.items()
            ]
        )

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        json_bytes = json.dumps(export_data, indent=2).encode("utf-8")

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Export Stats CSV",
                data=csv_bytes,
                file_name="repo_stats.csv",
                mime="text/csv",
            )
        with col_b:
            st.download_button(
                "⬇️ Export Stats JSON",
                data=json_bytes,
                file_name="repo_stats.json",
                mime="application/json",
            )
    except Exception:
        st.error("Failed to prepare export data")

    section_header(
        "Details",
        "Additional information",
        "Repository metadata and processing settings in a compact format.",
    )

    col1, col2 = st.columns(2)

    with col1:
        repo_body = []
        if "repo_url" in stats:
            repo_body.append(f"URL: {stats['repo_url']}")
        if "repo_name" in stats:
            repo_body.append(f"Name: {stats['repo_name']}")
        if os.path.exists("./chroma_db"):
            repo_body.append("Vector DB: ChromaDB (Local)")
            repo_body.append("Status: Active")
        render_info_card(
            "Repository details",
            "\n".join(repo_body) if repo_body else "No repository metadata available.",
            accent="Metadata",
        )

    with col2:
        render_info_card(
            "Processing details",
            "Embedding model: all-MiniLM-L6-v2\nEmbedding dimensions: 384\nRetrieval strategy: Similarity Search (k=6)\nLLM order: OpenRouter -> Gemini -> Groq",
            accent="Pipeline",
        )

    st.markdown("---")

    section_header(
        "Visuals",
        "Visual breakdown",
        "Charts that show the repository shape without extra noise.",
    )

    col1, col2 = st.columns(2)

    with col1:
        ext_break = stats.get("extension_breakdown", {}) or {}
        if ext_break:
            try:
                df_ext = pd.DataFrame(
                    list(ext_break.items()), columns=["extension", "count"]
                )
                df_ext = df_ext.set_index("extension")
                st.bar_chart(df_ext)
                with st.expander("View extension breakdown as table"):
                    st.dataframe(df_ext)
            except Exception:
                st.write(ext_break)
        else:
            render_empty_state(
                "No file type data available",
                "This repository stats payload does not include an extension breakdown.",
                accent="Files",
            )

    with col2:
        lang_break = stats.get("languages", {}) or {}
        if isinstance(lang_break, dict) and lang_break:
            try:
                df_lang = pd.DataFrame(
                    list(lang_break.items()), columns=["language", "count"]
                ).set_index("language")
                st.bar_chart(df_lang)
            except Exception:
                st.write(lang_break)
        else:
            render_empty_state(
                "Language breakdown not available",
                "The current stats payload did not include a language count map.",
                accent="Languages",
            )

        top_files = stats.get("top_files", []) or []
        if top_files:
            try:
                tf_df = pd.DataFrame(top_files)
                tf_df["size_kb"] = (tf_df["size"] / 1024).round(2)
                st.dataframe(
                    tf_df[["path", "size_kb"]].rename(
                        columns={"path": "file", "size_kb": "size (KB)"}
                    )
                )
            except Exception:
                st.write(top_files)

        render_info_card(
            "Pipeline status",
            "Repository cloned, analyzed, embedded, and stored for chat retrieval.",
            accent="Ready",
        )

    st.markdown("---")
    if st.button("🔄 Refresh Statistics", type="secondary", use_container_width=True):
        st.rerun()

    section_header(
        "People",
        "Contributor analytics",
        "A small view into activity patterns when a local git history is available.",
    )
    try:
        if os.path.exists("./cloned_repo/.git"):
            repo = Repo("./cloned_repo")
            commits = list(repo.iter_commits(max_count=5000))
            if commits:
                author_counts = {}
                dates = []
                for c in commits:
                    name = (
                        c.author.name
                        if c.author and c.author.name
                        else (c.author.email if c.author else "Unknown")
                    )
                    author_counts[name] = author_counts.get(name, 0) + 1
                    dates.append(c.committed_datetime)

                top = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
                top_df = pd.DataFrame(top, columns=["author", "commits"])
                st.table(top_df)

                # Commits over time
                if dates:
                    df_dates = pd.DataFrame({"date": dates})
                    df_dates["month"] = df_dates["date"].dt.to_period("M").astype(str)
                    timeline = df_dates.groupby("month").size()
                    st.line_chart(timeline)
            else:
                st.info("No commit history available (shallow clone or no commits)")
        else:
            st.info(
                "Repository clone not found; contributor analytics require a local clone."
            )
    except Exception as e:
        st.error(f"Failed to compute contributor analytics: {e}")

    section_header(
        "GitHub",
        "Issues and pull requests",
        "Optional repository insights fetched from the public GitHub API.",
    )
    github_token = st.text_input(
        "GitHub Personal Access Token (optional)",
        type="password",
        help="Needed to access private repos or increase rate limits",
    )
    repo_url = stats.get("repo_url")
    if repo_url:
        from urllib.parse import urlparse

        parsed = urlparse(repo_url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            owner, repo_name = parts[0], parts[1]
        else:
            owner = repo_name = None

        if owner and repo_name:
            if st.button("Fetch Issues & PRs Summary"):
                import requests

                headers = {"Accept": "application/vnd.github+json"}
                if github_token:
                    headers["Authorization"] = f"Bearer {github_token}"

                try:
                    issues_res = requests.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}/issues?state=open&per_page=50",
                        headers=headers,
                        timeout=10,
                    )
                    prs_res = requests.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}/pulls?state=open&per_page=50",
                        headers=headers,
                        timeout=10,
                    )

                    if issues_res.ok:
                        issues = [
                            i for i in issues_res.json() if "pull_request" not in i
                        ]
                        st.markdown(f"**Open issues:** {len(issues)}")
                        # Top 3 active issues by comments
                        top_issues = sorted(
                            issues, key=lambda x: x.get("comments", 0), reverse=True
                        )[:3]
                        for it in top_issues:
                            st.markdown(
                                f"- **{it.get('title')}** ({it.get('comments',0)} comments)"
                            )
                            body = it.get("body") or ""
                            st.write(body[:500] + ("..." if len(body) > 500 else ""))
                    else:
                        st.error(f"Failed to fetch issues: {issues_res.status_code}")

                    if prs_res.ok:
                        prs = prs_res.json()
                        st.markdown(f"**Open pull requests:** {len(prs)}")
                        top_prs = sorted(
                            prs, key=lambda x: x.get("comments", 0), reverse=True
                        )[:3]
                        for pr in top_prs:
                            st.markdown(
                                f"- **{pr.get('title')}** ({pr.get('comments',0)} comments)"
                            )
                            st.write((pr.get("body") or "")[:500])
                    else:
                        st.error(f"Failed to fetch PRs: {prs_res.status_code}")

                except Exception as e:
                    st.error(f"Error fetching GitHub data: {e}")
        else:
            st.info("Could not parse owner/repo from repo URL")
    else:
        st.info("Repo URL not available in stats")

    section_header(
        "Supply Chain",
        "Dependency and license analysis",
        "A lightweight scan of repository dependency manifests and licensing.",
    )
    try:
        from pathlib import Path

        repo_root = Path("./cloned_repo")
        deps = []
        # Python requirements
        req_file = repo_root / "requirements.txt"
        if req_file.exists():
            lines = req_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for ln in lines:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    deps.append({"name": ln, "source": "requirements.txt"})

        # pyproject.toml (basic parse)
        pyproj = repo_root / "pyproject.toml"
        if pyproj.exists():
            txt = pyproj.read_text(encoding="utf-8", errors="ignore")
            # crude parsing for [tool.poetry.dependencies] or [project]
            for line in txt.splitlines():
                if "=" in line and not line.strip().startswith("["):
                    parts = line.split("=")
                    if len(parts) >= 2:
                        name = parts[0].strip().strip('"')
                        deps.append({"name": name, "source": "pyproject.toml"})

        # package.json
        pkg = repo_root / "package.json"
        if pkg.exists():
            import json as _json

            pj = _json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            for section in ("dependencies", "devDependencies"):
                for k, v in pj.get(section, {}).items():
                    deps.append({"name": k, "version": v, "source": "package.json"})

        if deps:
            st.dataframe(pd.DataFrame(deps))
        else:
            st.info("No dependency files found in repository")

        # License detection
        lic_file = repo_root / "LICENSE"
        if lic_file.exists():
            st.markdown("**LICENSE file found:**")
            with st.expander("View LICENSE"):
                st.code(lic_file.read_text(encoding="utf-8", errors="ignore"))
        else:
            st.info("No LICENSE file found; cannot auto-detect license")
    except Exception as e:
        st.error(f"Dependency analysis failed: {e}")

    section_header(
        "Language insights",
        "Language composition",
        "Languages detected during ingestion.",
    )

    repo_root = Path("./cloned_repo")
    language_summary = stats.get("language_insights_summary") or {}

    bundle = build_report_bundle(repo_root=repo_root, stats=stats)

    render_info_card(
        "Language insights",
        f"Scanned {language_summary.get('files_scanned', 0)} files across {language_summary.get('language_count', 0)} languages. Dominant language: {language_summary.get('dominant_language') or 'N/A'}.",
        accent="Stack",
    )
    if language_summary.get("language_counts"):
        df_lang = pd.DataFrame(
            list(language_summary["language_counts"].items()),
            columns=["language", "count"],
        ).set_index("language")
        st.bar_chart(df_lang)
    with st.expander("Language and extension details"):
        st.json(language_summary)

    report_cols = st.columns(3)
    with report_cols[0]:
        st.download_button(
            "⬇️ Summary Markdown",
            data=bundle["summary_markdown"].encode("utf-8"),
            file_name="repo_summary.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with report_cols[1]:
        pdf_bytes = bundle.get("summary_pdf") or b""
        if pdf_bytes:
            st.download_button(
                "⬇️ Summary PDF",
                data=pdf_bytes,
                file_name="repo_summary.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button(
                "Summary PDF unavailable", disabled=True, use_container_width=True
            )
    with report_cols[2]:
        st.download_button(
            "⬇️ Onboarding Markdown",
            data=bundle["onboarding_markdown"].encode("utf-8"),
            file_name="repo_onboarding.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if bundle.get("mermaid_diagram"):
        with st.expander("Architecture diagram source"):
            st.code(bundle["mermaid_diagram"], language="mermaid")

    section_header(
        "Security",
        "Basic security scan",
        "A lightweight secret-pattern check to surface obvious risks.",
    )
    try:
        import re
        from pathlib import Path

        patterns = {
            "Private Key": re.compile(r"-----BEGIN .*PRIVATE KEY-----"),
            "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
            "GitHub Token (ghp_)": re.compile(r"ghp_[0-9A-Za-z_]{36}"),
            "API Key Assignment": re.compile(
                r'api[_-]?key\s*[=:]\s*["\']?([A-Za-z0-9\-_.]+)'
            ),
        }

        findings = []
        repo_root = Path("./cloned_repo")
        if repo_root.exists():
            for p in repo_root.rglob("*"):
                if not p.is_file():
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    for name, pat in patterns.items():
                        for m in pat.finditer(text):
                            snippet = m.group(0)
                            # find line number
                            lines = text[: m.start()].splitlines()
                            ln = len(lines) + 1
                            findings.append(
                                {
                                    "file": str(p.relative_to(repo_root)),
                                    "issue": name,
                                    "line": ln,
                                    "snippet": snippet[:200],
                                }
                            )
                except Exception:
                    continue

        if findings:
            st.markdown(
                "Potential secrets or risky patterns detected — review manually"
            )
            st.dataframe(pd.DataFrame(findings))
        else:
            st.success("No obvious secrets detected by the lightweight scan")
    except Exception as e:
        st.error(f"Security scan failed: {e}")

else:
    st.error("Repository statistics not available")
    st.info("Please process a repository first from the Chatbot page")

# Footer
st.markdown("---")
st.caption("Statistics are updated each time a new repository is processed.")
