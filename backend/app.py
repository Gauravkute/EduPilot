"""
app_streamlit.py — Streamlit File Extractor
Drop-in replacement for the Flask app.py

Directory structure stays EXACTLY the same:
  backend/
    app_streamlit.py        ← THIS FILE (run with: streamlit run app_streamlit.py)
    detect_file_type.py
    extractor/
      __init__.py
      extract_*.py

Run:
    cd backend
    pip install streamlit
    streamlit run app_streamlit.py
"""

import sys
import os
import json
import tempfile
import pandas as pd
import streamlit as st
from pathlib import Path

# ── path setup (same as app.py) ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract  # your existing extractor package


# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="File Extractor",
    page_icon="🔍",
    layout="wide",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif !important;
}
code, pre, .mono {
    font-family: 'Space Mono', monospace !important;
}

/* Dark background override */
.stApp { background-color: #0a0a0f; }

/* Hide Streamlit default header/footer */
#MainMenu, footer, header { visibility: hidden; }

/* Custom header */
.fx-header {
    padding: 1.5rem 0 1rem 0;
    border-bottom: 1px solid #2a2a3a;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.fx-header h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.5rem;
    color: #e8e8f0;
    margin: 0;
}
.fx-pill {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    background: #7c6dfa;
    color: #fff;
    padding: 2px 10px;
    border-radius: 99px;
}

/* Detection badges */
.badge {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    background: rgba(124,109,250,0.15);
    color: #7c6dfa;
    border: 1px solid #7c6dfa;
    padding: 1px 8px;
    border-radius: 4px;
    margin-right: 6px;
}
.badge-success { background: rgba(109,250,170,0.12); color: #6dfaaa; border-color: #6dfaaa; }
.badge-error   { background: rgba(250,109,109,0.12); color: #fa6d6d; border-color: #fa6d6d; }

/* Section cards */
.fx-card {
    background: #13131a;
    border: 1px solid #2a2a3a;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.fx-card-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #666680;
    margin-bottom: 0.75rem;
}

/* Error box */
.error-box {
    background: rgba(250,109,109,0.08);
    border: 1px solid #fa6d6d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #fa6d6d;
    white-space: pre-wrap;
    word-break: break-word;
}

/* Streamlit widget text color fixes */
label, .stMarkdown p { color: #e8e8f0 !important; }
.stTextInput input, .stSelectbox select { background: #13131a !important; color: #e8e8f0 !important; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def format_bytes(b: int) -> str:
    if b < 1024:        return f"{b} B"
    if b < 1_048_576:   return f"{b/1024:.1f} KB"
    return f"{b/1_048_576:.1f} MB"


def save_upload_to_temp(uploaded_file) -> str:
    """Save a Streamlit UploadedFile to a temp path; returns the path."""
    suffix = Path(uploaded_file.name).suffix or ".bin"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return tmp_path


def render_detection(result: dict):
    """Show file type detection metadata."""
    cols = st.columns(4)
    labels = ["type", "mime", "source", "error"]
    for col, label in zip(cols, labels):
        val = result.get(label) or ("none" if label == "error" else "—")
        badge_cls = "badge-error" if label == "error" and result.get("error") else \
                    "badge-success" if label == "type" else "badge"
        col.markdown(
            f'<div class="fx-card"><div class="fx-card-title">{label}</div>'
            f'<span class="badge {badge_cls}">{val}</span></div>',
            unsafe_allow_html=True
        )


def render_pdf(c: dict):
    st.markdown(f'<div class="fx-card"><div class="fx-card-title">Document Info</div>'
                f'Pages: <b style="color:#e8e8f0">{c.get("page_count","—")}</b></div>',
                unsafe_allow_html=True)

    meta = c.get("metadata", {})
    if meta:
        with st.expander("📄 Document Metadata", expanded=False):
            for k, v in meta.items():
                st.markdown(f"`{k}` → **{v}**")

    pages = c.get("pages", [])
    for pg in pages:
        with st.expander(f"Page {pg['page']} · {pg['mode']}  |  "
                         f"{pg['table_count']} tables · {pg['image_count']} images"):
            st.text_area("Text", value=pg.get("text", "(no text)"),
                         height=150, key=f"pdf_pg_{pg['page']}", disabled=True)

            for i, table in enumerate(pg.get("tables", [])):
                st.markdown(f"**Table {i+1}**")
                if table and len(table) > 1:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    st.dataframe(df, use_container_width=True)
                elif table:
                    st.dataframe(pd.DataFrame(table), use_container_width=True)

            images = pg.get("images", [])
            if images:
                chips = " ".join(
                    f'<span class="badge">{img["format"]} {img["width"]}×{img["height"]}</span>'
                    for img in images
                )
                st.markdown(f"**Embedded images:** {chips}", unsafe_allow_html=True)


def render_docx(c: dict):
    meta = c.get("metadata", {})
    paras = c.get("paragraphs", c.get("paragraph", []))  # handle both key names
    tables = c.get("tables", [])

    col1, col2 = st.columns(2)
    col1.metric("Paragraphs", len(paras))
    col2.metric("Tables", len(tables))

    if meta:
        with st.expander("📄 Document Metadata"):
            for k, v in meta.items():
                st.markdown(f"`{k}` → **{v}**")

    if paras:
        with st.expander(f"📝 Paragraphs ({len(paras)})", expanded=True):
            for p in paras:
                style_color = "#7c6dfa" if "Heading" in p.get("style","") else "#666680"
                st.markdown(
                    f'<div style="border-left:2px solid {style_color};padding-left:.75rem;margin-bottom:.6rem">'
                    f'<span style="font-size:.65rem;color:{style_color};font-family:Space Mono,monospace">'
                    f'{p.get("style","")}</span>'
                    f'<div style="color:#e8e8f0;font-size:.85rem">{p.get("text","")}</div></div>',
                    unsafe_allow_html=True
                )

    for i, table in enumerate(tables):
        with st.expander(f"📊 Table {i+1} ({len(table)} rows)"):
            if table and len(table) > 1:
                df = pd.DataFrame(table[1:], columns=table[0])
                st.dataframe(df, use_container_width=True)
            elif table:
                st.dataframe(pd.DataFrame(table), use_container_width=True)


def render_pptx(c: dict):
    st.metric("Slides", c.get("slide_count", 0))
    for slide in c.get("slides", []):
        with st.expander(f"🖼 Slide {slide['slide']}  |  {slide['text_count']} text items"):
            texts = slide.get("texts", [])
            if texts:
                for t in texts:
                    st.markdown(f"- {t}")
            notes = slide.get("notes", "")
            if notes:
                st.caption(f"📝 Notes: {notes}")


def render_xlsx(c: dict):
    st.metric("Sheets", c.get("sheet_count", 0))
    for sheet_name, rows in c.get("sheets", {}).items():
        with st.expander(f"📊 {sheet_name}  ({len(rows)} rows)", expanded=True):
            if rows and len(rows) > 1:
                df = pd.DataFrame(rows[1:], columns=rows[0])
                st.dataframe(df, use_container_width=True)
            elif rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.caption("Empty sheet")


def render_html(c: dict):
    col1, col2, col3 = st.columns(3)
    col1.metric("Title", c.get("title") or "—")
    col2.metric("Lines", len(c.get("text_lines", [])))
    col3.metric("Links", len(c.get("links", [])))

    lines = c.get("text_lines", [])
    if lines:
        with st.expander("📄 Text Content", expanded=True):
            st.text_area("", value="\n".join(lines), height=200, disabled=True)

    links = c.get("links", [])
    if links:
        with st.expander(f"🔗 Links ({len(links)})"):
            df = pd.DataFrame(links)
            st.dataframe(df, use_container_width=True)


def render_txt(c: dict):
    col1, col2 = st.columns(2)
    col1.metric("Total Lines", c.get("line_count", 0))
    col2.metric("Non-empty Lines", c.get("non_empty_lines", 0))
    lines = c.get("lines", [])
    if lines:
        with st.expander("📄 Content", expanded=True):
            st.text_area("", value="\n".join(lines), height=300, disabled=True)


def render_image(c: dict):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Format", c.get("format", "—"))
    col2.metric("Mode", c.get("mode", "—"))
    col3.metric("Width", c.get("width", "—"))
    col4.metric("Height", c.get("height", "—"))
    exif = c.get("exif", {})
    if exif:
        with st.expander("📷 EXIF Data"):
            for k, v in exif.items():
                st.markdown(f"`{k}` → {v}")


def render_content(result: dict):
    ftype = result.get("type")
    c = result.get("content")

    if result.get("error"):
        tb = result.get("traceback", "")
        st.markdown(
            f'<div class="error-box">⚠ {result["error"]}'
            f'{"<br><br>Traceback:<br>" + tb if tb else ""}</div>',
            unsafe_allow_html=True
        )
        return

    if not c:
        st.warning("No content returned.")
        return

    dispatch = {
        "pdf":  render_pdf,
        "docx": render_docx,
        "pptx": render_pptx,
        "xlsx": render_xlsx,
        "html": render_html,
        "txt":  render_txt,
        "jpg":  render_image,
        "png":  render_image,
    }

    renderer = dispatch.get(ftype)
    if renderer:
        renderer(c)
    else:
        st.json(c)  # fallback: raw JSON


# ── main UI ───────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="fx-header"><h1>File Extractor</h1><span class="fx-pill">streamlit</span></div>',
    unsafe_allow_html=True
)

left, right = st.columns([1, 2], gap="large")

with left:
    uploaded = st.file_uploader(
        "Drop a file or click to browse",
        type=["pdf", "docx", "pptx", "xlsx", "html", "htm", "txt", "jpg", "jpeg", "png"],
        label_visibility="visible"
    )

    if uploaded:
        st.markdown(
            f'<div class="fx-card">'
            f'<div class="fx-card-title">Selected File</div>'
            f'<div style="font-weight:700;color:#e8e8f0;word-break:break-all">{uploaded.name}</div>'
            f'<div style="color:#666680;font-size:.78rem;margin-top:.3rem">'
            f'{format_bytes(uploaded.size)}</div>'
            f'<span class="badge" style="margin-top:.5rem;display:inline-block">'
            f'{uploaded.type or "unknown mime"}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        extract_clicked = st.button("Extract →", use_container_width=True, type="primary")
    else:
        extract_clicked = False

with right:
    if not uploaded:
        st.markdown(
            '<div style="text-align:center;color:#666680;padding:4rem 0">'
            '<div style="font-size:4rem">🔍</div>'
            '<p>Upload a file to extract its content.</p></div>',
            unsafe_allow_html=True
        )
    elif not extract_clicked:
        st.markdown(
            '<div style="text-align:center;color:#666680;padding:4rem 0">'
            '<div style="font-size:4rem">📂</div>'
            '<p>Click <strong>Extract →</strong> to inspect.</p></div>',
            unsafe_allow_html=True
        )
    else:
        tmp_path = None
        try:
            with st.spinner("Detecting file type and extracting content…"):
                tmp_path = save_upload_to_temp(uploaded)
                result = extract(tmp_path)

            # Detection metadata row
            render_detection(result)
            st.divider()

            # Content
            render_content(result)

        except Exception as e:
            import traceback
            st.markdown(
                f'<div class="error-box">⚠ {e}<br><br>{traceback.format_exc()}</div>',
                unsafe_allow_html=True
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)