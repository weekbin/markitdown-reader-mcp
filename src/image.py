# -*- coding: utf-8 -*-
"""Image processing functions extracted from server.py"""

from __future__ import annotations

import os


def _is_small_image(img_path: str) -> bool:
    """判断图片是否属于小图（文件<1024字节 或 尺寸<32x32）"""
    try:
        if os.path.getsize(img_path) < 1024:
            return True
        from PIL import Image
        with Image.open(img_path) as img:
            w, h = img.size
            if w < 32 or h < 32:
                return True
    except Exception:
        pass
    return False


def _ocr_small_image(img_path: str) -> str:
    """对小于阈值的小图进行 OCR，返回识别文字"""
    try:
        from PIL import Image
        import pytesseract
        with Image.open(img_path) as img:
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            return text.strip()
    except Exception:
        return ""
