import fitz
import pdfplumber

MIN_TEXT_LENGTH = 20
TABLE_SNAP_TOL  = 3


def _extract_tables(plumber_page) -> list:
    raw = plumber_page.extract_tables({
        "snap_tolerance":      TABLE_SNAP_TOL,
        "join_tolerance":      3,
        "edge_min_length":     10,
        "min_words_vertical":  1,
        "min_words_horizontal":1,
    })
    return [
        [[cell if cell is not None else "" for cell in row] for row in table]
        for table in raw if table
    ]


def _extract_images(fitz_doc, fitz_page) -> list:
    images, seen = [], set()
    for img_info in fitz_page.get_images(full=True):
        xref = img_info[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            d = fitz_doc.extract_image(xref)
            images.append({"xref": xref, "width": d["width"], "height": d["height"], "format": d["ext"]})
        except Exception:
            continue
    return images


def extract(filepath: str) -> dict:
    """
    Every page:
      1. pdfplumber → tables
      2. fitz       → text  (digital page: fast native extraction)
                    → "(scanned page)" notice if text < MIN_TEXT_LENGTH
                      (no OCR — install pytesseract separately if needed)
      3. fitz       → embedded image metadata
    """
    fitz_doc = fitz.open(filepath)
    pages_output = []

    with pdfplumber.open(filepath) as plumber_doc:
        for i in range(len(fitz_doc)):
            fitz_page    = fitz_doc[i]
            plumber_page = plumber_doc.pages[i]

            tables = _extract_tables(plumber_page)
            text   = fitz_page.get_text("text").strip()
            mode   = "digital" if len(text) >= MIN_TEXT_LENGTH else "scanned"
            if mode == "scanned":
                text = "(scanned/image-only page — no text layer)"

            images = _extract_images(fitz_doc, fitz_page)

            pages_output.append({
                "page":        i + 1,
                "mode":        mode,
                "text":        text,
                "tables":      tables,
                "images":      images,
                "table_count": len(tables),
                "image_count": len(images),
            })

    metadata = {k: v for k, v in fitz_doc.metadata.items() if v}
    fitz_doc.close()

    return {
        "page_count": len(pages_output),
        "metadata":   metadata,
        "pages":      pages_output,
    }