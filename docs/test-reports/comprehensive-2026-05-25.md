# Comprehensive Test Report - 2026-05-25

## Test Summary

| Metric | Value |
|--------|-------|
| Date | 2026-05-25 |
| Total Tests | 17 |
| Passed | 17 |
| Failed | 0 |
| Skipped | 0 |
| Peak Memory | 167MB |
| Total Time | 4.6s |

## Test Coverage

All 14 MCP tools tested:

| Phase | Tool | Status | Time |
|-------|------|--------|------|
| Phase 1: Stateless | list_supported_files | ✓ PASS | 0.0s |
| Phase 1: Stateless | list_cache_dir (no args) | ✓ PASS | 0.0s |
| Phase 1: Stateless | get_processing_status (no args) | ✓ PASS | 0.0s |
| Phase 2: Cache | read_document (PDF, force_refresh) | ✓ PASS | 1.8s |
| Phase 2: Cache | read_document_pair (force_refresh) | ✓ PASS | 1.7s |
| Phase 2: Cache | slice_document | ✓ PASS | 0.0s |
| Phase 2: Cache | get_document_info | ✓ PASS | 0.0s |
| Phase 2: Cache | extract_images | ✓ PASS | 0.6s |
| Phase 3: State | get_processing_status (with doc_name) | ✓ PASS | 0.0s |
| Phase 3: State | list_cache_dir (with doc_name) | ✓ PASS | 0.0s |
| Phase 3: State | get_cached_content | ✓ PASS | 0.0s |
| Phase 3: State | retry_failed_images | ✓ PASS | 0.0s |
| Phase 3: State | resume_document | ✓ PASS | 0.0s |
| Phase 4: OCR | ocr_image | ✓ PASS | 0.1s |
| Phase 5: Update | update_document_markdown | ✓ PASS | 0.0s |
| Phase 5: Update | update_batch_document_markdown | ✓ PASS | 0.0s |
| Phase 6: Cleanup | resume_document (force_refresh cleanup) | ✓ PASS | 0.0s |

## Watchdog Protection

- Memory limit: 800MB
- CPU limit: 150%
- Timeout: 300s

## Test Documents

- PDF: `/home/weekbin/Documents/docs/GBT+34657.2-2017.pdf`
- DOCX: `/home/weekbin/Documents/docs/GBT+34657.2-2017.docx`

## Notes

- Test ran successfully with paired PDF+DOCX workflow
- 32 images extracted from PDF
- 29 unique images after deduplication
- All state-dependent tools verified with populated cache
