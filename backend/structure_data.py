"""
structure_data.py — Stage 2: Data Structuring
Converts cleaned text / raw extractor output into a normalized,
LLM-friendly JSON structure.

Output schema (always consistent, regardless of file type):
{
  "metadata": { "source", "file_type", "page_count", "author", ... },
  "sections": [
    {
      "index":     int,          # 0-based order in document
      "heading":   str | None,   # detected heading text
      "level":     int | None,   # 1 = H1, 2 = H2, etc.
      "paragraphs": [str, ...]   # clean text blocks in this section
    }
  ],
  "raw_text": str                # flat concatenation (for quick embedding)
}
"""

import re
from typing import Optional
from clean_text import clean_text


# ── Heading detection ─────────────────────────────────────────────────────────

# Matches "1.", "1.2", "1.2.3" prefixed lines — common in docs/reports
_RE_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")

# Short line (< 80 chars) ending without punctuation — likely a heading
_RE_HEADING_HEURISTIC = re.compile(r"^[A-Z][^\n]{0,78}[^.!?,;:]$")

# Known DOCX style names that indicate headings
_DOCX_HEADING_STYLES = {"Heading 1", "Heading 2", "Heading 3",
                         "Heading 4", "Title", "Subtitle"}


def _heading_level(text: str) -> Optional[int]:
    """
    Guess heading level from text alone.
    Returns 1, 2, or 3 — or None if not a heading.
    """
    m = _RE_NUMBERED.match(text.strip())
    if m:
        depth = m.group(1).count(".") + 1
        return min(depth, 3)
    if _RE_HEADING_HEURISTIC.match(text.strip()) and len(text.strip().split()) <= 10:
        return 1
    return None


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text on blank lines; drop empties."""
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


# ── Type-specific structurers ─────────────────────────────────────────────────

def _structure_from_flat_text(text: str, source: str, file_type: str) -> dict:
    """
    Generic structurer for TXT / HTML — no pre-parsed paragraphs.
    Splits on blank lines; detects headings heuristically.
    """
    paras = _split_into_paragraphs(text)
    sections = []
    current: Optional[dict] = None

    for para in paras:
        level = _heading_level(para)
        if level is not None:
            if current:
                sections.append(current)
            current = {"index": len(sections), "heading": para,
                       "level": level, "paragraphs": []}
        else:
            if current is None:
                # Content before first heading → anonymous section 0
                current = {"index": 0, "heading": None, "level": None, "paragraphs": []}
            current["paragraphs"].append(para)

    if current:
        sections.append(current)

    return {
        "metadata":  {"source": source, "file_type": file_type},
        "sections":  sections,
        "raw_text":  text,
    }


def _structure_from_docx(extracted: dict, source: str) -> dict:
    """
    Use DOCX extractor output (paragraphs with style names + tables).
    Heading styles → section boundaries.
    """
    paragraphs = extracted.get("paragraphs", [])
    tables     = extracted.get("tables", [])
    meta_raw   = extracted.get("metadata", {})

    sections: list[dict] = []
    current: Optional[dict] = None

    for p in paragraphs:
        style = p.get("style", "")
        text  = clean_text(p.get("text", ""))
        if not text:
            continue

        is_heading = style in _DOCX_HEADING_STYLES
        level = (int(style.split()[-1]) if "Heading" in style
                 and style.split()[-1].isdigit() else 1) if is_heading else None

        if is_heading:
            if current:
                sections.append(current)
            current = {"index": len(sections), "heading": text,
                       "level": level, "paragraphs": []}
        else:
            if current is None:
                current = {"index": 0, "heading": None, "level": None, "paragraphs": []}
            current["paragraphs"].append(text)

    if current:
        sections.append(current)

    # Append tables as a special "Tables" section
    if tables:
        sections.append({
            "index":      len(sections),
            "heading":    "Tables",
            "level":      None,
            "paragraphs": [str(table) for table in tables],
            "_type":      "table",
        })

    return {
        "metadata": {
            "source":    source,
            "file_type": "docx",
            "author":    meta_raw.get("author"),
            "title":     meta_raw.get("title"),
            "created":   meta_raw.get("created"),
        },
        "sections":  sections,
        "raw_text":  " ".join(
            p["text"] for p in paragraphs if p.get("text")
        ),
    }


def _structure_from_pdf(extracted: dict, source: str) -> dict:
    """
    Use PDF extractor output (pages with text + tables).
    Each page → one section; headings detected heuristically within page text.
    """
    pages    = extracted.get("pages", [])
    meta_raw = extracted.get("metadata", {})
    sections = []
    all_text_parts = []

    for page in pages:
        page_num = page.get("page", 0)
        raw_text = page.get("text", "")
        cleaned  = clean_text(raw_text, file_type="pdf")
        if not cleaned or cleaned.startswith("(scanned"):
            continue

        all_text_parts.append(cleaned)
        paras = _split_into_paragraphs(cleaned)

        # First short paragraph might be a heading
        heading = None
        body    = paras
        if paras and len(paras[0].split()) <= 10 and _heading_level(paras[0]):
            heading = paras[0]
            body    = paras[1:]

        sections.append({
            "index":      len(sections),
            "heading":    heading or f"Page {page_num}",
            "level":      1 if heading else None,
            "paragraphs": body,
            "_page":      page_num,
        })

    return {
        "metadata": {
            "source":     source,
            "file_type":  "pdf",
            "page_count": extracted.get("page_count", len(pages)),
            **{k: v for k, v in meta_raw.items() if v},
        },
        "sections":  sections,
        "raw_text":  "\n\n".join(all_text_parts),
    }


def _structure_from_pptx(extracted: dict, source: str) -> dict:
    """
    PPTX: each slide → one section; slide texts → paragraphs.
    """
    slides   = extracted.get("slides", [])
    sections = []

    for slide in slides:
        idx   = slide.get("slide", len(sections) + 1)
        texts = [clean_text(t) for t in slide.get("texts", []) if t.strip()]
        notes = clean_text(slide.get("notes", ""))

        heading = texts[0] if texts else f"Slide {idx}"
        body    = texts[1:] if len(texts) > 1 else []
        if notes:
            body.append(f"[Notes] {notes}")

        sections.append({
            "index":      len(sections),
            "heading":    heading,
            "level":      1,
            "paragraphs": body,
            "_slide":     idx,
        })

    return {
        "metadata":  {"source": source, "file_type": "pptx",
                      "slide_count": extracted.get("slide_count", len(slides))},
        "sections":  sections,
        "raw_text":  " ".join(
            t for s in slides for t in s.get("texts", [])
        ),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def structure_data(
    extracted: dict,
    source: str = "unknown",
) -> dict:
    """
    Convert extractor output → unified structured JSON.

    Args:
        extracted: dict returned by your extractor package's extract().
                   Must contain 'type' and 'content' keys.
        source:    Original filename or identifier.

    Returns:
        Structured dict with 'metadata', 'sections', 'raw_text'.
    """
    file_type = extracted.get("type", "unknown")
    content   = extracted.get("content") or {}

    if file_type == "docx":
        return _structure_from_docx(content, source)

    if file_type == "pdf":
        return _structure_from_pdf(content, source)

    if file_type == "pptx":
        return _structure_from_pptx(content, source)

    # TXT / HTML / fallback: flatten content to a single string
    if file_type in ("txt", "html"):
        text_lines = content.get("text_lines") or content.get("lines") or []
        flat_text  = clean_text("\n".join(text_lines), file_type=file_type)
        title      = content.get("title", "")
        result     = _structure_from_flat_text(flat_text, source, file_type)
        if title:
            result["metadata"]["title"] = title
        return result

    # Unknown type — best-effort
    flat = clean_text(str(content), file_type=file_type)
    return _structure_from_flat_text(flat, source, file_type)