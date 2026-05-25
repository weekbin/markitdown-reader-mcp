# -*- coding: utf-8 -*-
"""Storage-related functions extracted from server.py"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

from .constants import BASE_DIR

_log = logging.getLogger("markitdown")


# ─────────────────────────────────────────────────────────────────
# 辅助：文件锁
# ─────────────────────────────────────────────────────────────────


def _lock_file(lock_path: Path):
    """获取文件锁，用于原子写操作"""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(lock_path, "w")
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
    return lock_fd


def _unlock_file(lock_fd):
    """释放文件锁"""
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
    lock_fd.close()


# ─────────────────────────────────────────────────────────────────
# 文件锁：带超时机制的读写锁
# ─────────────────────────────────────────────────────────────────


def _with_write_lock(doc_name: str, operation, timeout: float = 10.0):
    """
    对文档执行需要排他锁的操作。
    使用 fcntl.LOCK_EX | LOCK_NB，timeout 秒后抛出 TimeoutError。
    """
    lock_path = _get_doc_dir(doc_name) / ".write.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(lock_path, "w")
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() - start >= timeout:
                lock_fd.close()
                raise TimeoutError(
                    f"Write lock timeout after {timeout}s for {doc_name}"
                )
            time.sleep(0.1)
    try:
        return operation()
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


def _with_read_lock(doc_name: str, operation, timeout: float = 10.0):
    """
    对文档执行需要共享锁的操作。
    使用 fcntl.LOCK_SH | LOCK_NB，timeout 秒后抛出 TimeoutError。
    """
    lock_path = _get_doc_dir(doc_name) / ".read.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(lock_path, "w")
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() - start >= timeout:
                lock_fd.close()
                raise TimeoutError(f"Read lock timeout after {timeout}s for {doc_name}")
            time.sleep(0.1)
    try:
        return operation()
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


# ─────────────────────────────────────────────────────────────────
# 辅助：持久化目录
# ─────────────────────────────────────────────────────────────────


def _make_doc_name(file_path: str) -> str:
    """
    Generate a unique cache directory name from file path.
    Format: {stem}_{dir_hash} where dir_hash is MD5 of the parent directory path.
    This prevents documents with the same filename but different locations
    (e.g. docs/GBT34657.pdf vs backup/GBT34657.pdf) from sharing cache.
    """
    import re as re_module

    p = Path(file_path)
    stem = re_module.sub(r"[^a-zA-Z0-9_.\-]", "", p.stem.replace(" ", "_"))[:40]
    dir_hash = hashlib.md5(str(p.parent).encode()).hexdigest()[:8]
    return f"{stem}_{dir_hash}"


def _get_doc_dir(doc_name: str) -> Path:
    """获取文档专属目录，不存在则创建"""
    d = BASE_DIR / doc_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_source_dir(doc_name: str) -> Path:
    """获取源文件备份目录，不存在则创建"""
    d = _get_doc_dir(doc_name) / "source"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _backup_source_file(file_path: str, doc_name: str) -> Path:
    """复制原始文件到 source 目录，返回备份路径"""
    import shutil

    src = Path(file_path)
    dst = _get_source_dir(doc_name) / src.name
    shutil.copy2(src, dst)
    return dst


def _get_history_dir(doc_name: str) -> Path:
    """获取下一个历史 run 目录，不存在则创建"""
    doc_dir = _get_doc_dir(doc_name)
    history_dir = doc_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    # 查找已有 run 编号
    existing = [
        d for d in history_dir.iterdir() if d.is_dir() and d.name.startswith("run_")
    ]
    run_nums = []
    for d in existing:
        try:
            run_nums.append(int(d.name.split("_")[1]))
        except (IndexError, ValueError):
            pass
    next_run = max(run_nums) + 1 if run_nums else 1
    run_dir = history_dir / f"run_{next_run:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _move_current_to_history(doc_name: str) -> Optional[Path]:
    """将当前缓存（slices/images/content.md）移动到历史目录，返回历史目录路径"""
    import shutil

    doc_dir = _get_doc_dir(doc_name)
    history_run_dir = _get_history_dir(doc_name)
    moved_items = []
    for item in ["slices", "images", "output.md", "index.json"]:
        src = doc_dir / item
        if src.exists():
            dst = history_run_dir / item
            shutil.move(str(src), str(dst))
            moved_items.append(item)
    _log.debug(f"  _move_current_to_history: moved {moved_items} to {history_run_dir}")
    return history_run_dir


def _calculate_content_hash(file_path: str) -> str:
    """计算文件内容的 MD5 哈希值，用于缓存验证"""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_slices_dir(doc_name: str) -> Path:
    d = _get_doc_dir(doc_name) / "slices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_images_dir(doc_name: str) -> Path:
    d = _get_doc_dir(doc_name) / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_index_path(doc_name: str) -> Path:
    return _get_doc_dir(doc_name) / "index.json"


def _load_index(doc_name: str) -> dict:
    p = _get_index_path(doc_name)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        # 确保新字段存在（向后兼容）
        data.setdefault("content_hash", "")
        data.setdefault("source_file", "")
        data.setdefault("runs", [])
        return data
    return {
        "slices": [],
        "images": [],
        "ocr_done": [],
        "content_hash": "",
        "source_file": "",
        "runs": [],
    }


def _save_index(doc_name: str, index: dict):
    lock_path = _get_doc_dir(doc_name) / ".index.lock"
    lock_fd = _lock_file(lock_path)
    try:
        p = _get_index_path(doc_name)
        p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        _unlock_file(lock_fd)


def _save_index_nolock(doc_name: str, index: dict):
    """无锁保存index（调用前需先获取锁）"""
    p = _get_index_path(doc_name)
    p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _delete_cache(doc_name: str) -> bool:
    """Delete all cached files for a document. Returns True if deleted, False if not found."""
    import shutil

    doc_dir = _get_doc_dir(doc_name)
    if not doc_dir.exists():
        return False

    # Recursively delete slices/, images/, output.md, content.md, index.json, and lock files
    for subdir in ["slices", "images"]:
        subpath = doc_dir / subdir
        if subpath.exists():
            shutil.rmtree(subpath)

    for fname in ["output.md", "content.md", "index.json"]:
        fpath = doc_dir / fname
        if fpath.exists():
            fpath.unlink()

    for lockfile in doc_dir.glob("*.lock"):
        lockfile.unlink()

    return True
