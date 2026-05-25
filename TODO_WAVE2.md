# Wave 2 Implementation Findings

## T5: force_refresh
- Added `force_refresh: bool = False` parameter to `read_document` (line ~958)
- `read_document_pair` already had `force_refresh` parameter (line ~998)
- When `force_refresh=True`: calls `_move_current_to_history(doc_name)` first to clear old cache

## T6: _is_small_image
- Added `_is_small_image(img_path: str) -> bool` function:
  - File size < 1024 bytes → return True
  - PIL dimensions < 32x32 → return True
  - Else return False
- Added `is_small` field to image dicts in:
  - `_read_single_document` (line ~804)
  - `_read_paired_documents` (line ~895)
  - `_read_slices_direct` (line ~711)

## T7: MD output with image anchoring
- Created `_build_unified_md_output(text, images, doc_name, doc_path)` function (line ~940)
- Changed output file from `content.md` to `output.md` in all 3 locations:
  - `_read_slices_direct`
  - `_read_single_document`
  - `_read_paired_documents`
- MD format with image anchors:
  ```markdown
  ![](path/to/img.png){.positioned page=1 y=245}
  Image: OCR result or "see nearby content"
  ```

## T8: _get_image_position_info for PDF
- Added `_get_image_position_info(pdf_path: str, page_num: int, bbox: tuple) -> dict` (line ~319)
- Uses PyMuPDF `page.get_text("dict")` to find blocks
- Returns: {page, y, nearest_text_above, nearest_text_below}

## T9: _get_docx_image_anchor for DOCX
- Added `_get_docx_image_anchor(docx_path: str, image_rId: str) -> dict` (line ~547)
- Iterates paragraphs to find inline shapes with matching rId
- Returns: {paragraph_index, anchor_text}
