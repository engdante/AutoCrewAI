"""
Anna's Archive Tool - Configuration and Setup
Handles imports, constants, and logging configuration.
"""

import os
import sys
import warnings
import logging
from typing import Type, Optional, ClassVar, List, Dict, Any
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# Debug mode flag
DEBUG_MODE = True
INTERACTIVE_MODE = False  # Set to True for manual debugging

# Setup debug log file in script/ directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
DEBUG_LOG_FILE = os.path.join(script_dir, "annas_archive_tool.log")

# Setup logging
def setup_logging():
    """Setup logging configuration."""
    # Clear debug log at start
    if os.path.exists(DEBUG_LOG_FILE):
        try:
            os.remove(DEBUG_LOG_FILE)
        except Exception as e:
            print(f"[WARNING] Could not clear debug log: {e}")
    
    # Clear old debug HTML files in script directory
    debug_files = [
        "debug_search_page.html",
        "debug_book_page.html", 
        "debug_slow_download_page.html",
        "debug_mirror_page.html"
    ]
    for filename in debug_files:
        path = os.path.join(script_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                debug_print(f"Cleared old debug file: {filename}")
            except Exception as e:
                print(f"[WARNING] Could not clear debug file {filename}: {e}")
    
    # Create logger
    logger = logging.getLogger('annas_archive_tool')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(DEBUG_LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def debug_print(msg: str):
    """Print and log debug message if DEBUG_MODE is enabled.
    Logs are written to logs/annas_archive_tool.log with a timestamp for easier tracing
    of execution flow and failures."""
    if DEBUG_MODE:
        logger.debug(msg)

# Input schemas
class AnnasArchiveInput(BaseModel):
    """Input schema for AnnasArchiveTool."""
    query: str = Field(..., description="The name and author of the book to search for.")

class BookResult(BaseModel):
    """Represents a search result from Anna's Archive."""
    title: str
    author: Optional[str] = None
    format: Optional[str] = None
    size: Optional[str] = None
    url: str
    md5: Optional[str] = None

# Tool class definition (will be imported from main module)
class AnnasArchiveTool(BaseTool):
    """
    Search for books on Anna's Archive, download them, and read their content.
    
    Uses Playwright for reliable Cloudflare bypass.
    Integrates with crewAI and supports RAG indexing.
    """
    name: str = "annas_archive_tool"
    description: str = (
        "Search for books on Anna's Archive, download them, and read their content. "
        "Input: book title and optionally the author. "
        "Returns the path of the downloaded file and a summary or snippet of its content."
    )
    args_schema: Type[BaseModel] = AnnasArchiveInput

# IPFS Gateways for fallback downloads
IPFS_GATEWAYS: ClassVar[List[str]] = [
    "https://cloudflare-ipfs.com/ipfs/",
    "https://ipfs.io/ipfs/",
    "https://gateway.pinata.cloud/ipfs/",
    "https://dweb.link/ipfs/"
]

# Anna's Archive domains (they frequently change domains)
# Try in order - first working one will be used
DOMAINS: ClassVar[List[str]] = [
    "https://annas-archive.li",
    "https://annas-archive.se", 
    "https://annas-archive.org",
    "https://bg.annas-archive.li",
]

# Dynamic URL variables (will be set at runtime)
BASE_URL: ClassVar[str] = ""
SEARCH_URL: ClassVar[str] = ""
_working_domain: ClassVar[Optional[str]] = None

# Suppress Pydantic V2 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')