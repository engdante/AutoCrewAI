"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - Download Manager
Handles downloading books, extracting download links, and file conversion.
This module now imports functionality from specialized modules.
"""

from typing import Dict, List, Optional, Tuple
try:
    from annas_download_manager_core import DownloadManager
except ModuleNotFoundError:
    from script.annas_download_manager_core import DownloadManager
try:
    from annas_link_extractor import get_download_links
except ModuleNotFoundError:
    from script.annas_link_extractor import get_download_links
try:
    from annas_file_converter import convert_mobi_to_txt, convert_mobi_fallback, read_file_content
except ModuleNotFoundError:
    from script.annas_file_converter import convert_mobi_to_txt, convert_mobi_fallback, read_file_content

import sys
from pathlib import Path
# Re-export the DownloadManager class for backward compatibility
__all__ = ['DownloadManager']