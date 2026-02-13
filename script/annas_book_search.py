"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - Book Search Functionality
Handles searching for books on Anna's Archive and parsing search results.
"""

import re
import os
import logging
import random
from typing import List, Optional
from bs4 import BeautifulSoup

import sys
from pathlib import Path
# Import from other modules
try:
    from annas_config import logger, debug_print, BookResult, INTERACTIVE_MODE
except ModuleNotFoundError:
    from script.annas_config import logger, debug_print, BookResult, INTERACTIVE_MODE
try:
    from annas_utils import score_book_relevance, pause_for_input, random_delay
except ModuleNotFoundError:
    from script.annas_utils import score_book_relevance, pause_for_input, random_delay
import time
try:
    from annas_browser_manager import BrowserManager
except ModuleNotFoundError:
    from script.annas_browser_manager import BrowserManager

class BookSearcher:
    """Handles book searching and result parsing."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
    
    def search_books(self, query: str, max_results: int = 10, headless: bool = False) -> List[BookResult]:
        """
        Search for books on Anna's Archive.

        Returns a list of BookResult objects.
        """
        debug_print(f"search_books: Starting search with query: '{query}', max_results: {max_results}")
        self.browser_manager.init_browser(headless=headless)
        
        # Fix URL generation - ensure we have a proper base URL
        working_domain = self.browser_manager.find_working_domain()
        if not working_domain:
            debug_print("Could not find working domain")
            return []
        
        search_url = f"{working_domain}/search?q={query.replace(' ', '+')}"
        debug_print(f"Search URL: {search_url}")
        print(f"[INFO] Searching: {search_url}")
        
        debug_print("Navigating to search URL...")
        try:
            self.browser_manager._page.goto(search_url, wait_until='domcontentloaded', timeout=45000)
        except Exception as e:
            debug_print(f"Search navigation failed: {e}")
            if INTERACTIVE_MODE:
                pause_for_input("Search navigation failed. Fix in browser and press ENTER...")
        
        debug_print("Page loaded")
        
        # Wait for Cloudflare if present
        self.browser_manager.wait_for_cloudflare(self.browser_manager._page)
        
        debug_print("Waiting for results to load...")
        # Wait for results to load
        random_delay(2, 4)
        
        # Wait for book entries to appear on the page
        debug_print("Waiting for book entries to load...")
        try:
            # Wait for the main results container to appear
            self.browser_manager._page.wait_for_selector('.js-aarecord-list-outer', timeout=20000)
            debug_print("Results container found")
        except Exception as e:
            debug_print(f"Wait for selector failed: {e}")
            # If not found, check if we're blocked
            self.browser_manager.take_screenshot("search_failed.png")
            if INTERACTIVE_MODE:
                 pause_for_input("Results not found. Check search_failed.png, fix and press ENTER...")
        
        # Small delay to let content settle
        time.sleep(1)
        
        # Get page content directly
        content = self.browser_manager.get_page_content(self.browser_manager._page)
        
        if not content:
            debug_print("Failed to get page content")
            print("[ERROR] Failed to get page content")
            return []
        
        debug_print(f"Page content length: {len(content)} characters")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        results = []
        
        # CRITICAL: Find book entries ONLY in the main results container
        # The main results are in .js-aarecord-list-outer container
        debug_print("=== SELECTOR STRATEGY ===")
        debug_print("Primary: .js-aarecord-list-outer a[href*='/md5/']")
        
        # Primary selector: Main search results container
        results_container = soup.select_one('.js-aarecord-list-outer')
        if not results_container:
             debug_print("WARNING: .js-aarecord-list-outer not found, trying fallback...")
             book_entries = soup.select('a[href*="/md5/"]')
        else:
             book_entries = results_container.select('a[href*="/md5/"]')
        
        debug_print(f"Found {len(book_entries)} potential entries")
        
        seen_md5 = set()
        results = []
        
        # Process entries to find valid ones with titles
        for entry in book_entries:
            if len(results) >= max_results:
                break
                
            href = entry.get('href', '')
            
            # Skip if this is from Recent downloads (has tabindex="-1")
            if entry.get('tabindex') == '-1':
                continue
            
            # Extract MD5 from URL
            md5_match = re.search(r'/md5/([0-9a-f]{32})', href)
            if not md5_match:
                continue
            
            md5 = md5_match.group(1)
            
            # Skip if we already saw this MD5
            if md5 in seen_md5:
                continue
            
            # Get title from the link
            title = entry.get_text(strip=True)
            if not title:
                continue
            
            # Metadata extraction
            author = None
            format_type = None
            size = None
            
            # The structure provided by the user:
            # .js-aarecord-list-outer contains the entries.
            # Each entry has a title link and then metadata in a specific div.
            parent_container = entry.find_parent('div', class_='flex')
            if parent_container:
                # 1. Author search
                meta_links = parent_container.select('a[href*="/search?q="]')
                for m_link in meta_links:
                     if m_link != entry:
                          author = m_link.get_text(strip=True)
                          break
                
                # 2. Format, Size, Language search
                # Using the specific class pattern for the metadata row
                meta_row = parent_container.select_one('.text-gray-800, .dark\\:text-slate-400')
                if meta_row:
                    meta_text = meta_row.get_text(separator=' | ', strip=True)
                    debug_print(f"Found metadata row: {meta_text}")
                    
                    # Extract format
                    format_match = re.search(r'\b(PDF|EPUB|MOBI|FB2|RTF|AZW3?|DJVU|TXT)\b', meta_text, re.IGNORECASE)
                    if format_match:
                        format_type = format_match.group(1).upper()
                    
                    # Extract size
                    size_match = re.search(r'([\d.]+\s*[KMGT]?B)', meta_text)
                    if size_match:
                        size = size_match.group(1)
            
            book = BookResult(
                title=title[:200],
                author=author,
                format=format_type,
                size=size,
                url=f"{working_domain}/md5/{md5}",
                md5=md5
            )
            results.append(book)
            seen_md5.add(md5)
            debug_print(f"Added book: {book.title[:50]}... ({book.format}, {book.size})")
        
        debug_print(f"search_books: Returning {len(results)} results")
        print(f"[INFO] Found {len(results)} books")
        return results
    
    def score_and_sort_results(self, results: List[BookResult], query: str) -> List[BookResult]:
        """Score and sort search results by relevance and preferred format."""
        print("\n[INFO] Search Results (sorted by relevance and format):")
        scored_results = []
        for book in results:
            # Base score from title/author
            score = score_book_relevance(book.title, query)
            
            # Format bonus: Prioritize PDF and EPUB
            if book.format:
                fmt = book.format.upper()
                if fmt == 'PDF':
                    score += 20.0
                elif fmt == 'EPUB':
                    score += 15.0
                elif fmt in ['MOBI', 'AZW3']:
                    score += 5.0
                elif fmt == 'TXT':
                    score -= 10.0
            
            scored_results.append((score, book))
            debug_print(f"Scored '{book.title}' [{book.format}] -> {score:.1f}")
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        for i, (score, book) in enumerate(scored_results):
            print(f"  {i+1}. {book.title} [score: {score:.0f}]")
            print(f"     Author: {book.author or 'Unknown'}")
            print(f"     Format: {book.format or 'Unknown'}, Size: {book.size or 'Unknown'}")
            print(f"     URL: {book.url}")
            print()
        
        return [book for score, book in scored_results]