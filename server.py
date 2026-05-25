# -*- coding: utf-8 -*-
"""markitdown-reader MCP Service - Thin entry point"""

import logging
import os

# Configure logging to ~/.opencode/markitdown/logs/markitdown.log
log_dir = os.path.expanduser("~/.opencode/markitdown/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "markitdown.log")

# Configure root logger as a fallback for libraries that use the root logger.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

# Also configure the "markitdown" named logger with its own FileHandler.
# This ensures our log records always reach markitdown.log even if the MCP
# framework modifies or replaces root logger handlers at runtime.
_fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
_fh = logging.FileHandler(log_file)
_fh.setFormatter(_fmt)
_markitdown_log = logging.getLogger("markitdown")
_markitdown_log.setLevel(logging.DEBUG)
_markitdown_log.addHandler(_fh)
# Keep propagate=True so root logger (stderr) also receives the records.
# The root FileHandler and _fh both point to the same file; that's fine because
# each handler opens the file in append mode and Python's logging is thread-safe.

from mcp.server.fastmcp import FastMCP

# Import all MCP tools from src.mcp_tools
from src.mcp_tools import (
    # Core document tools
    read_document,
    read_document_pair,
    extract_images,
    ocr_image,
    slice_document,
    get_document_info,
    # Utility tools
    list_supported_files,
    list_cache_dir,
    get_cached_content,
    delete_cache,
    # Update tools
    update_document_markdown,
    update_batch_document_markdown,
    # Status/resume tools
    get_processing_status,
    retry_failed_images,
    resume_document,
    # Version
    get_version,
    # Server instance (already configured with all tools)
    mcp,
)

# Entry point
if __name__ == "__main__":
    mcp.run()
