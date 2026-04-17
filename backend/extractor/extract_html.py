from bs4 import BeautifulSoup
from pathlib import Path

def extract(filepath: str)->dict:
    html = Path(filepath).read_text(encoding='utf-8', errors='replace')
    soup = BeautifulSoup(html, 'html.parser')   # built-in parser, no extra install

    # Remove script / style noise
    for tag in soup(['script', 'style', 'head']):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""
    text  = soup.get_text(separator='\n')

    # Collapse blank lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    links = [
        {"text": a.get_text(strip=True), "href": a.get('href', '')}
        for a in soup.find_all('a')
        if a.get('href')
    ]

    return {"title": title, "text_lines": lines, "links": links}
