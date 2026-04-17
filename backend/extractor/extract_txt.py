from pathlib import Path

def extract(filepath:str)-> dict:
    try:
        text = Path(filepath).read_text(encoding='utf-8')
    except UnicodeDecodeError:
        text = Path(filepath).read_text(encoding='latin-1')
    
    lines = text.splitlines()
    non_empty = [l for l in lines if l.strip()]

    return{
        "line_count": len(lines),
        "non_empty_lines": len(non_empty),
        "lines": lines

    }