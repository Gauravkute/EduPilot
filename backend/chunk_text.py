"""
chunk_text.py — Stage 3: Semantic-aware Chunking
Splits structured document data into LLM-optimized chunks.

Design goals:
  1. Never break mid-sentence.
  2. Prefer breaking at paragraph boundaries.
  3. Each chunk carries enough context (section heading + source) for retrieval.
  4. Configurable size. Token-aware (approximated at 4 chars ≈ 1 token).
  5. Overlapping window to avoid context loss at chunk boundaries.

Output per chunk:
{
  "chunk_id":    str,   # "<source>__<section_idx>__<chunk_idx>"
  "source":      str,
  "file_type":   str,
  "section":     str | None,   # heading of the parent section
  "level":       int | None,
  "text":        str,
  "char_count":  int,
  "token_est":   int,          # estimated tokens (chars / 4)
  "page":        int | None,   # PDF only
  "slide":       int | None,   # PPTX only
}
"""

import re
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

CHARS_PER_TOKEN   = 4       # rough approximation; use tiktoken for precision
DEFAULT_MAX_CHARS = 1500    # ≈ 375 tokens — safe for most 8k-context LLMs
DEFAULT_OVERLAP   = 200     # chars of overlap between consecutive chunks


# ── Sentence splitter (no NLTK dependency) ────────────────────────────────────

# Split on ". ", "! ", "? " — but not on "Dr. Smith", "e.g. " etc.
_RE_SENTENCE = re.compile(
    r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s"
)


def _split_sentences(text: str) -> list[str]:
    """
    Lightweight sentence splitter. Splits on sentence-ending punctuation
    followed by whitespace, while ignoring common abbreviations.
    """
    parts = _RE_SENTENCE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


# ── Core chunker ──────────────────────────────────────────────────────────────

def _build_chunks_from_paragraphs(
    paragraphs: list[str],
    max_chars:  int,
    overlap:    int,
) -> list[str]:
    """
    Greedy paragraph-first, then sentence-level chunking.

    Algorithm:
      1. Try to fill a chunk with whole paragraphs.
      2. If a single paragraph exceeds max_chars, split it by sentences.
      3. Apply overlap: carry the last `overlap` chars of the previous
         chunk into the start of the next one.
    """
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""
    overlap_tail = ""   # carries forward the end of the last chunk

    def _flush(buf: str):
        nonlocal overlap_tail
        text = buf.strip()
        if text:
            # Prepend overlap from previous chunk (skip on first chunk)
            full = (overlap_tail + " " + text).strip() if overlap_tail else text
            chunks.append(full)
            # Store the tail of THIS chunk for next overlap
            overlap_tail = text[-overlap:] if len(text) > overlap else text

    for para in paragraphs:
        # Case 1: paragraph alone exceeds limit → sentence-level split
        if len(para) > max_chars:
            if buffer:
                _flush(buffer)
                buffer = ""
            sentences = _split_sentences(para)
            sent_buf  = ""
            for sent in sentences:
                if len(sent_buf) + len(sent) + 1 > max_chars:
                    _flush(sent_buf)
                    sent_buf = sent
                else:
                    sent_buf = (sent_buf + " " + sent).strip()
            if sent_buf:
                _flush(sent_buf)
        # Case 2: adding paragraph would overflow buffer → flush first
        elif len(buffer) + len(para) + 2 > max_chars:
            _flush(buffer)
            buffer = para
        # Case 3: accumulate
        else:
            buffer = (buffer + "\n\n" + para).strip() if buffer else para

    if buffer:
        _flush(buffer)

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_text(
    structured: dict,
    max_chars:  int = DEFAULT_MAX_CHARS,
    overlap:    int = DEFAULT_OVERLAP,
) -> list[dict]:
    """
    Chunk a structured document (output of structure_data()) into
    retrieval-ready pieces.

    Args:
        structured: Output of structure_data().
        max_chars:  Maximum characters per chunk (default 1500 ≈ 375 tokens).
        overlap:    Character overlap between consecutive chunks (default 200).

    Returns:
        List of chunk dicts ready for embedding / vector store insertion.
    """
    meta      = structured.get("metadata", {})
    sections  = structured.get("sections", [])
    source    = meta.get("source", "unknown")
    file_type = meta.get("file_type", "unknown")

    all_chunks: list[dict] = []

    for section in sections:
        sec_idx   = section.get("index", 0)
        heading   = section.get("heading")
        level     = section.get("level")
        paragraphs = section.get("paragraphs", [])
        page      = section.get("_page")
        slide     = section.get("_slide")

        raw_chunks = _build_chunks_from_paragraphs(paragraphs, max_chars, overlap)

        for chunk_idx, text in enumerate(raw_chunks):
            if not text.strip():
                continue

            # Prepend section heading as context prefix (cheap but powerful)
            # This helps the LLM understand the chunk's context without
            # needing to look up metadata.
            context_prefix = f"[{heading}]\n" if heading else ""
            full_text = context_prefix + text

            all_chunks.append({
                "chunk_id":   f"{source}__{sec_idx}__{chunk_idx}",
                "source":     source,
                "file_type":  file_type,
                "section":    heading,
                "level":      level,
                "text":       full_text,
                "char_count": len(full_text),
                "token_est":  len(full_text) // CHARS_PER_TOKEN,
                "page":       page,
                "slide":      slide,
            })

    return all_chunks


def chunk_stats(chunks: list[dict]) -> dict:
    """
    Quick summary stats for a chunk list — useful for debugging
    token budgets before sending to an LLM.
    """
    if not chunks:
        return {}
    sizes = [c["token_est"] for c in chunks]
    return {
        "total_chunks":    len(chunks),
        "total_tokens_est": sum(sizes),
        "avg_tokens":      round(sum(sizes) / len(sizes), 1),
        "min_tokens":      min(sizes),
        "max_tokens":      max(sizes),
    }