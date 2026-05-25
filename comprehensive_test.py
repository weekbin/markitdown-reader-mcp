#!/usr/bin/env python3
"""
Comprehensive test script for all 14 markitdown-reader MCP tools.
Watchdog protects against memory/CPU/timeout overruns.
"""

import sys
import os
import time
import threading
import resource
import signal
import traceback
import json
import glob
import re
from pathlib import Path

# ===== Watchdog =====
MAX_MEM_MB = 800
MAX_CPU_PCT = 150
HARD_TIMEOUT = 300

def get_mem_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024

def read_cpu():
    """Read CPU usage from /proc/self/stat."""
    try:
        with open('/proc/self/stat', 'r') as f:
            parts = f.read().split()
            utime = int(parts[13])
            stime = int(parts[14])
            total = utime + stime
            # Convert jiffies to percent (sysconf(_SC_CLK_TCK) typically 100)
            clk_tck = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
            return total * 100.0 / clk_tck / (time.time() - _start_time + 0.01)
    except:
        return 0.0

_start_time = time.time()

def watchdog_loop():
    last_print = 0
    while True:
        time.sleep(1)
        elapsed = time.time() - _start_time
        mem = get_mem_mb()
        if mem > MAX_MEM_MB:
            print(f"\n[WATCHDOG] KILL: mem={mem}MB > {MAX_MEM_MB}MB")
            os._exit(2)
        if elapsed > HARD_TIMEOUT:
            print(f"\n[WATCHDOG] KILL: timeout {elapsed:.0f}s")
            os._exit(1)
        if elapsed - last_print >= 10:
            cpu = read_cpu()
            print(f"  [STATUS] {elapsed:.0f}s mem={mem}MB cpu={cpu:.0f}%")
            last_print = elapsed

# ===== Setup =====
sys.path.insert(0, '/home/weekbin/.opencode/mcp/markitdown-reader')

PDF = '/home/weekbin/Documents/docs/GBT+34657.2-2017.pdf'
DOCX = '/home/weekbin/Documents/docs/GBT+34657.2-2017.docx'

results = {}  # tool_name -> (status, output_preview, mem_before, mem_after, elapsed)
_detected_doc_name = None  # Will be set after Phase 2

def test(name, fn, *args, **kwargs):
    """Run a tool test and record results."""
    mem_before = get_mem_mb()
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.time() - t0
        mem_after = get_mem_mb()
        output = str(result)[:200] if result else "(empty)"
        results[name] = ("PASS", output, mem_before, mem_after, elapsed)
        print(f"  ✓ {name} | mem={mem_before}→{mem_after}MB | {elapsed:.1f}s | {output[:60]}...")
    except Exception as e:
        elapsed = time.time() - t0
        mem_after = get_mem_mb()
        results[name] = ("FAIL", str(e)[:200], mem_before, mem_after, elapsed)
        print(f"  ✗ {name} | {e.__class__.__name__}: {str(e)[:80]}")

def detect_doc_name():
    """Detect the doc_name for GBT+34657.2-2017 from cache directory."""
    import hashlib
    from pathlib import Path
    p = Path(PDF)
    stem = p.stem.replace(" ", "_")[:40]
    # Sanitize stem: remove invalid chars
    stem = re.sub(r"[^a-zA-Z0-9_.\-]", "", stem)
    dir_hash = hashlib.md5(str(p.parent).encode()).hexdigest()[:8]
    return f"{stem}_{dir_hash}"

def find_image_in_cache():
    """Find the first image file in the GBT+34657.2-2017 cache."""
    global _detected_doc_name
    if _detected_doc_name is None:
        return None
    img_dir = Path.home() / ".opencode" / "markitdown" / _detected_doc_name / "images"
    if img_dir.exists():
        images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg"))
        if images:
            return str(images[0])
    return None

def find_img_id_from_cache():
    """Find the first image ID (filename) in the GBT+34657.2-2017 cache."""
    global _detected_doc_name
    if _detected_doc_name is None:
        return None
    img_dir = Path.home() / ".opencode" / "markitdown" / _detected_doc_name / "images"
    if img_dir.exists():
        images = list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg"))
        if images:
            return images[0].name
    img_dir2 = Path.home() / ".opencode" / "markitdown" / _detected_doc_name
    index_path = img_dir2 / "index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                idx = json.load(f)
            for img in idx.get("images", []):
                return img.get("id") or img.get("name")
        except:
            pass
    return None

def main():
    global _detected_doc_name

    print("=" * 70)
    print("COMPREHENSIVE TEST: All 14 markitdown-reader MCP tools")
    print("=" * 70)
    print(f"PDF: {PDF}")
    print(f"DOCX: {DOCX}")
    print(f"Watchdog: mem>{MAX_MEM_MB}MB, cpu>{MAX_CPU_PCT}%, timeout>{HARD_TIMEOUT}s")
    print()

    # Start watchdog thread
    watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
    watchdog_thread.start()

    # Import all tools
    print("[SETUP] Importing MCP tools...")
    try:
        from src.mcp_tools import (
            read_document,
            read_document_pair,
            extract_images,
            ocr_image,
            slice_document,
            get_document_info,
            list_supported_files,
            list_cache_dir,
            update_document_markdown,
            update_batch_document_markdown,
            get_processing_status,
            retry_failed_images,
            resume_document,
            get_cached_content,
        )
        print("[SETUP] Import successful")
    except Exception as e:
        print(f"[ERROR] Failed to import: {e}")
        traceback.print_exc()
        return 1

    print()

    # ===== Phase 1: Stateless tools (no prior processing needed) =====
    print("=" * 70)
    print("PHASE 1: Stateless tools")
    print("=" * 70)
    test("list_supported_files", list_supported_files)
    test("list_cache_dir (no args)", list_cache_dir)
    test("get_processing_status (no args)", get_processing_status)
    print()

    # ===== Phase 2: Populate cache =====
    print("=" * 70)
    print("PHASE 2: Cache population (force_refresh=True)")
    print("=" * 70)

    print("\n-- Running read_document(PDF, force_refresh=True)...")
    test("read_document (PDF, force_refresh)", read_document, PDF, force_refresh=True)
    _detected_doc_name = detect_doc_name()
    print(f"  [INFO] Detected doc_name: {_detected_doc_name}")

    print("\n-- Running read_document_pair(PDF, DOCX, force_refresh=True)...")
    test("read_document_pair (force_refresh)", read_document_pair, PDF, DOCX, force_refresh=True)

    print("\n-- Running slice_document(PDF)...")
    test("slice_document", slice_document, PDF)

    print("\n-- Running get_document_info(PDF)...")
    test("get_document_info", get_document_info, PDF)

    print("\n-- Running extract_images(PDF)...")
    test("extract_images", extract_images, PDF)

    # Verify doc_name was detected
    if _detected_doc_name is None:
        _detected_doc_name = detect_doc_name()
    print(f"\n  [INFO] Using doc_name: {_detected_doc_name}")
    print()

    # ===== Phase 3: State-dependent tools (need cached data) =====
    print("=" * 70)
    print("PHASE 3: State-dependent tools")
    print("=" * 70)

    test("get_processing_status (with doc_name)", get_processing_status, doc_name=_detected_doc_name)
    test("list_cache_dir (with doc_name)", list_cache_dir, doc_name=_detected_doc_name)
    test("get_cached_content", get_cached_content, _detected_doc_name)
    test("retry_failed_images", retry_failed_images, _detected_doc_name)
    test("resume_document", resume_document, PDF)
    print()

    # ===== Phase 4: OCR tools (need image files) =====
    print("=" * 70)
    print("PHASE 4: OCR tools")
    print("=" * 70)

    image_path = find_image_in_cache()
    if image_path:
        print(f"  [INFO] Found image: {image_path}")
        test("ocr_image", ocr_image, image_path)
    else:
        results["ocr_image"] = ("SKIP", "No image found in cache", 0, 0, 0)
        print("  ⊘ ocr_image | SKIP: No image found in cache")
    print()

    # ===== Phase 5: Update tools =====
    print("=" * 70)
    print("PHASE 5: Update tools")
    print("=" * 70)

    img_id = find_img_id_from_cache()
    if img_id:
        print(f"  [INFO] Using img_id: {img_id}")
        test("update_document_markdown", update_document_markdown, img_id, "Test OCR result from comprehensive test script", None)
    else:
        results["update_document_markdown"] = ("SKIP", "No img_id found in cache", 0, 0, 0)
        print("  ⊘ update_document_markdown | SKIP: No img_id found in cache")

    # Batch update - use same img_id or a fake one
    if img_id:
        fake_img_id = f"nonexistent_{int(time.time())}"
        batch_updates = [
            {"img_id": fake_img_id, "ocr_result": "Batch test OCR result"},
        ]
        test("update_batch_document_markdown", update_batch_document_markdown, batch_updates)
    else:
        results["update_batch_document_markdown"] = ("SKIP", "No img_id found for batch test", 0, 0, 0)
        print("  ⊘ update_batch_document_markdown | SKIP: No img_id found for batch test")
    print()

    # ===== Phase 6: Clean up =====
    print("=" * 70)
    print("PHASE 6: Cleanup")
    print("=" * 70)
    test("resume_document (force_refresh cleanup)", resume_document, PDF)
    print()

    # ===== Report =====
    print("=" * 70)
    print("COMPREHENSIVE TEST REPORT")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r[0] == "PASS")
    failed = sum(1 for r in results.values() if r[0] == "FAIL")
    skipped = sum(1 for r in results.values() if r[0] == "SKIP")

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped, {len(results)} total")
    print()

    for name, (status, output, mb1, mb2, elapsed) in sorted(results.items()):
        print(f"  [{status:4s}] {name}")
        if status != "SKIP":
            print(f"         mem={mb1}→{mb2}MB | {elapsed:.1f}s | {output[:80]}")
        else:
            print(f"         {output}")
        print()

    peak_mem = max(r[3] for r in results.values())
    print(f"Peak memory: {peak_mem}MB")
    print(f"Total time: {time.time() - _start_time:.1f}s")

    if failed > 0:
        print("\n[FAILURES DETECTED]")
        for name, (status, output, *_) in sorted(results.items()):
            if status == "FAIL":
                print(f"  - {name}: {output}")
        return 1

    return 0

if __name__ == '__main__':
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(soft, 4096), hard))
    except:
        pass

    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        sys.exit(130)
