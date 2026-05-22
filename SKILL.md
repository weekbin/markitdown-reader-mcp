# markitdown-reader MCP Service — Agent Guide

## 核心原则

**最优策略：同时提供 PDF + DOCX 配对文件，一次性获得完整结果。**

单文件模式的已知缺陷：
- 只提供 PDF → 文字乱码（CID-font 问题），图片正常
- 只提供 DOCX → 文字正常，可能无法提取图片

## 工具接口（5个）

### 1. read_document(path, fast=False)
**首选工具**。传入任意路径，自动检测配对文件并读取。

**参数**：
- `fast=False`（默认）：文字 + 图片全量，较慢
- `fast=True`：只读文字，跳过图片提取，**秒回**

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
  "mode": "pdf_single"
}
```

**mode 取值**：`paired` / `pdf_single` / `docx_single`

**调度规则（按顺序检查 STATUS）**：
1. `need_pairing: true` → **立即询问用户**能否提供另一格式
2. `fast: true` → 图片未提取，需要单独用 `extract_images()` 补
3. `content_written: true` → 读取 `content_path` 获取完整内容
4. `images_extracted: false` → 调用 `extract_images()` 提取图片

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

### 3. read_document_pair(pdf_path, docx_path)
**显式配对读取**。用户已确认有配对文件时使用。

```python
read_document_pair("/path/a.pdf", "/path/a.docx")
```
→ DOCX 提取文字表格，PDF 提取图片

### 4. extract_images(path)
**单独提取图片**。小图(<50KB)已内置 OCR，返回路径列表。

### 5. get_document_info(path)
查看元信息：页数、段落数、表格数、预估分片数、配对建议。

## 调度流程

### 完整读取大文档

**Step 1**：快速探查
```
read_document(path, fast=True)   ← 先用 fast 模式，秒回
  → 看 STATUS need_pairing / fast / content_written
```

**Step 2a**：`need_pairing: true` → 询问用户能否提供另一格式

**Step 2b**：有配对或用户确认 → `read_document_pair(pdf, docx, fast=False)`

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
|------|------|
| PDF 分片 | 每 5 页一片 |
| DOCX 分片 | 每 20 block 一片 |
| 直接返回上限 | 400K 字符（超限写文件） |
| 小图 OCR 阈值 | <50KB（内置 tesseract） |
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
