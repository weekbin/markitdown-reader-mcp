# markitdown-reader MCP Service — Agent Guide

## 核心原则

**最优策略：同时提供 PDF + DOCX 配对文件，一次性获得完整结果。**

单文件模式的已知缺陷：
- 只提供 PDF → 文字乱码（CID-font 问题），图片正常
- 只提供 DOCX → 文字正常，可能无法提取图片

## 工具接口（5个）

### 1. read_document(path, fast=False, slice_ids=None, force_refresh=False, callback_url="")
**首选工具**。传入任意路径，自动检测配对文件并读取。

**参数**：
- `path`：文件路径（PDF 或 DOCX）
- `fast=False`（默认）：文字 + 图片全量，较慢
- `fast=True`：只读文字，跳过图片提取，**秒回**
- `slice_ids=None`（默认）：读全部分片。若指定，则从预先分片文件中只读指定分片。**需要先调用 slice_document()**
- `force_refresh=False`（默认）：复用缓存/断点续读。`True`=清空所有缓存和历史，重新从头处理
- `callback_url=""`（默认）：可选的 HTTP POST 回调地址。仅在你有 HTTP 服务监听时才设置。

**返回 `[STATUS]` 块，agent 可直接解析**：

```json
{
  "doc": "文件名.pdf",
  "paired": false,
  "need_pairing": true,
  "fast": false,
  "images_extracted": true,
  "slice_count": 7,
  "slices": ["p1-5", "p6-10", ...],
  "image_count": 12,
  "ocr_count": 2,
  "content_written": true,
  "content_path": "/path/to/content.md",
  "chars": 450000,
  "mode": "pdf_single",
  "next_steps": [...]
}
```

**mode 取值**：`paired` / `pdf_single` / `docx_single`

**调度规则（按顺序检查 STATUS）**：
1. `need_pairing: true` → **立即询问用户**能否提供另一格式（也可查看 `next_steps` 获取配对建议）
2. `fast: true` → 图片未提取，需要单独用 `extract_images()` 补
3. `content_written: true` → 读取 `content_path` 获取完整内容
4. `images_extracted: false` → 调用 `extract_images()` 提取图片
5. **始终检查 `next_steps` 字段**，它提供下一步行动建议

### 2. slice_document(path, pages_per_slice=5)
**独立分片工具**。只分片，不读取内容，返回结构化信息。

```json
{
  "doc_name": "GBT27930",
  "total_pages": 187,
  "slice_count": 38,
  "slices": [
    {"slice_id": "p1-5", "page_range": "1-5", "page_count": 5, "slice_index": 0},
    ...
  ],
  "paired_file": "/path/to/file.docx"
}
```

### 3. read_document_pair(pdf_path, docx_path, force_refresh=False, callback_url="")
**显式配对读取**。用户已确认有配对文件时使用。

```python
read_document_pair("/path/a.pdf", "/path/a.docx")
```
→ DOCX 提取文字表格，PDF 提取图片

注意：`fast` 不是 `read_document_pair` 的参数，图片提取由服务内部控制。

### 配对模式 vs 单文件模式

**配对模式（推荐）**：
- PDF → 图片（含位置信息）
- DOCX → 文字 + 表格
- 同一内容在不同页出现 → 只存一份（image_hashes 去重）

**单文件模式（不推荐）**：
- 只有 PDF → 文字可能乱码（CID-font 问题）
- 只有 DOCX → 无法提取图片

### 4. extract_images(path, page_range="")
**单独提取图片**。返回路径列表，小图(<50KB)已内置 OCR。

### 5. get_document_info(path)
查看元信息：页数、段落数、表格数、预估分片数、配对建议。

## 调度流程

### 完整读取大文档

**Step 1**：快速探查
```
read_document(path, fast=True)   ← 先用 fast 模式，秒回
  → 看 STATUS need_pairing / fast / content_written / next_steps
```

**Step 2a**：`need_pairing: true` → 询问用户能否提供另一格式

**Step 2b**：有配对或用户确认 → `read_document_pair(pdf, docx)`

**Step 2c**：无配对且无法提供 → 单文件模式继续干活，可选 `fast=True` 先拿文字

**Step 3**：提取图片
```
extract_images(path)
  → 大图(≥50KB): file:// 路径 → minimax-token-plan_understand_image
  → 小图(<50KB): 已内置 OCR，结果在返回中
```

## 超时处理

**如果工具调用超时**（MCP error -32001）：
→ 说明文档很大，改用 `fast=True` 先拿文字，图片单独提取

## ⚠️ 多进程分片调用 — 反模式警告

**切勿这样做**：
```
slices = slice_document(path)
for s in slices:
    read_document(path, slice_ids=[s])  # ❌ 并行调用
```

**问题**：
1. 每个并行调用读写同一个 index.json → last write wins，早期结果丢失
2. 各进程的 seen_hashes 独立 → image_hashes 跨页去重完全失效
3. 若任意进程 force_refresh=True → 清空 image_hashes → 其他全部失效

**正确做法**：
```
read_document_pair(pdf_path, docx_path)  # ✅ 一次调用，内部自动分片
```

**理由**：
- 共享 index.json 和 image_hashes，跨 slice 去重有效
- 原子性缓存更新，无并发冲突
- 服务内部已有并行处理

若文档很大导致超时 → 使用 `fast=True` 先拿文字，图片单独提取。

## force_refresh=True

`force_refresh=True` will:
- Delete all cached slices, images, and index for this document
- Re-extract all images directly from the original PDF (by page range, not slice files)
- Run Tesseract on small images (<50KB)
- Rebuild output.md

Use `delete_cache(doc_name)` for a guaranteed clean slate before `read_document_pair(force_refresh=True)`.

## 出错恢复

| 工具 | 用途 |
|------|------|
| `get_processing_status(doc_name)` | 查看 pending/failed 图片数 |
| `retry_failed_images(doc_name)` | 重试失败图片的 OCR |
| `resume_document(file_path)` | 从上次断点继续处理 |
| `delete_cache(doc_name)` | 删除文档所有缓存，重新开始 |

## next_steps 字段

Every response includes `next_steps: [...]`. **必须检查此字段**，它提供下一步行动建议。

## Caller Premium OCR Guide

### Overview
Tesseract provides emergency OCR only for small images (<50KB). For quality-critical content
(diagrams, complex tables, Chinese documents), use a premium OCR service (e.g., minimax token plan MCP).

### Step 2 — Query Image Status

Use `get_processing_status(doc_name)` to get structured guidance:

```python
status = get_processing_status(doc_name)
# Returns:
# {
#   "needs_premium_ocr": [...],      # Tesseract failed or skipped — MUST call premium OCR
#   "premium_completed": [...],       # Already OCR'd with premium — do NOT re-OCR
#   "informational_only": [...],      # Small icon/logo — does not affect understanding
#   "has_tesseract_result": [...],    # Tesseract succeeded — decide based on quality
#   "progress": 33.3,
#   "total_images": 10,
#   "slicing_mode": "paired",
#   "next_steps": [...]
# }
```

**Which images need premium OCR?**

| Category | When | Action |
|----------|-------|--------|
| `needs_premium_ocr` | Tesseract failed or was skipped | ✅ Must call premium OCR |
| `premium_completed` | You already submitted OCR results | ❌ Do NOT re-OCR — wastes API calls |
| `informational_only` | Small icon/logo (<32×32px or <1KB) | ❌ Safe to ignore |
| `has_tesseract_result` | Tesseract produced text | ⚠️ Optional — re-OCR if quality insufficient |

### Step-by-Step Workflow

**Step 1**: Read document
```python
read_document_pair(pdf_path, docx_path)
# Returns: text + image list + next_steps
```

**Step 2**: Query image status with structured categories
```python
status = get_processing_status(doc_name)
# Returns: {needs_premium_ocr: [...], informational_only: [...], has_tesseract_result: [...], ...}
```

**Step 3**: Call premium OCR on each pending image
```python
# Example with minimax-token-plan MCP:
# Use understand_image tool with prompt "OCR this image, return all text"
markitdown-reader_get_cached_content(doc_name)  # Get image file paths
# For each pending image:
understand_image(image_path="/path/to/image.png", prompt="Return all text content in this image")
```

**Step 4**: Submit OCR results
```python
# Batch update all results at once
updates = [
    {"img_id": "p11_i1", "ocr_result": "充电接口互操作性测试框图...", "position_info": {...}},
    {"img_id": "p1_i0", "ocr_result": "产品封面...", "position_info": {...}},
]
update_batch_document_markdown(updates)
```

### After Premium OCR Update

When you call `update_batch_document_markdown`, the image's status changes to `premium_completed`.
Subsequent `get_processing_status` calls will show it under `premium_completed` — you do NOT need to OCR it again.

### Image File Path Access

Images are stored at:
```
~/.opencode/markitdown/{doc_name}/images/{doc}_p{page}_i{index}_{md5hash}.png
```

Get from `get_cached_content(doc_name)` → look for `images` list, or read `index.json`.

### Getting Latest Content After OCR Update

After calling `update_batch_document_markdown`, the `output.md` is **automatically rebuilt** with new OCR text.
The image's `ocr_status` changes to `premium_completed` — subsequent `get_processing_status` calls
will show it under `premium_completed`, so you know NOT to OCR it again.

```python
# Get updated content
result = get_cached_content(doc_name)
# result["content"] contains the rebuilt output.md
```

### 重要提醒

- **Do NOT** call `retry_failed_images()` for quality OCR — tesseract is not the right tool
- **Use** `update_batch_document_markdown` to commit premium OCR results
- **Image anchors** in `output.md` will update automatically after batch update
- **Small images** (icons, logos, <32x32px or <1KB) are excluded from `output.md` but saved to disk for audit

## 删除文档缓存

如果文档提取结果异常或需要强制重新处理，使用 `delete_cache`：

```python
result = delete_cache(doc_name)
# {"success": true, "doc_name": "...", "message": "Cache deleted successfully"}
```

**注意**：删除后文档将以全新状态重新处理，所有 OCR 结果将丢失。

## 目录结构

```
~/.opencode/markitdown/{文档名}/
├── slices/       # 分片文件
├── images/       # 图片池（持久化）
│   └── *.png
├── content.md    # 超长内容写入文件
└── index.json    # 元信息
```

## 关键约束

| 约束 | 值 |
|------|-----|
| PDF 分片 | 每 5 页一片 |
| DOCX 分片 | 每 **200** block 一片 |
| 直接返回上限 | 400K 字符（超限写文件） |
| 小图过滤 | <1KB 或 <32×32 → 不出现在 images 列表但仍保存到磁盘 + OCR |
| 大图 OCR 阈值 | <50KB → 自动 tesseract OCR，结果在返回中 |
| 大图 | ≥50KB，返回 file:// 路径 |
| 图片池 | 持久化到 ~/.opencode/markitdown/ |

## 快速查询

| 需求 | 工具 | 参数 |
|------|------|------|
| 读文档（首选） | `read_document` | `fast=True` 先探查 |
| 了解分片结构 | `slice_document` | `pages_per_slice=5` |
| 配对读取 | `read_document_pair` | — |
| 只提取图片 | `extract_images` | — |
| 查元信息 | `get_document_info` | — |
