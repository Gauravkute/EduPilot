import json
from extractor import extract

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"

    result = extract(filepath)

    # Pretty-print the result
    # content can be large; truncate for display
    display = {**result}
    if isinstance(display.get("content"), dict):
        pages = display["content"].get("pages", [])
        if pages:
            display["content"]["pages"] = pages[:2]   # show first 2 pages only

    print(json.dumps(display, indent=2, default=str))