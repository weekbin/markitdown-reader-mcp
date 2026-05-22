# markitdown-reader MCP Service — Redesign Doc

## 决策

1. **配对检测不到时**：先问用户，用户提供则走配对模式；无法提供则走单文件模式（文字+表格+图片），告知用户无法保证质量但继续干活
2. **分片机制**：默认按页码分，每 5 页一片
3. **输出格式**：Markdown
4. **小图处理**：<50KB 内置 tesseract OCR，不上报主引擎

---

## 目录结构

```
~/.opencode/markitdown/
└── {doc_name}/
    ├── slices/              # 分片文件（临时）
    │   ├── {doc_name}_p1-5.pdf
    │   └── {doc_name}_p6-10.pdf
    ├── images/              # 图片池（持久化）
    │   ├── {doc_name}_p3_i0_md5hash.png
    │   └── ...
    └── index.json           # 元信息（分片列表+图片索引+OCR状态）
```

**图片池是持久化的**，跨调用不丢失。

---

## 工具接口

### 1. `read_document(file_path: str) -> str`
自动检测配对文件，分片读取，返回完整 Markdown。

**流程**：
```
用户传路径
    ↓
检测配对文件（同目录同名 .pdf/.docx）
    ↓
有配对 → read_document_pair
无配对 → 单文件模式
    ↓
分片（5页/片）
    ↓
逐片读取 + 合并
    ↓
图片提取 → 图片池（MD5去重）
小图(<50KB) → 内置 OCR
    ↓
返回 Markdown（含图片引用）
```

**返回格式**：
```
# {文档名}

[文字内容...]

[图片: file:///home/weekbin/.opencode/markitdown/{doc}/images/img.png]
[图片: file:///.../img.png]

---
分片信息: 3片, 页1-5/6-10/11-12
配对: 是/否
图片: 5张(含X张已OCR)
---
```

### 2. `read_document_pair(pdf_path: str, docx_path: str) -> str`
显式配对读取。PDF 提取图片，DOCX 提取文字/表格，合并。

### 3. `extract_images(file_path: str, page_range?: str) -> str`
专门提取图片，返回图片列表。小图内置 OCR。

### 4. `get_document_info(file_path: str) -> str`
返回页数、分片预估、图片数量、配对建议。

---

## 配对文件检测逻辑

```python
def _find_paired_file(path: str) -> str | None:
    """在同目录查找同名不同扩展名的配对文件"""
    stem = Path(path).stem
    directory = Path(path).parent
    for ext in ['.pdf', '.docx']:
        if Path(path).suffix.lower() != ext:
            paired = directory / f"{stem}{ext}"
            if paired.exists():
                return str(paired)
    return None
```

---

## 分片逻辑

### PDF 分片（PyMuPDF）
```python
def _slice_pdf(src: str, out_dir: str, pages_per_slice: int = 5) -> list[dict]:
    doc = fitz.open(src)
    slices = []
    for i in range(0, len(doc), pages_per_slice):
        end = min(i + pages_per_slice, len(doc))
        slice_doc = fitz.open()
        slice_doc.insert_pdf(doc, from_page=i, to_page=end-1)
        out_path = f"{out_dir}/slice_{i//pages_per_slice:03d}.pdf"
        slice_doc.save(out_path)
        slices.append({"id": f"p{i+1}-{end}", "path": out_path, "pages": (i+1, end)})
    return slices
```

### DOCX 分片（python-docx XML）
```python
def _slice_docx(src: str, out_dir: str, blocks_per_slice: int = 20) -> list[dict]:
    # 按段落+表格分块，每blocks_per_slice个block为一片
    # 写新docx，替换document.xml的body
```

---

## 图片提取策略

### PDF
- PyMuPDF `page.get_images(full=True)` + MD5 去重
- 大图(≥50KB): 写文件，返回 `file://` 路径
- 小图(<50KB): PIL+pytesseract OCR，结果写入图片池的 `.ocr.txt` 旁注文件

### DOCX
- ZIP 解压 `word/media/` + MD5 去重
- 同上大小图策略

### 去重
```python
# 全局 MD5 集合存在 index.json 中
# 提取前检查，已存在则跳过
# 新图写入图片池，更新 index.json
```

---

## 写入文件 vs 直接返回

- 单片内容 <400K 字符：直接返回 Markdown
- 总内容 >400K 或 >10分片：写入 `~/.opencode/markitdown/{doc}/content.md`，返回文件路径

---

## 配对询问流程（read_document 内部）

```
检测无配对
    ↓
返回提示："未找到配对文件，是否有另一格式版本？"
    ↓
用户可调用 read_document_pair(pdf, docx) 显式指定
    或继续调用 read_document(path) 单文件模式
```
