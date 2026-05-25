# AGENTS.md — markitdown-reader

## OVERVIEW

Python MCP service exposing document tools via FastMCP. Targets PDF, DOCX, and image OCR workflows. Refactored from single file into `src/` module structure.

## STRUCTURE

```
markitdown-reader/
  src/
    __init__.py          # Package init
    constants.py         # SLICE_PAGES, IMAGE_SIZE_THRESHOLD, BASE_DIR
    storage.py           # File I/O, index.json, locks
    parser.py            # PDF/DOCX extraction, image dedup
    image.py             # Small image filter, OCR
    callbacks.py         # HTTP callback POST
    mcp_tools.py         # MCP tool implementations (~1405 lines)
    utils.py             # Helpers (mem(), _log)
  server.py              # Thin FastMCP entry point (~30 lines)
  AGENTS.md
  requirements.txt
  comprehensive_test.py
```

## WHERE TO LOOK

- **Main entry**: `read_document` (`src/mcp_tools.py` line ~56)
- **Paired reading**: `_read_paired_documents` (`src/mcp_tools.py` line ~1156)
- **Single reading**: `_read_single_document` (`src/mcp_tools.py` line ~1034)
- **Slice resolution**: `_read_slices_direct` (`src/mcp_tools.py` line ~895)
- **Image extraction**: `extract_images` (`src/mcp_tools.py` line ~277)
- **Paired file detection**: `_find_paired_file` (`src/mcp_tools.py` line ~875)
- **File locks**: `_with_write_lock` / `_with_read_lock` (`src/storage.py` lines ~41, ~66)
- **Callbacks**: `_post_callback` (`src/callbacks.py` line ~15)

## CODE MAP

### MCP Tools

| Tool | Line | Signature |
|------|------|-----------|
| `read_document` | ~56 | `(file_path, fast?, slice_ids?, force_refresh?, callback_url?)` |
| `read_document_pair` | ~206 | `(pdf_path, docx_path, force_refresh?, callback_url?)` |
| `extract_images` | ~277 | `(file_path, page_range?)` |
| `slice_document` | ~358 | `(file_path, pages_per_slice=5)` |
| `get_document_info` | ~427 | `(file_path)` |
| `ocr_image` | ~338 | `(image_path)` |
| `list_supported_files` | ~493 | `()` |
| `list_cache_dir` | ~513 | `(doc_name=None)` |
| `get_cached_content` | ~819 | `(doc_name, run="latest")` |
| `get_processing_status` | ~648 | `(doc_name?, file_path?)` |
| `retry_failed_images` | ~715 | `(doc_name)` |
| `update_document_markdown` | ~560 | `(img_id, ocr_result, position_info?)` |
| `update_batch_document_markdown` | ~594 | `(updates)` |
| `resume_document` | ~755 | `(file_path)` |

### Large Functions (>90 lines)

| Function | Line | Purpose |
|---------|------|---------|
| `read_document` | ~56 | Auto-detect pairing, slice, return Markdown |
| `_read_slices_direct` | ~895 | Slice ID to path mapping |
| `_read_single_document` | ~1034 | Core document processing |
| `_read_paired_documents` | ~1156 | Paired PDF+DOCX flow |

### Key Constants

| Constant | Value | Source |
|----------|-------|--------|
| `SLICE_PAGES` | `5` | `src/constants.py` |
| `SLICE_BLOCKS` | `200` | `src/constants.py` |
| `IMAGE_SIZE_THRESHOLD` | `50*1024` | `src/constants.py` |
| `BASE_DIR` | `~/.opencode/markitdown/` | `src/constants.py` |

## CONVENTIONS

- Private functions: `_` prefix
- Constants: `UPPER_SNAKE_CASE`
- Logging: `_log.debug()` for progress, `_log.exception()` for errors
- Memory tracking: `mem()` helper (`src/utils.py`)
- Type hints on all public functions
- Progress format: `[STATUS]\n{JSON}\n[/STATUS]\n{Markdown}`
- All responses include `next_steps` field for guidance

## CALLER GUIDE

### How to Call These Tools

**Protocol**: All calls are **synchronous** — do NOT provide a `callback_url`.
The service returns complete responses directly.

**Typical call pattern**:
1. Call `read_document` or `read_document_pair`
2. Receive: `{text, images, slices, next_steps, ...}`
3. Done — no callback needed

**next_steps field**:
- Every response includes `next_steps: [...]` with actionable next actions
- Always check `next_steps` before making follow-up calls

### force_refresh Parameter

| Value | Effect |
|-------|--------|
| `False` (default) | Reuse cached slices/images, resume from checkpoint |
| `True` | Clear all cache and reprocess from scratch |

### Image Deduplication (image_hashes)

The service tracks image content MD5 hashes in `index.json["image_hashes"]`.
Same content appearing on different pages = only one file saved.
This works across slices automatically when using the standard call flow.
MD5 is computed from original bytes (before resize).

### Small Image Filter

Images that are **<1KB or <32x32 pixels** are:
- Excluded from the `images` list in responses
- Still saved to disk for audit purposes
- OCR'd automatically for content completeness
- Marked with `is_small: true` in index.json

### Multi-Process Anti-Pattern Warning

**DO NOT do this**:
```python
slices = slice_document(path)
for s in slices:
    read_document(path, slice_ids=[s])  # Parallel calls — ❌
```
Each parallel call writes to the same `index.json`. Last write wins.
Each process gets empty `seen_hashes` — no dedup.
If one uses `force_refresh=True`, all dedup breaks.

**CORRECT**:
```python
read_document_pair(pdf, docx)  # One call, internal slicing — ✅
```

### Error Recovery

- `get_processing_status(doc_name)` — check pending/failed images
- `retry_failed_images(doc_name)` — retry failed OCR
- `resume_document(file_path)` — continue from checkpoint

### Limits

| Limit | Value |
|-------|-------|
| PDF slice | 5 pages |
| DOCX slice | 200 blocks |
| Image dedup | MD5-based, cross-slice via `image_hashes` |
| Small image filter | <1KB or <32×32 (filtered from results, saved+OCR'd) |
| OCR threshold | <50KB (auto-tesseract) |
| Memory watchdog | 800MB |
| Timeout per slice | 300s |

## NEW FEATURES

### File Locks (T16, T17)
- `_with_write_lock(doc_name, operation)` — Exclusive lock (LOCK_EX) with 10s timeout, uses LOCK_NB
- `_with_read_lock(doc_name, operation)` — Shared lock (LOCK_SH) with 10s timeout, uses LOCK_NB
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
- `list_cache_dir(doc_name=None)` — List all cached documents or specific one
- `get_cached_content(doc_name, run="latest")` — Retrieve cached content from current or historical run

### Cross-Slice Image Deduplication (T23)
- Image hashes tracked in `index.json["image_hashes"]`
- Same content on different pages = one file saved
- Works automatically when using standard call flow

## ANTI-PATTERNS

1. **Deprecated constant**: `MAX_CHARS_RETURN` no longer used — do not reference
2. **Slice paths**: `_find_paired_file` skips `/slices/` paths — do not process them
3. **Parallel slice reads**: Do not call `read_document` with `slice_ids` in parallel — causes index.json race conditions and dedup failure
4. **force_refresh race**: Multiple processes with `force_refresh=True` will overwrite each other's cache

## UNIQUE STYLES

- **Paired detection**: Auto-find same-stem PDF+DOCX without explicit pairing
- **Image pool**: Images in `~/.opencode/markitdown/{doc}/images/`. Content-based dedup via `index.json["image_hashes"]` — same content on different pages = one file. MD5 computed from original bytes (before resize).
- **Small image filter**: <1KB or <32×32 pixels — excluded from `images` list but saved to disk and OCR'd for audit. Appears as `is_small: true` in index.
- **Process isolation**: Each MCP call = separate PID, logs to `logs/markitdown.log`
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
    ├── images/              # Pooled images (content-based dedup)
    │   └── {doc}_p1_i0_abc123.png
    ├── source/              # Backed up original files
    │   └── document.pdf
    ├── history/             # Historical runs
    │   └── run_001/
    │       ├── slices/
    │       ├── images/
    │       └── output.md
    ├── index.json           # Metadata (slices, images, image_hashes, runs)
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
- Image deduplication uses `image_hashes` in `index.json` for cross-slice dedup
- MD5 computed from original bytes (before resize)
- OCR loop and progress building duplicated in `_read_slices_direct`, `_read_single_document`, `_read_paired_documents`
- File locks use `LOCK_NB` (non-blocking) with 10s timeout to prevent deadlocks
