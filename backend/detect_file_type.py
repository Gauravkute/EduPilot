# # backend/extractor/__init__.py

# import importlib
# import sys, os
# sys.path.insert(0, os.path.dirname(__file__) + "/..")
# from detect_file_type import detect_file_type

# # Map type → module name (imported lazily on first use)
# _ROUTER = {
#     'pdf':  'extractor.extract_pdf',
#     'docx': 'extractor.extract_docx',
#     'pptx': 'extractor.extract_pptx',
#     'xlsx': 'extractor.extract_xlsx',
#     'html': 'extractor.extract_html',
#     'txt':  'extractor.extract_txt',
#     'jpg':  'extractor.extract_image',
#     'png':  'extractor.extract_image',
# }

# def extract(filepath: str) -> dict:
#     detection = detect_file_type(filepath)
#     ftype     = detection["type"]
#     base      = {"filepath": filepath, **detection, "error": None}

#     module_name = _ROUTER.get(ftype)
#     if module_name is None:
#         return {**base, "content": None, "error": f"No extractor for type '{ftype}'"}

#     try:
#         module  = importlib.import_module(module_name)  # imported HERE, not at startup
#         content = module.extract(filepath)
#         return {**base, "content": content}
#     except Exception as e:
#         return {**base, "content": None, "error": str(e)}

import magic
from pathlib import Path

# Maps MIME type → short type key used by the router
_MIME_MAP = {
    "application/pdf":                                              "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/html":                                                    "html",
    "text/plain":                                                   "txt",
    "image/jpeg":                                                   "jpg",
    "image/png":                                                    "png",
}

# Fallback: extension → type (when magic returns generic application/octet-stream)
_EXT_MAP = {
    ".pdf": "pdf", ".docx": "docx", ".pptx": "pptx",
    ".xlsx": "xlsx", ".html": "html", ".htm": "html",
    ".txt": "txt", ".jpg": "jpg", ".jpeg": "jpg", ".png": "png",
}


def detect_file_type(filepath: str) -> dict:
    mime = magic.from_file(filepath, mime=True)
    ftype = _MIME_MAP.get(mime)

    # Fallback to extension if MIME is ambiguous
    if ftype is None:
        ext = Path(filepath).suffix.lower()
        ftype = _EXT_MAP.get(ext, "unknown")

    return {"type": ftype, "mime": mime, "source": "magic"}