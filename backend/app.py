"""
app.py — Flask upload server
Structure:
  backend/
    app.py              ← YOU ARE HERE
    detect_file_type.py
    extractor/
      __init__.py
      extract_*.py
"""

import os, tempfile, sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

# app.py is inside backend/, so THIS directory already has detect_file_type.py
# and the extractor/ package — just add the current dir to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File Extractor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#0a0a0f; --surface:#13131a; --border:#2a2a3a;
    --accent:#7c6dfa; --accent2:#fa6d9a; --text:#e8e8f0;
    --muted:#666680; --success:#6dfaaa; --error:#fa6d6d;
    --mono:'Space Mono',monospace; --sans:'Syne',sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;display:grid;grid-template-rows:auto 1fr}
  header{padding:2rem 3rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:1rem}
  header h1{font-size:1.4rem;font-weight:800;letter-spacing:-0.02em}
  header .pill{font-family:var(--mono);font-size:.65rem;background:var(--accent);color:#fff;padding:2px 8px;border-radius:99px}
  main{display:grid;grid-template-columns:340px 1fr;height:calc(100vh - 73px)}
  .panel-left{border-right:1px solid var(--border);padding:2rem;display:flex;flex-direction:column;gap:1.5rem;overflow-y:auto}
  .dropzone{border:2px dashed var(--border);border-radius:12px;padding:2.5rem 1.5rem;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;position:relative}
  .dropzone:hover,.dropzone.drag{border-color:var(--accent);background:rgba(124,109,250,.05)}
  .dropzone input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%}
  .dropzone .icon{font-size:2.5rem;margin-bottom:.75rem}
  .dropzone p{font-size:.85rem;color:var(--muted)}
  .dropzone strong{color:var(--accent)}
  .file-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;display:none;flex-direction:column;gap:.4rem}
  .file-card.show{display:flex}
  .file-card .name{font-weight:700;font-size:.9rem;word-break:break-all}
  .file-card .badge{font-family:var(--mono);font-size:.65rem;background:rgba(124,109,250,.15);color:var(--accent);border:1px solid var(--accent);padding:1px 7px;border-radius:4px;width:fit-content}
  .file-card .size{font-size:.75rem;color:var(--muted)}
  button#extractBtn{width:100%;padding:.85rem;background:var(--accent);color:#fff;border:none;border-radius:8px;font-family:var(--sans);font-size:.9rem;font-weight:700;cursor:pointer;transition:opacity .2s,transform .1s;display:none}
  button#extractBtn.show{display:block}
  button#extractBtn:hover{opacity:.85}
  button#extractBtn:active{transform:scale(.98)}
  button#extractBtn:disabled{opacity:.4;cursor:not-allowed}
  .meta-block{display:none;flex-direction:column;gap:.5rem}
  .meta-block.show{display:flex}
  .meta-block h3{font-size:.7rem;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
  .meta-row{display:flex;justify-content:space-between;font-size:.78rem;padding:.35rem 0;border-bottom:1px solid var(--border)}
  .meta-row .key{color:var(--muted);font-family:var(--mono)}
  .meta-row .val{color:var(--text);font-weight:700;text-align:right;max-width:55%;word-break:break-all}
  .panel-right{padding:2rem 2.5rem;overflow-y:auto;display:flex;flex-direction:column;gap:1.5rem}
  .placeholder{margin:auto;text-align:center;color:var(--muted);font-size:.9rem}
  .placeholder .big{font-size:4rem;margin-bottom:1rem}
  .section{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}
  .section-header{padding:.85rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
  .section-header h2{font-size:.8rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
  .section-header .count{font-family:var(--mono);font-size:.65rem;background:var(--border);padding:2px 8px;border-radius:99px;color:var(--muted)}
  .section-body{padding:1.25rem}
  pre.content-text{font-family:var(--mono);font-size:.72rem;line-height:1.7;color:#b0b0cc;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow-y:auto}
  .data-table{width:100%;border-collapse:collapse;font-size:.75rem}
  .data-table th{background:rgba(124,109,250,.1);color:var(--accent);font-family:var(--mono);padding:.4rem .75rem;text-align:left;font-size:.65rem;letter-spacing:.05em}
  .data-table td{padding:.4rem .75rem;border-bottom:1px solid var(--border);color:var(--text);vertical-align:top}
  .data-table tr:last-child td{border-bottom:none}
  .error-box{background:rgba(250,109,109,.08);border:1px solid var(--error);border-radius:8px;padding:1rem 1.25rem;font-family:var(--mono);font-size:.78rem;color:var(--error);white-space:pre-wrap;word-break:break-word}
  .spinner{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;display:none;margin:auto}
  .spinner.show{display:block}
  @keyframes spin{to{transform:rotate(360deg)}}
  .img-grid{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.75rem}
  .img-chip{font-family:var(--mono);font-size:.65rem;background:rgba(250,109,154,.1);border:1px solid var(--accent2);color:var(--accent2);padding:2px 8px;border-radius:4px}
</style>
</head>
<body>
<header>
  <h1>File Extractor</h1>
  <span class="pill">v1.0</span>
</header>
<main>
  <aside class="panel-left">
    <div class="dropzone" id="dropzone">
      <input type="file" id="fileInput" accept=".pdf,.docx,.pptx,.xlsx,.html,.htm,.txt,.jpg,.jpeg,.png">
      <div class="icon">📂</div>
      <p>Drop file here or <strong>browse</strong></p>
      <p style="margin-top:.4rem;font-size:.75rem">PDF · DOCX · PPTX · XLSX · HTML · TXT · JPG · PNG</p>
    </div>
    <div class="file-card" id="fileCard">
      <span class="name" id="fileName"></span>
      <span class="badge" id="fileType"></span>
      <span class="size" id="fileSize"></span>
    </div>
    <button id="extractBtn">Extract →</button>
    <div class="spinner" id="spinner"></div>
    <div class="meta-block" id="metaBlock">
      <h3>Detection</h3>
      <div id="metaRows"></div>
    </div>
  </aside>
  <section class="panel-right" id="rightPanel">
    <div class="placeholder"><div class="big">🔍</div><p>Upload a file to extract its content.</p></div>
  </section>
</main>
<script>
const dropzone   = document.getElementById('dropzone');
const fileInput  = document.getElementById('fileInput');
const fileCard   = document.getElementById('fileCard');
const extractBtn = document.getElementById('extractBtn');
const spinner    = document.getElementById('spinner');
const metaBlock  = document.getElementById('metaBlock');
const metaRows   = document.getElementById('metaRows');
const rightPanel = document.getElementById('rightPanel');
let selectedFile = null;

dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', e => {
  e.preventDefault(); dropzone.classList.remove('drag');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(file) {
  selectedFile = file;
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileType').textContent  = file.type || 'unknown mime';
  document.getElementById('fileSize').textContent  = formatBytes(file.size);
  fileCard.classList.add('show');
  extractBtn.classList.add('show');
  metaBlock.classList.remove('show');
  rightPanel.innerHTML = '<div class="placeholder"><div class="big">🔍</div><p>Click <strong>Extract</strong> to inspect.</p></div>';
}

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(1) + ' MB';
}

extractBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  extractBtn.disabled = true;
  spinner.classList.add('show');
  rightPanel.innerHTML = '';

  const fd = new FormData();
  fd.append('file', selectedFile);

  try {
    const res  = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();
    renderMeta(data);
    renderContent(data);
  } catch(err) {
    rightPanel.innerHTML = `<div class="error-box">Request failed: ${err.message}</div>`;
  } finally {
    extractBtn.disabled = false;
    spinner.classList.remove('show');
  }
});

function renderMeta(data) {
  const rows = [
    ['type',   data.type   || '—'],
    ['mime',   data.mime   || '—'],
    ['source', data.source || '—'],
    ['error',  data.error  || 'none'],
  ];
  metaRows.innerHTML = rows.map(([k,v]) =>
    `<div class="meta-row"><span class="key">${k}</span><span class="val">${esc(String(v))}</span></div>`
  ).join('');
  metaBlock.classList.add('show');
}

function renderContent(data) {
  rightPanel.innerHTML = '';

  if (data.error) {
    // Show error + traceback if present for easier debugging
    const tb = data.traceback ? `\n\nTraceback:\n${data.traceback}` : '';
    rightPanel.innerHTML = `<div class="error-box">⚠ ${esc(data.error)}${esc(tb)}</div>`;
    return;
  }

  const c = data.content;
  if (!c) { rightPanel.innerHTML = '<div class="error-box">No content returned.</div>'; return; }

  const type = data.type;

  if (type === 'pdf') {
    addMeta(c.metadata, 'Document Metadata');
    addKeyVal({ 'Page count': c.page_count });
    c.pages?.forEach(pg => {
      addSection(
        `Page ${pg.page} · ${pg.mode}`,
        `${pg.table_count} tables · ${pg.image_count} images`,
        `<pre class="content-text">${esc(pg.text || '(no text)')}</pre>` +
        (pg.tables?.length ? pg.tables.map(t => tableHTML(t)).join('') : '') +
        (pg.images?.length ? `<div class="img-grid">${pg.images.map(i=>`<div class="img-chip">${i.format} ${i.width}×${i.height}</div>`).join('')}</div>` : '')
      );
    });
    return;
  }

  if (type === 'docx') {
    addMeta(c.metadata, 'Document Metadata');
    addKeyVal({ Paragraphs: c.paragraph?.length || 0, Tables: c.tables?.length || 0 });
    if (c.paragraph?.length) {
      addSection('Paragraphs', c.paragraph.length,
        c.paragraph.map(p =>
          `<div style="border-left:2px solid var(--border);padding-left:.75rem;margin-bottom:.5rem">
            <span style="font-size:.65rem;color:var(--muted)">${esc(p.style)}</span>
            <div style="font-size:.8rem">${esc(p.text)}</div>
           </div>`
        ).join('')
      );
    }
    c.tables?.forEach((t,i) => addSection(`Table ${i+1}`, t.length+' rows', tableHTML(t)));
    return;
  }

  if (type === 'pptx') {
    addKeyVal({ 'Slide count': c.slide_count });
    c.slides?.forEach(s =>
      addSection(`Slide ${s.slide}`, s.text_count+' text items',
        `<pre class="content-text">${esc((s.texts||[]).join('\n'))}</pre>` +
        (s.notes ? `<div style="margin-top:.75rem;font-size:.75rem;color:var(--muted)">Notes: ${esc(s.notes)}</div>` : '')
      )
    );
    return;
  }

  if (type === 'xlsx') {
    addKeyVal({ Sheets: c.sheet_count });
    Object.entries(c.sheets || {}).forEach(([name, rows]) =>
      addSection(`Sheet: ${name}`, rows.length+' rows', tableHTML(rows))
    );
    return;
  }

  if (type === 'html') {
    addKeyVal({ Title: c.title || '—', Lines: c.text_lines?.length, Links: c.links?.length });
    if (c.text_lines?.length) addSection('Text Content', c.text_lines.length+' lines',
      `<pre class="content-text">${esc(c.text_lines.join('\n'))}</pre>`);
    if (c.links?.length) addSection('Links', c.links.length,
      tableHTML([['Text','Href'], ...c.links.map(l=>[l.text,l.href])]));
    return;
  }

  if (type === 'txt') {
    addKeyVal({ Lines: c.line_count, 'Non-empty': c.non_empty_lines });
    addSection('Content', c.line_count+' lines',
      `<pre class="content-text">${esc(c.lines?.join('\n'))}</pre>`);
    return;
  }

  if (type === 'jpg' || type === 'png') {
    addKeyVal({ Format: c.format, Mode: c.mode, Width: c.width, Height: c.height });
    if (c.exif && Object.keys(c.exif).length) addMeta(c.exif, 'EXIF Data');
    return;
  }

  addSection('Raw Output', '', `<pre class="content-text">${esc(JSON.stringify(c, null, 2))}</pre>`);
}

function addSection(title, badge, bodyHTML) {
  const el = document.createElement('div');
  el.className = 'section';
  el.innerHTML = `
    <div class="section-header">
      <h2>${esc(String(title))}</h2>
      ${badge !== '' ? `<span class="count">${esc(String(badge))}</span>` : ''}
    </div>
    <div class="section-body">${bodyHTML}</div>`;
  rightPanel.appendChild(el);
}

function addKeyVal(obj) {
  const rows = Object.entries(obj).map(([k,v]) =>
    `<div class="meta-row"><span class="key">${k}</span><span class="val">${esc(String(v))}</span></div>`
  ).join('');
  addSection('Summary', '', rows);
}

function addMeta(obj, title='Metadata') {
  if (!obj || !Object.keys(obj).length) return;
  const rows = Object.entries(obj).map(([k,v]) =>
    `<div class="meta-row"><span class="key">${k}</span><span class="val">${esc(String(v))}</span></div>`
  ).join('');
  addSection(title, Object.keys(obj).length+' fields', rows);
}

function tableHTML(rows) {
  if (!rows?.length) return '<p style="color:var(--muted);font-size:.8rem">Empty table</p>';
  const [head, ...body] = rows;
  return `<div style="overflow-x:auto"><table class="data-table">
    <thead><tr>${head.map(h=>`<th>${esc(String(h))}</th>`).join('')}</tr></thead>
    <tbody>${body.map(r=>`<tr>${r.map(c=>`<td>${esc(String(c))}</td>`).join('')}</tr>`).join('')}</tbody>
  </table></div>`;
}

function esc(s='') {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file received"}), 400

    suffix = Path(f.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = extract(tmp_path)
        return jsonify(_serialise(result))
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _serialise(obj):
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialise(i) for i in obj]
    if isinstance(obj, bytes):
        return f"<bytes len={len(obj)}>"
    try:
        import json; json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


if __name__ == "__main__":
    app.run(debug=True, port=5000)