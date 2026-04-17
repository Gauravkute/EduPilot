import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"
    result = extract(filepath)

    display = {**result}
    if isinstance(display.get("content"), dict):
        pages = display["content"].get("pages", [])
        if pages:
            display["content"]["pages"] = pages[:2]

    print(json.dumps(display, indent=2, default=str))