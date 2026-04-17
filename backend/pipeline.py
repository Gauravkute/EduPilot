"""
pipeline.py — Orchestrator
Connects extract → clean → structure → chunk into a single callable.

Usage:
    from pipeline import run_pipeline

    result = run_pipeline(extractor_output, source="report.pdf")

    result["structured"]   # full structured JSON
    result["chunks"]       # list of chunk dicts
    result["stats"]        # token / chunk stats
    result["log"]          # per-stage timing + status
"""

import logging
import time
from typing import Optional

from clean_text     import clean_text
from structure_data import structure_data
from chunk_text     import chunk_text, chunk_stats

# ── Module-level logger ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _stage(name: str):
    """Context manager: logs stage entry/exit and measures wall-clock time."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        log.info("▶ Stage [%s] started", name)
        t0 = time.perf_counter()
        try:
            yield
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            log.error("✗ Stage [%s] FAILED after %.3fs — %s", name, elapsed, exc)
            raise
        elapsed = time.perf_counter() - t0
        log.info("✓ Stage [%s] finished in %.3fs", name, elapsed)

    return _ctx()


def _validate_extractor_output(extractor_output: dict) -> None:
    """Raise ValueError with a clear message if the payload is malformed."""
    if not isinstance(extractor_output, dict):
        raise ValueError(f"extractor_output must be a dict, got {type(extractor_output).__name__}")
    if extractor_output.get("error"):
        raise ValueError(f"Extractor reported an error: {extractor_output['error']}")
    if extractor_output.get("content") is None:
        raise ValueError("extractor_output['content'] is None — nothing to process")
    if "type" not in extractor_output:
        raise ValueError("extractor_output is missing 'type' key")


# ── Public API ────────────────────────────────────────────────────────────────

def run_pipeline(
    extractor_output: dict,
    source:    str = "unknown",
    max_chars: int = 1500,
    overlap:   int = 200,
) -> dict:
    """
    Full document processing pipeline.

    Stage 1 — Validate:   Confirm extractor output is well-formed.
    Stage 2 — Structure:  Convert to unified JSON schema.
                          (clean_text is called internally per block)
    Stage 3 — Chunk:      Split into LLM-optimized retrieval units.

    Args:
        extractor_output: Raw dict from extractor.extract().
        source:           Filename / document identifier.
        max_chars:        Max chars per chunk (default 1500 ≈ 375 tokens).
        overlap:          Overlap chars between chunks (default 200).

    Returns:
        {
            "structured": dict,   # full structured document
            "chunks":     list,   # ready-to-embed chunks
            "stats":      dict,   # summary stats
            "log":        list,   # per-stage timing records
        }

    Raises:
        ValueError:  Malformed / errored extractor payload.
        RuntimeError: Any stage failure (original exception chained).
    """
    pipeline_start = time.perf_counter()
    stage_log: list[dict] = []
    file_type = extractor_output.get("type", "unknown")

    log.info("═══ Pipeline START  source=%s  type=%s ═══", source, file_type)

    # ── Stage 1: Validate ────────────────────────────────────────────────────
    t0 = time.perf_counter()
    log.info("▶ Stage [validate] started")
    try:
        _validate_extractor_output(extractor_output)
    except ValueError as exc:
        log.error("✗ Stage [validate] FAILED — %s", exc)
        raise
    _record(stage_log, "validate", t0, "ok")
    log.info("✓ Stage [validate] finished in %.3fs", time.perf_counter() - t0)

    # ── Stage 2: Structure (+ clean internally) ──────────────────────────────
    t0 = time.perf_counter()
    log.info("▶ Stage [structure] started")
    try:
        structured = structure_data(extractor_output, source=source)
    except Exception as exc:
        _record(stage_log, "structure", t0, f"error: {exc}")
        log.error("✗ Stage [structure] FAILED — %s", exc)
        raise RuntimeError("structure stage failed") from exc
    section_count = len(structured.get("sections", []))
    _record(stage_log, "structure", t0, f"ok — {section_count} sections")
    log.info(
        "✓ Stage [structure] finished in %.3fs  sections=%d",
        time.perf_counter() - t0, section_count,
    )

    # ── Stage 3: Chunk ───────────────────────────────────────────────────────
    t0 = time.perf_counter()
    log.info("▶ Stage [chunk] started  max_chars=%d  overlap=%d", max_chars, overlap)
    try:
        chunks = chunk_text(structured, max_chars=max_chars, overlap=overlap)
        stats  = chunk_stats(chunks)
    except Exception as exc:
        _record(stage_log, "chunk", t0, f"error: {exc}")
        log.error("✗ Stage [chunk] FAILED — %s", exc)
        raise RuntimeError("chunk stage failed") from exc
    _record(stage_log, "chunk", t0, f"ok — {len(chunks)} chunks")
    log.info(
        "✓ Stage [chunk] finished in %.3fs  chunks=%d  tokens_est=%s",
        time.perf_counter() - t0, len(chunks), stats.get("total_tokens_est", "?"),
    )

    total = time.perf_counter() - pipeline_start
    log.info(
        "═══ Pipeline END  %.3fs  chunks=%d  tokens_est=%s ═══",
        total, len(chunks), stats.get("total_tokens_est", "?"),
    )

    return {
        "structured": structured,
        "chunks":     chunks,
        "stats":      stats,
        "log":        stage_log,
    }


def _record(stage_log: list, name: str, t0: float, status: str) -> None:
    stage_log.append({
        "stage":    name,
        "elapsed_s": round(time.perf_counter() - t0, 4),
        "status":   status,
    })


# ── Demo / manual test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    MOCK_DOCX_OUTPUT = {
        "type": "docx",
        "content": {
            "metadata": {
                "author":  "Jane Smith",
                "title":   "Q3 Financial Report",
                "created": "2024-09-01T09:00:00",
            },
            "paragraphs": [
                {"style": "Heading 1", "text": "Executive Summary",        "bold": True,  "italic": False},
                {"style": "Normal",    "text": "This report covers the financial performance for Q3 2024. Revenue grew by 18% year-over-year, driven primarily by the expansion into European markets.", "bold": False, "italic": False},
                {"style": "Normal",    "text": "Operating costs remained stable at $4.2M, reflecting tight expense controls implemented in Q2.", "bold": False, "italic": False},
                {"style": "Heading 2", "text": "Revenue Breakdown",        "bold": True,  "italic": False},
                {"style": "Normal",    "text": "North America contributed $8.1M (62% of total). Europe contributed $3.2M (25%). Asia-Pacific contributed $1.7M (13%).", "bold": False, "italic": False},
                {"style": "Heading 2", "text": "Risks and Outlook",        "bold": True,  "italic": False},
                {"style": "Normal",    "text": "Key risks include foreign exchange volatility and potential supply chain disruptions. The outlook for Q4 remains positive, with projected revenue between $14M and $16M.", "bold": False, "italic": False},
            ],
            "tables": [[
                ["Region",        "Revenue", "% Share"],
                ["North America", "$8.1M",   "62%"],
                ["Europe",        "$3.2M",   "25%"],
                ["Asia-Pacific",  "$1.7M",   "13%"],
            ]],
        },
        "filepath": "report.docx",
        "mime":     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "error":    None,
    }

    result = run_pipeline(MOCK_DOCX_OUTPUT, source="Q3_Financial_Report.docx")

    print("\n" + "=" * 60)
    print("STAGE LOG")
    print("=" * 60)
    print(json.dumps(result["log"], indent=2))

    print("\n" + "=" * 60)
    print("STATS")
    print("=" * 60)
    print(json.dumps(result["stats"], indent=2))

    print("\n" + "=" * 60)
    print("CHUNKS")
    print("=" * 60)
    for chunk in result["chunks"]:
        print(f"\n--- {chunk['chunk_id']} ---")
        print(f"Section : {chunk['section']}")
        print(f"Tokens  : ~{chunk['token_est']}")
        print(f"Text    :\n{chunk['text']}")