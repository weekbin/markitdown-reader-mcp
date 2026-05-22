# markitdown-reader MCP Service

Model Context Protocol 服务，用于读取 PDF/DOCX 标准文档，支持自动分片、配对文件、OCR 图片识别。

## 功能特性

- **PDF 读取**：PyMuPDF 提取文字 + 图片，支持 CID-font 编码中文
- **DOCX 读取**：python-docx 提取文字 + 表格
- **自动分片**：PDF 每 5 页一片，DCI 多文档每 200 block 一片
- **配对文件**：自动检测同名 PDF+DOCX，PDF 提取图片、DOCX 提取文字，合并输出
- **图片池**：MD5 去重，持久化到 `~/.opencode/markitdown/{doc}/images/`
- **小图 OCR**：<50KB 图片自动调用 tesseract 识别中文
- **进程隔离**：每进程独立日志文件，避免多进程日志混写

## 工具接口

### `read_document(file_path, fast=False)`

主工具。自动检测配对文件，分片读取。

- `file_path`：文档路径（PDF 或 DOCX）
- `fast=True`：跳过图片提取（加快速度）

```python
# 单文件模式
read_document("/path/to/document.pdf")

# 配对模式（自动检测同名 docx）
read_document("/path/to/document.pdf")

# 快速模式（跳过图片）
read_document("/path/to/document.pdf", fast=True)
```

### `read_document_pair(pdf_path, docx_path)`

显式配对读取。PDF 提取图片，DOCX 提取文字表格。

```python
read_document_pair("/path/to/doc.pdf", "/path/to/doc.docx")
```

### `extract_images(file_path, page_range="")`

专门提取图片，返回图片列表及 file:// 路径。

```python
# 提取全部图片
extract_images("/path/to/document.pdf")

# 只提取指定页
extract_images("/path/to/document.pdf", page_range="1-5")
```

### `get_document_info(file_path)`

返回文档元信息：页数、分片数、图片数、配对建议。

### `slice_document(file_path, pages_per_slice=5)`

只做分片，返回 JSON 格式分片信息，不读取内容。

### `ocr_image(image_path)`

对单张图片进行 OCR 识别，返回识别文字。

### `list_supported_files()`

返回支持的文件格式和工具接口说明。

## 输出格式

```
[STATUS]
{...JSON 状态...}
[/STATUS]

# 文档名.pdf

配对: 是 → doc.docx
分片: 16片 (b1-200, b201-400, ...)
图片: 281张（含21张已OCR）

=== [b1-200] ===
[提取的文字内容...]

[图片: file:///home/weekbin/.opencode/markitdown/doc/images/...]
```

JSON 状态字段：
- `chars`：提取字符数
- `slice_count`：分片数
- `image_count`：图片数
- `ocr_count`：OCR 成功数
- `content_written`：是否超长写入文件
- `slices`：分片 ID 列表

## 安装

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装 tesseract OCR（Linux）

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

### 3. 配置 OpenCode MCP

在 `opencode.json` 的 `mcp` 节点添加：

```json
"markitdown-reader": {
  "type": "local",
  "command": [
    "/path/to/.venv/bin/python3",
    "/path/to/server.py"
  ],
  "enabled": true
}
```

## 依赖

- Python 3.12+
- `mcp[fastapi]` — MCP server framework
- `PyMuPDF` — PDF 读取和分片
- `python-docx` — DOCX 读取
- `lxml` — DOCX XML 解析
- `Pillow` — 图片处理
- `pytesseract` — OCR

## 目录结构

```
~/.opencode/markitdown/
└── {doc_name}/
    ├── slices/              # 分片文件
    │   ├── slice_000.pdf
    │   └── slice_000.docx
    ├── images/              # 图片池（MD5 去重）
    │   └── {doc}_p1_i0_abc123.png
    ├── index.json           # 元信息（分片列表+图片索引）
    └── content.md           # 超长内容写入文件
```

## 分片参数

| 文档类型 | 分片大小 | 说明 |
|----------|----------|------|
| PDF | 5 页/片 | 按物理页分片 |
| DOCX | 200 block/片 | 按段落+表格分块 |

字符数超 400000 时，内容写入 `content.md`，返回文件路径提示。
