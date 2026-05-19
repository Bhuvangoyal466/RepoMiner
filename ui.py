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
    --bg-1: #f6fbff;
    --surface: #ffffff;
    --muted: #6b7280;
    --text: #0f172a;
    --primary-600: #2563eb;
    --primary-500: #3b82f6;
    --accent-600: #0ea5a4;
    --border: rgba(15,23,42,0.06);
    --radius-lg: 16px;
    --radius-xl: 22px;
    --shadow-1: 0 10px 30px rgba(2,6,23,0.06);
  }

  html,body,[class*="css"]{font-family: Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial;}
  .stApp{ background: linear-gradient(180deg,var(--bg-1), #fbfdff 60%); color:var(--text); }
  .block-container{ max-width:1200px; padding-top:28px; padding-bottom:36px; }

  .hero-shell{ background: linear-gradient(90deg, rgba(59,130,246,0.06), rgba(6,182,212,0.03)); border-radius:var(--radius-xl); padding:32px; box-shadow:var(--shadow-1); border:1px solid var(--border); }
  .hero-eyebrow{ display:inline-block; padding:8px 14px; border-radius:999px; color:var(--primary-600); background:linear-gradient(90deg,#e6f0ff, #f0fcff); font-weight:700; font-size:13px; }
  .hero-title{ font-size: clamp(28px,4.2vw,44px); margin:8px 0 6px; font-weight:800; color:var(--text); }
  .hero-subtitle{ color:var(--muted); max-width:70ch; margin-bottom:14px; }

  .cta{ display:inline-block; padding:10px 16px; border-radius:999px; font-weight:700; text-decoration:none; }
  .cta.primary{ background: linear-gradient(90deg,var(--primary-500), var(--primary-600)); color:white; box-shadow:0 8px 20px rgba(59,130,246,0.14); }
  .cta.ghost{ background:transparent; color:var(--primary-600); border:1px solid rgba(59,130,246,0.08); }

  .pill-row{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
  .ui-pill{ background:linear-gradient(180deg,#ffffff,#fbfdff); padding:8px 12px; border-radius:999px; color:var(--muted); font-weight:700; border:1px solid rgba(15,23,42,0.04); }
  .ui-pill.primary{ color:var(--primary-600); background:linear-gradient(90deg, rgba(59,130,246,0.08), rgba(14,165,164,0.04)); }

  .card-grid{ display:grid; grid-template-columns: repeat(3,1fr); gap:20px; align-items:stretch; }
  .modern-card{ background:var(--surface); padding:18px; border-radius:var(--radius-lg); box-shadow:0 8px 24px rgba(2,6,23,0.04); border:1px solid var(--border); transition:transform .14s ease, box-shadow .14s ease; }
  .modern-card:hover{ transform:translateY(-6px); box-shadow:0 18px 42px rgba(2,6,23,0.08); }
  .card-emoji{ font-size:28px; margin-right:10px; }
  .card-head{ display:flex; align-items:center; gap:12px; }
  .card-title{ font-weight:800; font-size:18px; color:var(--text); }
  .card-body{ color:var(--muted); margin-top:8px; }

  section[data-testid="stSidebar"]{ background: linear-gradient(180deg,#ffffff, #fbfcff); border-right:1px solid rgba(15,23,42,0.03); }
  .sidebar .stButton>button{ border-radius:999px; padding:10px 14px; }

  div[data-testid="stMetric"]{ border-radius:12px; padding:12px; border:1px solid var(--border); background:var(--surface); }

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
