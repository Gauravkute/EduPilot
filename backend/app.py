"""
app.py — Streamlit File Extractor + Pipeline
Two tabs:
  1. Extract   — raw extractor output (existing behaviour)
  2. Pipeline  — full clean → structure → chunk with stats + log

Run:
    cd backend
    streamlit run app.py
"""

import sys
import os
import json
import tempfile
import pandas as pd
import streamlit as st
from pathlib import Path
import logging

# ── path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract       # existing extractor package
from pipeline  import run_pipeline  # NEW: end-to-end pipeline


# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocFlow",
    page_icon="⬡",
    layout="wide",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Bricolage+Grotesque:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Bricolage Grotesque', sans-serif !important;
    background-color: #0c0c10 !important;
    color: #d8d8e8 !important;
}
code, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }

#MainMenu, footer, header { visibility: hidden; }
.stApp { background-color: #0c0c10; }

/* header */
.df-header {
    display: flex; align-items: center; gap: 12px;
    padding: 1.6rem 0 1.2rem 0;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 1.6rem;
}
.df-logo {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #5c6bff 0%, #b06bff 100%);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; color: #fff; font-weight: 800;
}
.df-title { font-size: 1.4rem; font-weight: 800; color: #f0f0ff; margin: 0; }
.df-sub   { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem;
            color: #5c5c7a; margin-left: auto; }

/* stat cards */
.stat-row { display: flex; gap: 10px; margin-bottom: 1rem; }
.stat-card {
    flex: 1; background: #13131c; border: 1px solid #1e1e2e;
    border-radius: 10px; padding: 0.9rem 1rem;
}
.stat-label { font-size: 0.65rem; font-family: 'IBM Plex Mono', monospace;
              color: #5c5c7a; text-transform: uppercase; letter-spacing: .06em; }
.stat-value { font-size: 1.5rem; font-weight: 800; color: #f0f0ff; line-height: 1.2; }
.stat-sub   { font-size: 0.7rem; color: #5c5c7a; margin-top: 2px; }

/* stage timeline */
.timeline { margin: .5rem 0 1.2rem 0; }
.tl-item  {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 0; border-bottom: 1px solid #1e1e2e;
    font-family: 'IBM Plex Mono', monospace; font-size: .75rem;
}
.tl-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-ok   { background: #4dffa0; box-shadow: 0 0 6px #4dffa055; }
.dot-err  { background: #ff5c7a; box-shadow: 0 0 6px #ff5c7a55; }
.tl-name  { color: #a0a0c8; width: 90px; }
.tl-ms    { color: #5c5c7a; margin-left: auto; }
.tl-status{ color: #d8d8e8; }

/* chunk card */
.chunk-card {
    background: #13131c; border: 1px solid #1e1e2e;
    border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: .75rem;
}
.chunk-meta { display: flex; gap: 10px; margin-bottom: .6rem; flex-wrap: wrap; }
.tag {
    font-family: 'IBM Plex Mono', monospace; font-size: .65rem;
    padding: 2px 9px; border-radius: 99px; border: 1px solid;
}
.tag-section { color: #7c8fff; border-color: #7c8fff30; background: #7c8fff12; }
.tag-tokens  { color: #4dffa0; border-color: #4dffa030; background: #4dffa012; }
.tag-type    { color: #b06bff; border-color: #b06bff30; background: #b06bff12; }
.chunk-id    { font-family: 'IBM Plex Mono', monospace; font-size: .6rem; color: #3a3a5a; }
.chunk-text  { font-size: .82rem; color: #c8c8e0; white-space: pre-wrap;
               line-height: 1.55; margin-top: .5rem; }

/* error */
.err-box {
    background: rgba(255,92,122,.07); border: 1px solid #ff5c7a;
    border-radius: 8px; padding: 1rem 1.2rem;
    font-family: 'IBM Plex Mono', monospace; font-size: .75rem;
    color: #ff5c7a; white-space: pre-wrap;
}

/* badge row */
.badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 1rem; }
.badge {
    font-family: 'IBM Plex Mono', monospace; font-size: .65rem;
    padding: 3px 10px; border-radius: 5px; border: 1px solid #2a2a3e;
    background: #13131c; color: #8888b0;
}
.badge-hi { background: #7c8fff18; color: #7c8fff; border-color: #7c8fff40; }

/* upload area label */
label, .stMarkdown p { color: #d8d8e8 !important; }
.stTextInput input    { background: #13131c !important; color: #e8e8f0 !important; }

/* tab styling */
.stTabs [role="tab"]           { font-family: 'IBM Plex Mono', monospace !important;
                                  font-size: .8rem !important; color: #5c5c7a !important; }
.stTabs [aria-selected="true"] { color: #f0f0ff !important;
                                  border-bottom: 2px solid #7c8fff !important; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def format_bytes(b: int) -> str:
    if b < 1024:      return f"{b} B"
    if b < 1_048_576: return f"{b/1024:.1f} KB"
    return f"{b/1_048_576:.1f} MB"


def save_upload(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return path


# ── Extract tab renderers (unchanged from original) ───────────────────────────

def render_detection(result: dict):
    cols   = st.columns(4)
    labels = ["type", "mime", "source", "error"]
    for col, label in zip(cols, labels):
        val = result.get(label) or ("none" if label == "error" else "—")
        col.markdown(
            f'<div style="background:#13131c;border:1px solid #1e1e2e;border-radius:10px;'
            f'padding:.8rem 1rem"><div style="font-size:.6rem;font-family:IBM Plex Mono,monospace;'
            f'color:#5c5c7a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem">'
            f'{label}</div><span class="badge badge-hi">{val}</span></div>',
            unsafe_allow_html=True,
        )


def render_pdf(c: dict):
    st.markdown(f'**Pages:** {c.get("page_count", "—")}')
    meta = c.get("metadata", {})
    if meta:
        with st.expander("📄 Metadata"):
            for k, v in meta.items(): st.markdown(f"`{k}` → **{v}**")
    for pg in c.get("pages", []):
        with st.expander(f"Page {pg['page']} · {pg['mode']}  |  {pg['table_count']} tables"):
            st.text_area("Text", value=pg.get("text", "(no text)"),
                         height=130, key=f"pdf_{pg['page']}", disabled=True)
            for i, tbl in enumerate(pg.get("tables", [])):
                st.markdown(f"**Table {i+1}**")
                df = pd.DataFrame(tbl[1:], columns=tbl[0]) if len(tbl) > 1 else pd.DataFrame(tbl)
                st.dataframe(df, use_container_width=True)


def render_docx(c: dict):
    paras  = c.get("paragraphs", [])
    tables = c.get("tables", [])
    c1, c2 = st.columns(2)
    c1.metric("Paragraphs", len(paras))
    c2.metric("Tables", len(tables))
    meta = c.get("metadata", {})
    if meta:
        with st.expander("📄 Metadata"):
            for k, v in meta.items(): st.markdown(f"`{k}` → **{v}**")
    if paras:
        with st.expander(f"📝 Paragraphs ({len(paras)})", expanded=True):
            for p in paras:
                clr = "#7c8fff" if "Heading" in p.get("style", "") else "#5c5c7a"
                st.markdown(
                    f'<div style="border-left:2px solid {clr};padding-left:.75rem;margin-bottom:.5rem">'
                    f'<span style="font-size:.62rem;color:{clr};font-family:IBM Plex Mono,monospace">'
                    f'{p.get("style","")}</span>'
                    f'<div style="color:#d8d8e8;font-size:.84rem">{p.get("text","")}</div></div>',
                    unsafe_allow_html=True,
                )
    for i, tbl in enumerate(tables):
        with st.expander(f"📊 Table {i+1}"):
            df = pd.DataFrame(tbl[1:], columns=tbl[0]) if len(tbl) > 1 else pd.DataFrame(tbl)
            st.dataframe(df, use_container_width=True)


def render_pptx(c: dict):
    st.metric("Slides", c.get("slide_count", 0))
    for slide in c.get("slides", []):
        with st.expander(f"🖼 Slide {slide['slide']}  |  {slide['text_count']} items"):
            for t in slide.get("texts", []): st.markdown(f"- {t}")
            if slide.get("notes"): st.caption(f"📝 {slide['notes']}")


def render_xlsx(c: dict):
    st.metric("Sheets", c.get("sheet_count", 0))
    for name, rows in c.get("sheets", {}).items():
        with st.expander(f"📊 {name}  ({len(rows)} rows)", expanded=True):
            if rows:
                df = pd.DataFrame(rows[1:], columns=rows[0]) if len(rows) > 1 else pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)


def render_html(c: dict):
    c1, c2, c3 = st.columns(3)
    c1.metric("Title", c.get("title") or "—")
    c2.metric("Lines", len(c.get("text_lines", [])))
    c3.metric("Links", len(c.get("links", [])))
    with st.expander("📄 Text", expanded=True):
        st.text_area("", value="\n".join(c.get("text_lines", [])), height=200, disabled=True)
    if c.get("links"):
        with st.expander(f"🔗 Links ({len(c['links'])})"):
            st.dataframe(pd.DataFrame(c["links"]), use_container_width=True)


def render_txt(c: dict):
    c1, c2 = st.columns(2)
    c1.metric("Total Lines", c.get("line_count", 0))
    c2.metric("Non-empty",   c.get("non_empty_lines", 0))
    with st.expander("📄 Content", expanded=True):
        st.text_area("", value="\n".join(c.get("lines", [])), height=300, disabled=True)


def render_image(c: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Format", c.get("format", "—"))
    c2.metric("Mode",   c.get("mode",   "—"))
    c3.metric("Width",  c.get("width",  "—"))
    c4.metric("Height", c.get("height", "—"))
    if c.get("exif"):
        with st.expander("📷 EXIF"):
            for k, v in c["exif"].items(): st.markdown(f"`{k}` → {v}")


def render_content(result: dict):
    if result.get("error"):
        st.markdown(f'<div class="err-box">⚠ {result["error"]}</div>', unsafe_allow_html=True)
        return
    c = result.get("content")
    if not c:
        st.warning("No content returned.")
        return
    dispatch = {"pdf": render_pdf, "docx": render_docx, "pptx": render_pptx,
                "xlsx": render_xlsx, "html": render_html, "txt": render_txt,
                "jpg": render_image, "png": render_image}
    fn = dispatch.get(result.get("type"))
    fn(c) if fn else st.json(c)


# ── Pipeline tab renderer (NEW) ───────────────────────────────────────────────

def render_pipeline(result: dict, pipe_result: dict):
    stats     = pipe_result.get("stats", {})
    chunks    = pipe_result.get("chunks", [])
    stage_log = pipe_result.get("log", [])
    structured = pipe_result.get("structured", {})

    # ── Stats row ────────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="stat-row">'
        f'<div class="stat-card"><div class="stat-label">Chunks</div>'
        f'<div class="stat-value">{stats.get("total_chunks", 0)}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Est. Tokens</div>'
        f'<div class="stat-value">{stats.get("total_tokens_est", 0):,}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Avg Tokens</div>'
        f'<div class="stat-value">{stats.get("avg_tokens", 0)}</div>'
        f'<div class="stat-sub">min {stats.get("min_tokens",0)} · max {stats.get("max_tokens",0)}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Sections</div>'
        f'<div class="stat-value">{len(structured.get("sections", []))}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Stage timeline ────────────────────────────────────────────────────────
    with st.expander("⏱ Stage log", expanded=False):
        items_html = ""
        for entry in stage_log:
            ok  = "error" not in entry.get("status", "")
            dot = "dot-ok" if ok else "dot-err"
            ms  = f"{entry['elapsed_s']*1000:.1f} ms"
            items_html += (
                f'<div class="tl-item">'
                f'<span class="tl-dot {dot}"></span>'
                f'<span class="tl-name">{entry["stage"]}</span>'
                f'<span class="tl-status">{entry["status"]}</span>'
                f'<span class="tl-ms">{ms}</span>'
                f'</div>'
            )
        st.markdown(f'<div class="timeline">{items_html}</div>', unsafe_allow_html=True)

    # ── Structured JSON ───────────────────────────────────────────────────────
    with st.expander("🗂 Structured JSON", expanded=False):
        st.json(structured)

    # ── Chunk viewer ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:.7rem;font-family:IBM Plex Mono,monospace;'
        f'color:#5c5c7a;text-transform:uppercase;letter-spacing:.06em;margin:1rem 0 .5rem 0">'
        f'{len(chunks)} Chunks</div>',
        unsafe_allow_html=True,
    )

    for chunk in chunks:
        section = chunk.get("section") or "—"
        tokens  = chunk.get("token_est", 0)
        ftype   = chunk.get("file_type", "")
        cid     = chunk.get("chunk_id", "")
        text    = chunk.get("text", "")

        st.markdown(
            f'<div class="chunk-card">'
            f'<div class="chunk-meta">'
            f'<span class="tag tag-section">{section}</span>'
            f'<span class="tag tag-tokens">~{tokens} tokens</span>'
            f'<span class="tag tag-type">{ftype}</span>'
            f'</div>'
            f'<div class="chunk-id">{cid}</div>'
            f'<div class="chunk-text">{text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Download chunks ───────────────────────────────────────────────────────
    st.download_button(
        label="⬇ Download chunks JSON",
        data=json.dumps(chunks, indent=2, default=str),
        file_name=f"{result.get('filepath','doc').rsplit('/',1)[-1]}_chunks.json",
        mime="application/json",
    )


# ── Sidebar: file upload ──────────────────────────────────────────────────────

st.markdown(
    '<div class="df-header">'
    '<div class="df-logo">⬡</div>'
    '<h1 class="df-title">DocFlow</h1>'
    '<span class="df-sub">extract · clean · structure · chunk</span>'
    '</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div style="font-size:.7rem;font-family:IBM Plex Mono,monospace;'
        'color:#5c5c7a;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.75rem">'
        'Upload</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Drop file or click to browse",
        type=["pdf", "docx", "pptx", "xlsx", "html", "htm", "txt", "jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )
    if uploaded:
        st.markdown(
            f'<div style="background:#13131c;border:1px solid #1e1e2e;border-radius:10px;'
            f'padding:.8rem 1rem;margin-top:.75rem">'
            f'<div style="font-weight:700;color:#f0f0ff;word-break:break-all;font-size:.85rem">'
            f'{uploaded.name}</div>'
            f'<div style="color:#5c5c7a;font-size:.7rem;margin-top:.25rem">'
            f'{format_bytes(uploaded.size)}</div></div>',
            unsafe_allow_html=True,
        )
        run_btn = st.button("Run Pipeline →", use_container_width=True, type="primary")

        st.divider()
        with st.expander("⚙ Chunk settings"):
            max_chars = st.slider("Max chars / chunk", 500, 3000, 1500, 100)
            overlap   = st.slider("Overlap chars",      0,  500,  200,  50)
    else:
        run_btn   = False
        max_chars = 1500
        overlap   = 200

# ── Main area: tabs ───────────────────────────────────────────────────────────

if not uploaded:
    st.markdown(
        '<div style="text-align:center;color:#3a3a5a;padding:6rem 0">'
        '<div style="font-size:4rem">⬡</div>'
        '<p style="font-family:IBM Plex Mono,monospace;font-size:.8rem">'
        'Upload a file in the sidebar to begin.</p></div>',
        unsafe_allow_html=True,
    )
else:
    tab_extract, tab_pipeline = st.tabs(["🔍  Extractor", "⚡  Pipeline"])

    tmp_path = None
    try:
        tmp_path = save_upload(uploaded)

        # ── Tab 1: raw extractor ──────────────────────────────────────────────
        with tab_extract:
            with st.spinner("Extracting…"):
                ext_result = extract(tmp_path)
            render_detection(ext_result)
            st.divider()
            render_content(ext_result)

        # ── Tab 2: full pipeline ──────────────────────────────────────────────
        with tab_pipeline:
            if not run_btn:
                st.markdown(
                    '<div style="text-align:center;color:#3a3a5a;padding:4rem 0">'
                    '<div style="font-size:3rem">⚡</div>'
                    '<p style="font-family:IBM Plex Mono,monospace;font-size:.8rem">'
                    'Click <strong style="color:#7c8fff">Run Pipeline →</strong> in the sidebar.</p>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                try:
                    with st.spinner("Running pipeline…"):
                        # extractor output is already in ext_result from Tab 1
                        pipe_result = run_pipeline(
                            ext_result,
                            source=uploaded.name,
                            max_chars=max_chars,
                            overlap=overlap,
                        )
                    render_pipeline(ext_result, pipe_result)
                except (ValueError, RuntimeError) as exc:
                    st.markdown(
                        f'<div class="err-box">⚠ Pipeline error\n\n{exc}</div>',
                        unsafe_allow_html=True,
                    )

    except Exception as e:
        import traceback
        st.markdown(
            f'<div class="err-box">⚠ {e}\n\n{traceback.format_exc()}</div>',
            unsafe_allow_html=True,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)