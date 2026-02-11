"""
Anna's Archive Tool - Utility Functions
Contains helper functions for relevance scoring, file type detection, and other utilities.
"""

import re
import os
import time
import random
import logging
from typing import Optional, Tuple

# Import logger from config
from annas_config import logger, debug_print, DEBUG_MODE, INTERACTIVE_MODE

def is_relevant(title: str, query: str) -> bool:
    """Check if title is relevant to the search query."""
    if not title or not query:
        return False
    
    # Normalize both strings
    title_lower = title.lower()
    query_words = set(query.lower().split())
    
    # Count how many query words appear in title
    matches = sum(1 for word in query_words if word in title_lower)
    
    # At least 50% of query words should match
    min_matches = max(1, len(query_words) // 2)
    return matches >= min_matches


def score_book_relevance(book_title: str, query: str) -> float:
    """
    Score how relevant a book title is to the search query.
    Higher score = better match.
    
    Scoring:
    - Exact title match: 100
    - Title starts with query: 90
    - Title contains query as whole words: 80
    - Query words in title: 10 per word
    - Penalty for extra words in title: -5 per extra word
    """
    if not book_title or not query:
        return 0.0
    
    title_lower = book_title.lower().strip()
    query_lower = query.lower().strip()
    
    # Exact match
    if title_lower == query_lower:
        return 100.0
    
    # Title starts with query
    if title_lower.startswith(query_lower):
        return 90.0
    
    # Title contains query as substring
    if query_lower in title_lower:
        # Check if it's a whole word match
        pattern = r'\b' + re.escape(query_lower) + r'\b'
        if re.search(pattern, title_lower):
            return 80.0
        return 60.0
    
    # Count query words in title
    query_words = set(query_lower.split())
    title_words = set(title_lower.split())
    
    words_in_title = sum(1 for word in query_words if word in title_lower)
    exact_word_matches = len(query_words & title_words)
    
    score = (words_in_title * 10) + (exact_word_matches * 5)
    
    # Penalty for extra words that are NOT in query
    # This helps penalize "The Maker of Dune" vs "Dune"
    extra_words = len(title_words - query_words)
    score -= extra_words * 2
    
    # Bonus for shorter titles (more likely to be exact match)
    if len(title_words) <= len(query_words) + 2:
        score += 10
    
    return max(0.0, score)

def pause_for_input(msg: str = "Press ENTER to continue..."):
    """Pause execution and wait for user input."""
    if INTERACTIVE_MODE:
        input(f"\n>>> {msg}")

def random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """Add random delay to avoid detection."""
    delay = random.uniform(min_sec, max_sec)
    debug_print(f"random_delay: Sleeping for {delay:.2f} seconds")
    time.sleep(delay)

def verify_file_type(path: str, initial_ext: str) -> Tuple[str, str]:
    """Verifies file type using magic bytes and renames if necessary."""
    debug_print(f"verify_file_type: Verifying file: {path}")
    if not os.path.exists(path):
        debug_print(f"File does not exist: {path}")
        return path, initial_ext
        
    with open(path, "rb") as f:
        header = f.read(1024)
    
    real_ext = initial_ext
    if header.startswith(b"%PDF"):
        real_ext = "pdf"
    elif header.startswith(b"PK\x03\x04"):
        if b"mimetypeapplication/epub+zip" in header:
            real_ext = "epub"
        else:
            real_ext = "epub" 
    elif b"BOOKMOBI" in header:
        real_ext = "mobi"
    elif header.startswith(b"\xef\xbb\xbf") or all(32 <= b <= 126 or b in [9, 10, 13] for b in header[:100]):
        real_ext = "txt"

    debug_print(f"Detected file type: {real_ext} (initial: {initial_ext})")
    
    if real_ext != initial_ext:
        new_path = os.path.splitext(path)[0] + f".{real_ext}"
        try:
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(path, new_path)
            debug_print(f"Renamed file to: {new_path}")
            return new_path, real_ext
        except Exception as e:
            debug_print(f"Could not rename file: {e}")
            print(f"[WARNING] Could not rename file: {e}")
            return path, real_ext
    
    return path, real_ext

def resolve_download_dir(download_dir: Optional[str], crew_name: Optional[str]) -> str:
    """Determine the download directory."""
    debug_print(f"resolve_download_dir: download_dir={download_dir}, crew_name={crew_name}")
    if download_dir:
        path = os.path.abspath(download_dir)
        debug_print(f"Using explicit download directory: {path}")
        print(f"[INFO] Using explicit download directory: {path}")
        return path
    
    if crew_name:
        path = os.path.abspath(os.path.join(project_root, "crews", crew_name, "input"))
        debug_print(f"Using crew-specific input directory: {path}")
        print(f"[INFO] Using crew-specific input directory: {path}")
        return path
        
    env_output_dir = os.environ.get("CREW_OUTPUT_DIR")
    if env_output_dir:
        crew_base_dir = os.path.dirname(os.path.abspath(env_output_dir))
        path = os.path.join(crew_base_dir, "input")
        debug_print(f"Using environment-derived input directory: {path}")
        print(f"[INFO] Using environment-derived input directory: {path}")
        return os.path.abspath(path)
    
    path = os.path.abspath(os.path.join(project_root, "input"))
    debug_print(f"Using default project input directory: {path}")
    print(f"[INFO] Using default project input directory: {path}")
    return path

# Import project_root from config
from annas_config import project_root