# from detect_file_type import detect_file_type
# from extractor.extract_pdf    import extract as _pdf
# from extractor.extract_docx   import extract as _docx
# from extractor.extract_pptx   import extract as _pptx
# from extractor.extract_xlsx   import extract as _xlsx
# from extractor.extract_html   import extract as _html
# from extractor.extract_txt    import extract as _txt
# from extractor.extract_image  import extract as _image

# _ROUTER = {
#     'pdf': _pdf,
#     'docx':_docx,
#     'pptx':_pptx,
#     'xlsx':_xlsx,
#     'html':_html,
#     'txt':_txt,
#     'jpg':_image,
#     'png':_image
# }

# def extract(filepath : str) -> dict:ī
#     detection = detect_file_type(filepath)
#     ftype = detection["type"]
#     extractor = _ROUTER.get(ftype)

#     base = {"filepath":filepath,**detection,"error":None}

#     if extractor is None:
#         return {**base,"content":None,
#                 "error":f"No extractor for type '{ftype}'"}
    
#     try:
#         content = extractor(filepath)
#         return{**base,"content":content}
#     except Exception as e:
#         return {**base,"content":None,"error":str(e)}

# import importlib, sys, os
# sys.path.insert(0, os.path.dirname(__file__))
# from detect_file_type import detect_file_type

# # Lazy router — modules imported only when needed
# _ROUTER = {
#     "pdf":  "extractor.extract_pdf",
#     "docx": "extractor.extract_docx",
#     "pptx": "extractor.extract_pptx",
#     "xlsx": "extractor.extract_xlsx",
#     "html": "extractor.extract_html",
#     "txt":  "extractor.extract_txt",
#     "jpg":  "extractor.extract_image",
#     "png":  "extractor.extract_image",
# }


# def extract(filepath: str) -> dict:
#     detection = detect_file_type(filepath)
#     ftype = detection["type"]
#     base = {"filepath": filepath, **detection, "error": None}

#     module_name = _ROUTER.get(ftype)
#     if module_name is None:
#         return {**base, "content": None, "error": f"No extractor for type '{ftype}'"}

#     try:
#         module = importlib.import_module(module_name)
#         content = module.extract(filepath)
#         return {**base, "content": content}
#     except Exception as e:
#         return {**base, "content": None, "error": str(e)}

import importlib
from detect_file_type import detect_file_type   # caller sets sys.path

_ROUTER = {
    "pdf":  "extractor.extract_pdf",
    "docx": "extractor.extract_docx",
    "pptx": "extractor.extract_pptx",
    "xlsx": "extractor.extract_xlsx",
    "html": "extractor.extract_html",
    "txt":  "extractor.extract_txt",
    "jpg":  "extractor.extract_image",
    "png":  "extractor.extract_image",
}

def extract(filepath: str) -> dict:
    detection = detect_file_type(filepath)
    ftype = detection["type"]
    base = {"filepath": filepath, **detection, "error": None}

    module_name = _ROUTER.get(ftype)
    if module_name is None:
        return {**base, "content": None, "error": f"No extractor for type '{ftype}'"}

    try:
        module = importlib.import_module(module_name)
        content = module.extract(filepath)
        return {**base, "content": content}
    except Exception as e:
        return {**base, "content": None, "error": str(e)}