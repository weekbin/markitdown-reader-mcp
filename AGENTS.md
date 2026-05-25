# AGENTS.md — markitdown-reader

## OVERVIEW

Single-file Python MCP service exposing document tools via FastMCP. Targets PDF, DOCX, and image OCR workflows. No tests, no package structure, flat architecture.

## STRUCTURE

```
markitdown-reader/
  server.py          # ~2120 lines, everything lives here
  AGENTS.md          # This file
  requirements.txt
```

## WHERE TO LOOK

- **Main entry**: `read_document` (line ~1221)
- **Paired reading**: `_read_paired_documents` (line ~1021)
- **Single reading**: `_read_single_document` (line ~904)
- **Slice resolution**: `_read_slices_direct` (line ~760)
- **Image extraction**: `extract_images` (line ~1438)
- **Paired file detection**: `_find_paired_file` (line ~254)
- **File locks**: `_with_write_lock` / `_with_read_lock` (lines ~76, ~114)
- **Callbacks**: `_post_callback` (line ~132)

## CODE MAP

### MCP Tools

| Tool | Lines | Signature |
|------|-------|-----------|
| `read_document` | ~40 | `(file_path, fast?, slice_ids?, force_refresh?, callback_url?)` |
| `read_document_pair` | ~70 | `(pdf_path, docx_path, force_refresh?, callback_url?)` |
| `extract_images` | ~50 | `(file_path, page_range?)` |
| `slice_document` | ~60 | `(file_path, pages_per_slice=5)` |
| `get_document_info` | ~80 | `(file_path)` |
| `ocr_image` | ~25 | `(image_path)` |
| `list_supported_files` | ~20 | `()` |
| `list_cache_dir` | ~45 | `(doc_name=None)` |
| `get_cached_content` | ~55 | `(doc_name, run="latest")` |
| `get_processing_status` | ~50 | `(doc_name?, file_path?)` |
| `retry_failed_images` | ~40 | `(doc_name)` |
| `update_document_markdown` | ~30 | `(img_id, ocr_result, position_info?)` |
| `update_batch_document_markdown` | ~60 | `(updates)` |
| `resume_document` | ~60 | `(file_path)` |

### Large Functions (>90 lines)

| Function | Lines | Purpose |
|---------|-------|---------|
| `read_document` | ~40 | Auto-detect pairing, slice, return Markdown |
| `_read_slices_direct` | ~120 | Slice ID to path mapping |
| `_read_single_document` | ~110 | Core document processing |
| `_read_paired_documents` | ~100 | Paired PDF+DOCX flow |

### Key Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `SLICE_PAGES` | `5` | PDF pages per slice |
| `SLICE_BLOCKS` | `200` | DOCX blocks per slice |
| `IMAGE_SIZE_THRESHOLD` | `50*1024` | Auto-OCR trigger (<50KB) |
| `BASE_DIR` | `~/.opencode/markitdown/` | Persistent storage root |

## CONVENTIONS

- Private functions: `_` prefix
- Constants: `UPPER_SNAKE_CASE`
- Logging: `_log.debug()` for progress, `_log.exception()` for errors
- Memory tracking: `mem()` helper
- No type hints, no config files
- Progress format: `[STATUS]\n{JSON}\n[/STATUS]\n{Markdown}`
- All responses include `next_steps` field for guidance

## NEW FEATURES

### File Locks (T16, T17)
- `_with_write_lock(doc_name, operation)` - Exclusive lock (LOCK_EX) with 10s timeout, uses LOCK_NB
- `_with_read_lock(doc_name, operation)` - Shared lock (LOCK_SH) with 10s timeout, uses LOCK_NB
- `get_processing_status` uses read lock for safe concurrent queries

### Non-blocking Slice Processing (T18)
- `_slice_pdf` and `_slice_docx` save progress after each slice
- Time budget checks prevent infinite loops (default 300s per slice phase)
- Partial progress preserved if time budget exceeded

### Callback URL (T19)
- `read_document` and `read_document_pair` accept `callback_url` parameter
- Events: `read_started`, `read_completed` posted via HTTP POST
- Failures logged but never block main processing

### Next Steps (T20)
- Every tool response includes `next_steps` with actionable guidance
- JSON responses have `next_steps` array
- Text responses include "下一步建议:" section

### Cache Management (T21, T22)
- `list_cache_dir(doc_name=None)` - List all cached documents or specific one
- `get_cached_content(doc_name, run="latest")` - Retrieve cached content from current or historical run

## ANTI-PATTERNS

1. **Deprecated constant**: `MAX_CHARS_RETURN` no longer used — do not reference
2. **Slice paths**: `_find_paired_file` skips `/slices/` paths — do not process them
3. **Modularity**: Single file — do not expect modular design

## UNIQUE STYLES

- **Paired detection**: Auto-find same-stem PDF+DOCX without explicit pairing
- **Image pool**: MD5-deduplicated images persist to `~/.opencode/markitdown/{doc}/images/`
- **Small image OCR**: Images <50KB auto-OCR'd via tesseract
- **Process isolation**: Each MCP call = separate PID, logs to `server_{pid}.log`
- **Mixed response**: Status block + Markdown in single response
- **Callback events**: POST notifications on document start/complete

## COMMANDS

```bash
# Run the server
python server.py

# Dependencies
pip install mcp PyMuPDF python-docx Pillow pytesseract
```

## DIRECTORY STRUCTURE

```
~/.opencode/markitdown/
└── {doc_name}/
    ├── slices/              # PDF and DOCX slice files
    │   ├── slice_000.pdf
    │   ├── slice_001.pdf
    │   └── slice_000.docx
    ├── images/              # Pooled images (MD5 deduplicated)
    │   └── {doc}_p1_i0_abc123.png
    ├── source/              # Backed up original files
    │   └── document.pdf
    ├── history/             # Historical runs
    │   └── run_001/
    │       ├── slices/
    │       ├── images/
    │       └── output.md
    ├── index.json           # Metadata (slices, images, runs)
    └── output.md            # Current unified output
```

## TESTING PROCESS

### Running Tests

```bash
# Run comprehensive test suite
python comprehensive_test.py

# Run from .venv if needed
.venv/bin/python3 comprehensive_test.py
```

### Test Coverage

All 14 MCP tools are tested in `comprehensive_test.py`:

| Phase | Tools |
|-------|-------|
| Phase 1: Stateless | `list_supported_files`, `list_cache_dir`, `get_processing_status` |
| Phase 2: Cache Population | `read_document`, `read_document_pair`, `slice_document`, `get_document_info`, `extract_images` |
| Phase 3: State-dependent | `get_processing_status`, `list_cache_dir`, `get_cached_content`, `retry_failed_images`, `resume_document` |
| Phase 4: OCR | `ocr_image` |
| Phase 5: Update | `update_document_markdown`, `update_batch_document_markdown` |

### Watchdog Protection

- Memory limit: 800MB
- CPU limit: 150%
- Timeout: 300s per phase

### Test Reports

Reports are saved to `docs/test-reports/` with format `comprehensive-YYYY-MM-DD.md`.

### Adding New Tools to Tests

When adding a new MCP tool:
1. Add the tool call to the appropriate phase in `comprehensive_test.py`
2. Ensure the tool is tested with both success and error cases
3. Update this section if the tool requires special handling

## NOTES

- `slice_ids` in `read_document` must map to actual slice directories
- Image deduplication uses `seen_paths` set across three functions
- OCR loop and progress building duplicated in `_read_slices_direct`, `_read_single_document`, `_read_paired_documents`
- File locks use `LOCK_NB` (non-blocking) with 10s timeout to prevent deadlocks
