"""
Anna's Archive Tool - Book Search Functionality
Handles searching for books on Anna's Archive and parsing search results.
"""

import re
import os
import logging
import random
from typing import List, Optional
from bs4 import BeautifulSoup

# Import from other modules
from annas_config import logger, debug_print, BookResult
from annas_utils import score_book_relevance, pause_for_input
from annas_browser_manager import BrowserManager

class BookSearcher:
    """Handles book searching and result parsing."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
    
    def search_books(self, query: str, max_results: int = 10) -> List[BookResult]:
        """
        Search for books on Anna's Archive.

        Returns a list of BookResult objects.
        """
        debug_print(f"search_books: Starting search with query: '{query}', max_results: {max_results}")
        self.browser_manager.init_browser(headless=False)  # Changed to False for visible browser
        
        # Fix URL generation - ensure we have a proper base URL
        working_domain = self.browser_manager.find_working_domain()
        if not working_domain:
            debug_print("Could not find working domain")
            return []
        
        search_url = f"{working_domain}/search?q={query.replace(' ', '+')}"
        debug_print(f"Search URL: {search_url}")
        print(f"[INFO] Searching: {search_url}")
        
        pause_for_input("Press ENTER to navigate to search page...")
        
        debug_print("Navigating to search URL...")
        self.browser_manager._page.goto(search_url, wait_until='networkidle')
        debug_print("Page loaded (networkidle)")
        
        # Wait for Cloudflare if present
        self.browser_manager.wait_for_cloudflare(self.browser_manager._page)
        
        debug_print("Waiting for results to load...")
        # Wait for results to load
        import time
        time.sleep(random.uniform(3, 5))
        
        # Wait for page to be stable
        try:
            self.browser_manager._page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception as e:
            debug_print(f"wait_for_load_state timeout: {e}")
        
        pause_for_input("Press ENTER to parse page content...")
        
        # Parse results
        results = []
        
        # Wait for book entries to appear on the page
        debug_print("Waiting for book entries to load...")
        try:
            # Wait for the main results container to appear
            self.browser_manager._page.wait_for_selector('.js-aarecord-list-outer', timeout=30000)
            debug_print("Results container found")
        except Exception as e:
            debug_print(f"Wait for selector failed: {e}")
            # Try alternative selectors
            try:
                self.browser_manager._page.wait_for_selector('a[href*="/md5/"]', timeout=10000)
                debug_print("Alternative selector found")
            except Exception as e2:
                debug_print(f"Alternative selector also failed: {e2}")
        
        # Small delay to let content settle
        import time
        time.sleep(random.uniform(1, 2))
        
        # Get page content directly without waiting for networkidle
        content = self.browser_manager.get_page_content(self.browser_manager._page)
        
        if not content:
            debug_print("Failed to get page content")
            print("[ERROR] Failed to get page content")
            return []
        
        debug_print(f"Page content length: {len(content)} characters")
        
        # Save to debug file
        self.browser_manager.save_debug_page(content, "debug_search_page.html")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # CRITICAL: Find book entries ONLY in the main results container
        # NOT in "Recent downloads" section which has links with tabindex="-1"
        # The main results are in .js-aarecord-list-outer container
        debug_print("=== SELECTOR STRATEGY ===")
        debug_print("Primary: .js-aarecord-list-outer a[href*='/md5/']")
        
        # Primary selector: Main search results container
        book_entries = soup.select('.js-aarecord-list-outer a[href*="/md5/"]')
        debug_print(f"Found {len(book_entries)} entries in main results container")
        
        if not book_entries:
            # Fallback: Find entries with line-clamp class (typical for search results)
            debug_print("Fallback: a.line-clamp-\\[3\\][href*='/md5/']")
            book_entries = soup.select('a.line-clamp-\\[3\\][href*="/md5/"]')
            debug_print(f"Found {len(book_entries)} entries with line-clamp class")
        
        if not book_entries:
            # Last resort: all md5 links but filter out recent downloads
            debug_print("Last resort: filtering out tabindex=-1 links (Recent downloads)")
            all_md5_links = soup.select('a[href*="/md5/"]')
            # Filter out links with tabindex="-1" (these are from Recent downloads)
            book_entries = [a for a in all_md5_links if a.get('tabindex') != '-1']
            debug_print(f"Found {len(book_entries)} entries after filtering")
        
        if not book_entries:
            debug_print("WARNING: No book entries found!")
            debug_print("Page content saved to debug_search_page.html for inspection")
            print("[DEBUG] Page content saved to debug_search_page.html")
        
        pause_for_input(f"Press ENTER to process {len(book_entries)} book entries...")
        
        # DEBUG: Print HTML structure of first 3 entries
        debug_print("=== HTML STRUCTURE OF FIRST 3 ENTRIES ===")
        for i, entry in enumerate(book_entries[:3]):
            debug_print(f"\n--- Entry {i+1} ---")
            # Get parent container for context
            parent = entry.find_parent('div', class_='flex')
            parent_text = parent.get_text(separator=' | ', strip=True)[:300] if parent else "No parent"
            debug_print(f"Parent text: {parent_text}")
            debug_print(f"Link text: {entry.get_text(strip=True)[:100]}")
            debug_print(f"Href: {entry.get('href', 'NO HREF')}")
            debug_print(f"Tabindex: {entry.get('tabindex', 'NONE')}")
        debug_print("=== END HTML STRUCTURE ===\n")
        
        seen_md5 = set()
        md5_data = {}  # Store {md5: {title, author, format, size, entry}} for later processing
        
        # First pass: collect all entries grouped by MD5
        for entry in book_entries[:max_results * 5]:  # Get extra to find best match per MD5
            href = entry.get('href', '')
            
            # Skip if this is from Recent downloads (has tabindex="-1")
            if entry.get('tabindex') == '-1':
                continue
            
            # Extract MD5 from URL
            md5_match = re.search(r'/md5/([0-9a-f]{32})', href)
            if not md5_match:
                continue
            
            md5 = md5_match.group(1)
            
            # Get title from the link
            title = entry.get_text(strip=True)
            
            # Skip entries with empty title (usually cover image links)
            if not title:
                debug_print(f"Skipping entry with empty title: {href}")
                continue
            
            # If this MD5 already has a title, skip
            if md5 in md5_data:
                continue
            
            # Store entry data
            md5_data[md5] = {
                'title': title,
                'entry': entry
            }
        
        # Second pass: extract metadata and create BookResult objects
        for md5, data in md5_data.items():
            if len(results) >= max_results:
                break
                
            entry = data['entry']
            title = data['title']
            
            # Try to get author and other metadata from parent container
            author = None
            format_type = None
            size = None
            
            parent_div = entry.find_parent('div', class_='flex')
            if parent_div:
                # Find author link (usually has icon-[mdi--user-edit])
                author_link = parent_div.select_one('a[href*="/search?q="]')
                if author_link and author_link != entry:
                    author = author_link.get_text(strip=True)
                
                # Find format/size info (usually in a text node)
                parent_text = parent_div.get_text(separator=' | ', strip=True)
                
                # Extract format (PDF, EPUB, MOBI, etc.)
                format_match = re.search(r'\b(PDF|EPUB|MOBI|FB2|RTF|AZW3?|DJVU|TXT)\b', parent_text, re.IGNORECASE)
                if format_match:
                    format_type = format_match.group(1).upper()
                
                # Extract size (e.g., "0.3MB", "2.5MB")
                size_match = re.search(r'([\d.]+\s*[KMGT]?B)', parent_text)
                if size_match:
                    size = size_match.group(1)
            
            book = BookResult(
                title=title[:100] if title else "Unknown Title",
                author=author,
                format=format_type,
                size=size,
                url=f"{working_domain}/md5/{md5}",
                md5=md5
            )
            results.append(book)
            debug_print(f"Added book: {book.title[:50]}... (author={author}, format={format_type}, size={size})")
        
        debug_print(f"search_books: Returning {len(results)} results")
        print(f"[INFO] Found {len(results)} books")
        return results
    
    def score_and_sort_results(self, results: List[BookResult], query: str) -> List[BookResult]:
        """Score and sort search results by relevance."""
        print("\n[INFO] Search Results (sorted by relevance):")
        scored_results = []
        for book in results:
            score = score_book_relevance(book.title, query)
            scored_results.append((score, book))
            debug_print(f"Scored '{book.title}' -> {score:.1f}")
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        for i, (score, book) in enumerate(scored_results):
            print(f"  {i+1}. {book.title} [score: {score:.0f}]")
            print(f"     Author: {book.author or 'Unknown'}")
            print(f"     Format: {book.format or 'Unknown'}, Size: {book.size or 'Unknown'}")
            print(f"     URL: {book.url}")
            print()
        
        return [book for score, book in scored_results]