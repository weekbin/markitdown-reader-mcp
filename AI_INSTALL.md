# AI Installation Guide — markitdown-reader MCP

Run each step in order. Commands assume Linux, Python 3.12+.

---

## Step 1 — Clone or Create the Service Directory

```bash
# If repo exists:
git clone https://github.com/weekbin/markitdown-reader-mcp.git /home/weekbin/.opencode/mcp/markitdown-reader
cd /home/weekbin/.opencode/mcp/markitdown-reader

# Or if already present, skip clone
```

---

## Step 2 — Create Virtual Environment and Install Dependencies

```bash
python3 -m venv /home/weekbin/.opencode/mcp/markitdown-reader/.venv
/home/weekbin/.opencode/mcp/markitdown-reader/.venv/bin/pip install -r /home/weekbin/.opencode/mcp/markitdown-reader/requirements.txt
```

Expected `requirements.txt` content:
```
mcp[fastapi]
PyMuPDF
python-docx
lxml
Pillow
pytesseract
```

If `mcp[fastapi]` fails, install individually:
```bash
pip install mcp fastapi uvicorn PyMuPDF python-docx lxml Pillow pytesseract
```

---

## Step 3 — Install Tesseract OCR

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim

# Verify
tesseract --version | head -3
```

---

## Step 4 — Configure in opencode.json

Add this entry to the `mcp` object in `~/.config/opencode/opencode.json`:

```json
"markitdown-reader": {
  "type": "local",
  "command": [
    "/home/weekbin/.opencode/mcp/markitdown-reader/.venv/bin/python3",
    "/home/weekbin/.opencode/mcp/markitdown-reader/server.py"
  ],
  "enabled": true,
  "environment": {
    "HTTP_PROXY": "http://127.0.0.1:20172",
    "HTTPS_PROXY": "http://127.0.0.1:20172"
  }
}
```

To find your `opencode.json`:
```bash
ls ~/.config/opencode/opencode.json
```

After editing, restart opencode or reload the MCP server.

---

## Step 5 — Verify Installation

```bash
# Test 1: Check virtual environment
/home/weekbin/.opencode/mcp/markitdown-reader/.venv/bin/python3 -c "import mcp, fitz, docx; print('deps OK')"

# Test 2: Check server starts
/home/weekbin/.opencode/mcp/markitdown-reader/.venv/bin/python3 /home/weekbin/.opencode/mcp/markitdown-reader/server.py &
sleep 2
kill %1 2>/dev/null

# Test 3: Check a document (via opencode session)
# In opencode, run:
#   markitdown-reader_get_document_info("/path/to/some.docx")
# Expected output shows page count and slice info
```

---

## Step 6 — Expected File Structure

After setup:
```
/home/weekbin/.opencode/mcp/markitdown-reader/
├── .venv/               # Python virtual environment
├── src/                  # Source modules
│   ├── __init__.py
│   ├── constants.py      # SLICE_PAGES, IMAGE_SIZE_THRESHOLD
│   ├── storage.py       # File I/O, index.json, locks
│   ├── parser.py        # PDF/DOCX extraction, image dedup
│   ├── image.py         # Small image filter, OCR
│   ├── callbacks.py     # HTTP callback POST
│   ├── mcp_tools.py     # MCP tool implementations
│   └── utils.py         # Helpers (mem(), _log)
├── server.py             # Thin FastMCP entry point (~30 lines)
├── AGENTS.md             # Developer architecture guide
├── SKILL.md              # Caller guide
├── comprehensive_test.py  # Test suite
├── requirements.txt
├── README.md
└── AI_INSTALL.md
```

Runtime cache (auto-created):
```
/home/weekbin/.opencode/markitdown/
└── {document_name}/
    ├── slices/          # PDF/DOCX slice files
    ├── images/          # Extracted images (MD5 deduped)
    └── index.json       # Metadata
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `mcp` import fails | Run `pip install mcp[fastapi]` in the venv |
| Tesseract not found | `sudo apt install tesseract-ocr tesseract-ocr-chi-sim` |
| Chinese OCR returns empty | Verify `tesseract-ocr-chi-sim` is installed |
| Server starts but no output | Check log at `~/.opencode/markitdown/server_{PID}.log` |
| Permission denied on venv | `chmod +x /home/weekbin/.opencode/mcp/markitdown-reader/.venv/bin/python3` |
| opencode can't find tool | Ensure `markitdown-reader` entry is inside the `mcp` object, not top-level |
