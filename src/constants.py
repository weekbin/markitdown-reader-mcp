"""Constants extracted from server.py"""

from pathlib import Path

SLICE_PAGES = 5  # 每5页一片
SLICE_BLOCKS = 200  # DOCX 每200 block 一片
IMAGE_SIZE_THRESHOLD = 50 * 1024  # 50KB
BASE_DIR = Path.home() / ".opencode" / "markitdown"
MAX_CHARS_RETURN = 0  # always write to file
