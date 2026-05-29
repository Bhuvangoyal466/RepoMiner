"""Shared Streamlit UI helpers for the repository chatbot app.

Centralized styling and small HTML helpers used by the Streamlit pages.
Keep helpers presentation-only: they must not touch backend/RAG logic.
"""

from __future__ import annotations

import html as _html
import streamlit as st


def apply_base_ui() -> None:
    """Inject the app-wide CSS theme and utility rules.

    Avoid heavy animations so Streamlit remains responsive.
    """

    st.markdown(
        """
<style>
  :root{
    --bg-1: #f4f8fc;
    --bg-2: #eef6ff;
    --surface: #ffffff;
    --surface-2: #f8fbff;
    --muted: #64748b;
    --text: #0f172a;
    --primary-700: #1d4ed8;
    --primary-600: #2563eb;
    --primary-500: #3b82f6;
    --accent-600: #0f766e;
    --border: rgba(15,23,42,0.08);
    --sidebar-surface: linear-gradient(180deg, #fbfdff 0%, #f2f7ff 100%);
    --sidebar-accent: linear-gradient(135deg, rgba(37,99,235,0.15), rgba(15,118,110,0.10));
    --radius-lg: 16px;
    --radius-xl: 24px;
    --shadow-1: 0 12px 36px rgba(2,6,23,0.06);
    --shadow-2: 0 20px 50px rgba(2,6,23,0.10);
  }

  html,body,[class*="css"]{font-family: Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial;}
  .stApp{ background:
      radial-gradient(circle at top left, rgba(59,130,246,0.12), transparent 28%),
      radial-gradient(circle at top right, rgba(15,118,110,0.10), transparent 26%),
      linear-gradient(180deg,var(--bg-1), var(--bg-2) 44%, #fbfdff 100%);
      color:var(--text);
  }
  .block-container{ max-width:1240px; padding-top:42px; padding-bottom:40px; }

  .section-surface{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-xl); box-shadow:var(--shadow-1); padding:20px; }

  .hero-shell{ background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(15,118,110,0.05)); border-radius:var(--radius-xl); padding:30px; box-shadow:var(--shadow-1); border:1px solid var(--border); }
  .hero-eyebrow{ display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:999px; color:var(--primary-700); background:linear-gradient(90deg,#e7efff, #eefbf8); font-weight:800; font-size:12px; letter-spacing:0.06em; text-transform:uppercase; }
  .hero-title{ font-size: clamp(30px,4.2vw,48px); margin:10px 0 8px; font-weight:900; color:var(--text); letter-spacing:-0.03em; }
  .hero-subtitle{ color:var(--muted); max-width:72ch; margin-bottom:14px; line-height:1.6; }

  .hero-actions{ display:flex; flex-wrap:wrap; gap:10px; }

  .cta{ display:inline-flex; align-items:center; justify-content:center; gap:8px; padding:10px 16px; border-radius:999px; font-weight:800; text-decoration:none; transition:transform .14s ease, box-shadow .14s ease, border-color .14s ease; }
  .cta:hover{ transform:translateY(-1px); }
  .cta.primary{ background: linear-gradient(135deg,var(--primary-500), var(--primary-700)); color:white; box-shadow:0 12px 24px rgba(37,99,235,0.18); }
  .cta.ghost{ background:rgba(255,255,255,0.72); color:var(--primary-700); border:1px solid rgba(37,99,235,0.12); }

  .pill-row{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
  .ui-pill{ background:linear-gradient(180deg,#ffffff,#f8fbff); padding:8px 12px; border-radius:999px; color:var(--muted); font-weight:700; border:1px solid rgba(15,23,42,0.06); box-shadow:0 6px 18px rgba(2,6,23,0.03); }
  .ui-pill.primary{ color:var(--primary-700); background:linear-gradient(90deg, rgba(37,99,235,0.10), rgba(15,118,110,0.06)); }

  .card-grid{ display:grid; grid-template-columns: repeat(3,1fr); gap:18px; align-items:stretch; }
  .modern-card{ background:linear-gradient(180deg,#ffffff, #fbfdff); padding:18px; border-radius:var(--radius-lg); box-shadow:0 10px 24px rgba(2,6,23,0.05); border:1px solid rgba(15,23,42,0.06); transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease; }
  .modern-card:hover{ transform:translateY(-4px); box-shadow:var(--shadow-2); border-color:rgba(37,99,235,0.12); }
  .card-emoji{ font-size:28px; margin-right:10px; }
  .card-head{ display:flex; align-items:center; gap:12px; }
  .card-title{ font-weight:850; font-size:18px; color:var(--text); letter-spacing:-0.01em; }
  .card-body{ color:var(--muted); margin-top:8px; line-height:1.55; }

  .sidebar-brand{ background:var(--sidebar-accent); border:1px solid rgba(37,99,235,0.12); border-radius:20px; padding:16px 16px 14px; margin:4px 0 14px; box-shadow:0 10px 28px rgba(2,6,23,0.05); }
  .sidebar-brand-kicker{ display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:900; letter-spacing:0.10em; text-transform:uppercase; color:var(--primary-700); }
  .sidebar-brand-title{ margin-top:8px; font-size:24px; font-weight:950; color:var(--text); line-height:1; letter-spacing:-0.03em; }
  .sidebar-brand-copy{ margin-top:7px; font-size:13px; color:var(--muted); line-height:1.45; }

  .sidebar-panel{ background:rgba(255,255,255,0.82); border:1px solid rgba(15,23,42,0.06); border-radius:18px; padding:14px; margin:0 0 12px; box-shadow:0 8px 20px rgba(2,6,23,0.03); }
  .sidebar-panel-title{ font-size:12px; font-weight:900; letter-spacing:0.08em; text-transform:uppercase; color:var(--primary-700); }
  .sidebar-panel-copy{ margin-top:6px; color:var(--muted); font-size:12px; line-height:1.45; }

  .compact-meta{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
  .compact-meta span{ display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; background:rgba(255,255,255,0.76); border:1px solid rgba(15,23,42,0.05); color:var(--muted); font-size:12px; font-weight:700; }

  section[data-testid="stSidebar"]{ background:var(--sidebar-surface); border-right:1px solid rgba(15,23,42,0.03); }
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"]{ padding-top:0.25rem; }
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] textarea,
  section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div{
    border-radius:14px !important;
  }
  .sidebar .stButton>button{ border-radius:999px; padding:10px 14px; }
  section[data-testid="stSidebar"] .stButton>button{ box-shadow:0 10px 24px rgba(37,99,235,0.12); }
  section[data-testid="stSidebar"] .stButton>button:hover{ box-shadow:0 14px 28px rgba(37,99,235,0.18); }

  div[data-testid="stMetric"]{ border-radius:12px; padding:12px; border:1px solid var(--border); background:var(--surface); }
  div[data-testid="stMetric"] label{ color:var(--muted) !important; }
  div[data-testid="stMetricValue"]{ color:var(--text) !important; }

  [data-testid="stAlert"]{ border-radius:16px; border:1px solid rgba(15,23,42,0.06); box-shadow:0 10px 24px rgba(2,6,23,0.04); }
  .stDownloadButton button{ border-radius:999px !important; }
  .stDataFrame, .stTable, [data-testid="stExpander"]{ border-radius:16px; }

  .empty-state{ background:linear-gradient(180deg,#ffffff,#f8fbff); border:1px dashed rgba(37,99,235,0.18); border-radius:20px; padding:22px; color:var(--muted); }
  .empty-state strong{ color:var(--text); }

  @media(max-width:900px){ .card-grid{ grid-template-columns: repeat(1,1fr); } .pill-row{ justify-content:flex-start; } }
</style>
""",
        unsafe_allow_html=True,
    )


def _safe_html(text: str) -> str:
    return _html.escape(text) if text is not None else ""


def render_hero(
    eyebrow: str, title: str, subtitle: str, actions: list[str] | None = None
) -> None:
    """Render the hero block.

    `actions` should be a list of HTML strings (e.g. from `cta_button`).
    """

    action_html = ""
    if actions:
        action_html = (
            "<div class='hero-actions' style='margin-top:12px;'>"
            + "".join(actions)
            + "</div>"
        )

    st.markdown(
        f"""
<div class="hero-shell">
  <div class="hero-eyebrow">{_safe_html(eyebrow)}</div>
  <h1 class="hero-title">{_safe_html(title)}</h1>
  <div class="hero-subtitle">{_safe_html(subtitle)}</div>
  {action_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_brand(
    title: str = "RepoMiner", subtitle: str = "Repository intelligence workspace"
) -> None:
    """Render a compact branded sidebar header."""

    st.sidebar.markdown(
        f"""
<div class="sidebar-brand">
  <div class="sidebar-brand-kicker">RepoMiner</div>
  <div class="sidebar-brand-title">{_safe_html(title)}</div>
  <div class="sidebar-brand-copy">{_safe_html(subtitle)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_panel(title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f'<div class="sidebar-panel-copy">{_safe_html(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.sidebar.markdown(
        f"""
<div class="sidebar-panel">
  <div class="sidebar-panel-title">{_safe_html(title)}</div>
  {subtitle_html}
</div>
""",
        unsafe_allow_html=True,
    )


def cta_button(label: str, href: str | None = None, kind: str = "primary") -> str:
    """Return a styled CTA HTML fragment.

    `kind` is 'primary' or 'ghost'. If `href` is None, returns a span.
    """

    cls = "cta primary" if kind == "primary" else "cta ghost"
    text = _safe_html(label)
    if href:
        return f'<a class="{cls}" href="{_html.escape(href)}">{text}</a>'
    return f'<span class="{cls}">{text}</span>'


def section_header(kicker: str, title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f'<div style="color:var(--muted); margin-top:6px;">{_safe_html(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
<div style="margin-top:20px; margin-bottom:12px;">
  <div style="font-weight:800; color:var(--primary-600); font-size:12px; text-transform:uppercase; letter-spacing:0.08em;">{_safe_html(kicker)}</div>
  <h2 style="margin:6px 0 0; font-size:22px;">{_safe_html(title)}</h2>
  {subtitle_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_pill_row(items: list[str]) -> None:
    pills = "".join(f'<div class="ui-pill">{_safe_html(i)}</div>' for i in items)
    st.markdown(f'<div class="pill-row">{pills}</div>', unsafe_allow_html=True)


def render_feature_card(title: str, body: str, emoji: str | None = None) -> None:
    emoji_html = f'<div class="card-emoji">{_safe_html(emoji)}</div>' if emoji else ""
    st.markdown(
        f"""
<div class="modern-card">
  <div class="card-head">{emoji_html}<div>
    <div class="card-title">{_safe_html(title)}</div>
    <div class="card-body">{_safe_html(body)}</div>
  </div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_info_card(title: str, body: str, accent: str | None = None) -> None:
    accent_html = (
        f'<div style="font-size:12px; color:var(--accent-600); font-weight:700">{_safe_html(accent)}</div>'
        if accent
        else ""
    )
    st.markdown(
        f"""
<div class="modern-card">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
    <div>
      <div style="font-weight:800">{_safe_html(title)}</div>
      <div style="color:var(--muted); margin-top:8px">{_safe_html(body)}</div>
    </div>
    {accent_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_dashboard_action(
    title: str, body: str, emoji: str, pill: str | None = None
) -> None:
    pill_html = (
        f'<div class="ui-pill primary" style="display:inline-flex; margin-top:12px;">{_safe_html(pill)}</div>'
        if pill
        else ""
    )
    st.markdown(
        f"""
<div class="modern-card" style="min-height:100%;">
  <div class="card-head">
    <div class="card-emoji">{_safe_html(emoji)}</div>
    <div>
      <div class="card-title">{_safe_html(title)}</div>
      <div class="card-body">{_safe_html(body)}</div>
      {pill_html}
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str, accent: str | None = None) -> None:
    accent_html = (
        f'<div style="margin-bottom:8px; font-size:12px; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; color:var(--primary-700);">{_safe_html(accent)}</div>'
        if accent
        else ""
    )
    st.markdown(
        f"""
<div class="empty-state">
  {accent_html}
  <div style="font-weight:850; color:var(--text); font-size:18px;">{_safe_html(title)}</div>
  <div style="margin-top:8px; line-height:1.55;">{_safe_html(body)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_metric_card(
    label: str, value: str, copy: str | None = None, accent: str | None = None
) -> None:
    copy_html = (
        f'<div style="color:var(--muted); margin-top:8px">{_safe_html(copy)}</div>'
        if copy
        else ""
    )
    accent_html = (
        f'<div style="font-size:12px; color:var(--primary-600); font-weight:700">{_safe_html(accent)}</div>'
        if accent
        else ""
    )
    st.markdown(
        f"""
<div class="modern-card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div style="font-weight:700; color:var(--muted);">{_safe_html(label)}</div>
      <div style="font-size:20px; font-weight:800; margin-top:6px">{_safe_html(value)}</div>
      {copy_html}
    </div>
    {accent_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
