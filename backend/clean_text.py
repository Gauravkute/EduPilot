"""
clean_text.py — Stage 1: Text Cleaning
Removes noise, normalizes whitespace, strips headers/footers/page numbers.
Designed to be file-type-aware but safe as a generic fallback.
"""

import re
from typing import Optional


# ── Regex patterns compiled once at module load (performance) ─────────────────

# Page numbers: standalone digits, or "Page 3 of 10", "- 3 -", etc.
_RE_PAGE_NUM = re.compile(
    r"(?:^|\n)\s*(?:[-–]\s*)?\d+\s*(?:[-–]\s*)?(?:of\s+\d+)?\s*(?=\n|$)",
    re.MULTILINE,
)

# Common running headers/footers — repeated short lines (detected dynamically)
_RE_REPEATED_SHORT = re.compile(r"^.{1,60}$", re.MULTILINE)

# Excessive whitespace
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")
_RE_TRAILING_WS   = re.compile(r"[ \t]+$", re.MULTILINE)

# Unicode normalization targets
_REPLACEMENTS = [
    ("\u2019", "'"),   # right single quotation
    ("\u2018", "'"),   # left single quotation
    ("\u201c", '"'),   # left double quotation
    ("\u201d", '"'),   # right double quotation
    ("\u2013", "-"),   # en-dash
    ("\u2014", "--"),  # em-dash
    ("\u00a0", " "),   # non-breaking space
    ("\u2022", "-"),   # bullet
    ("\u00b7", "-"),   # middle dot
    ("\uf0b7", "-"),   # private use bullet (common in Word exports)
]


def _normalize_unicode(text: str) -> str:
    """Replace curly quotes, dashes, bullets with ASCII equivalents."""
    for bad, good in _REPLACEMENTS:
        text = text.replace(bad, good)
    return text


def _remove_page_numbers(text: str) -> str:
    """Strip standalone page-number lines."""
    return _RE_PAGE_NUM.sub("\n", text)


def _remove_repeated_headers(text: str, threshold: int = 3) -> str:
    """
    Detect lines that appear 3+ times in the document — likely running headers
    or footers — and remove all occurrences.

    threshold: minimum repetition count to qualify as a header/footer.
    """
    lines = text.splitlines()
    from collections import Counter
    counts = Counter(l.strip() for l in lines if l.strip())
    noise  = {line for line, cnt in counts.items() if cnt >= threshold and len(line) < 80}
    if not noise:
        return text
    cleaned = [l for l in lines if l.strip() not in noise]
    return "\n".join(cleaned)


def _collapse_whitespace(text: str) -> str:
    """Strip trailing whitespace per line, collapse 3+ blank lines to 2."""
    text = _RE_TRAILING_WS.sub("", text)
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def clean_text(
    text: str,
    file_type: Optional[str] = None,
    remove_page_numbers: bool = True,
    remove_repeated_headers: bool = True,
    header_threshold: int = 3,
) -> str:
    """
    Main entry point for text cleaning.

    Args:
        text:                    Raw extracted text.
        file_type:               'pdf' | 'docx' | 'pptx' | 'txt' | 'html' | None
                                 Used to apply type-specific heuristics.
        remove_page_numbers:     Strip standalone page-number lines.
        remove_repeated_headers: Strip running headers/footers.
        header_threshold:        How many repeats = header/footer.

    Returns:
        Cleaned string.
    """
    if not text:
        return ""

    text = _normalize_unicode(text)

    if remove_page_numbers:
        text = _remove_page_numbers(text)

    # PDF-specific: aggressive header/footer removal (they repeat every page)
    if remove_repeated_headers or file_type == "pdf":
        text = _remove_repeated_headers(text, threshold=header_threshold)

    text = _collapse_whitespace(text)
    return text