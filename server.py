# -*- coding: utf-8 -*-
"""markitdown-reader MCP Service - Thin entry point"""

import logging
import os

# Configure logging to ~/.opencode/markitdown/logs/markitdown.log
log_dir = os.path.expanduser("~/.opencode/markitdown/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "markitdown.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

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
