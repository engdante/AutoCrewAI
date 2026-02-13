"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - Link Extractor
Contains methods for extracting download links from book pages.
"""

import re
import time
import os
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

import sys
from pathlib import Path
# Import from other modules
try:
    from annas_config import debug_print, IPFS_GATEWAYS, INTERACTIVE_MODE, project_root
except ModuleNotFoundError:
    from script.annas_config import debug_print, IPFS_GATEWAYS, INTERACTIVE_MODE, project_root
try:
    from annas_utils import random_delay, pause_for_input
except ModuleNotFoundError:
    from script.annas_utils import random_delay, pause_for_input

def _is_valid_download_link(href: str) -> bool:
    """
    Validate if a href is a valid download link and not a navigation link.
    """
    if not href or not href.startswith('http'):
        return False
    
    # Skip navigation/account links
    skip_patterns = [
        '/account/', '/login', '/register', '/signup', '/auth/',
        '/faq', '/contact', '/donate', '/blog', '/search',
        '/md5/', '/isbn/', '/doi/', '/torrents/', '/datasets/',
        'jdownloader.org'
    ]
    
    for pattern in skip_patterns:
        if pattern in href.lower():
            return False
    
    # Should contain file extension or download keyword
    has_file_ext = any(href.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi', '.zip', '.torrent'])
    has_download_keyword = any(kw in href.lower() for kw in ['download', 'zlib', 'getfile', 'partner'])
    
    return has_file_ext or has_download_keyword

def _extract_direct_link_from_html(page_content: str) -> Optional[str]:
    """
    Extracts a direct download link from the page HTML based on specific patterns.
    Prioritizes text content within certain tags.
    """
    soup = BeautifulSoup(page_content, 'html.parser')
    
    # Strategy 1: Look for the specific pattern identified by the user
    # <span class="bg-gray-200 ...">https://b4mcx2ml.net/...pdf</span>
    for span_tag in soup.select('span.bg-gray-200.pl-2.pr-1.ml-\\[-4px\\].rounded.whitespace-normal.break-all'):
        link_text = span_tag.get_text(strip=True)
        if link_text.startswith('http') and _is_valid_download_link(link_text):
            debug_print(f"Found direct link in span.bg-gray-200: {link_text}")
            return link_text
            
    # Strategy 2: Look for 'Download' buttons with hrefs that are direct links
    # This covers cases where the direct link is the href of a button/link
    download_link_selectors = [
        'a[href*="/get/"]', # Common pattern
        'a[href*="download"]',
        'a[href*="/file/"]',
        'a[onclick*="navigator.clipboard.writeText"]' # To catch the copy button links
    ]

    for selector in download_link_selectors:
        for link_tag in soup.select(selector):
            href = link_tag.get('href')
            if href and href.startswith('http') and _is_valid_download_link(href):
                debug_print(f"Found direct link via selector {selector}: {href}")
                return href
            # Check onclick attribute for copyable links
            onclick = link_tag.get('onclick')
            if onclick and 'navigator.clipboard.writeText' in onclick:
                match = re.search(r"navigator\.clipboard\.writeText\('([^']+)'\)", onclick)
                if match:
                    copied_link = match.group(1)
                    if copied_link.startswith('http') and _is_valid_download_link(copied_link):
                        debug_print(f"Found direct link in onclick attribute: {copied_link}")
                        return copied_link

    # Strategy 3: Check meta tags or script tags if they contain direct links (less common)
    for meta_tag in soup.select('meta[property="og:url"], meta[itemprop="contentUrl"]'):
        content_url = meta_tag.get('content')
        if content_url and content_url.startswith('http') and _is_valid_download_link(content_url):
            debug_print(f"Found direct link in meta tag: {content_url}")
            return content_url
            
    return None

def find_slow_download_button(page) -> List[str]:
    """
    Find and return up to 3 Slow Download URLs from the MD5 page.
    Logic from anni logic.txt: #md5-panel-downloads > div:nth-child(2) > ul
    """
    debug_print("=== STRATEGY: Looking for Slow Download links ===")
    
    slow_download_urls = []
    try:
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # 1. Try the specific selector from anni logic.txt
        # #md5-panel-downloads > div:nth-child(2) > ul
        slow_download_section = soup.select_one('#md5-panel-downloads > div:nth-child(2) > ul')
        
        # 2. Fallback: Search for any list containing "Slow Partner Server"
        if not slow_download_section:
            debug_print("Specific selector failed, searching for 'Slow download' section...")
            slow_headers = soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'div'] and 'Slow download' in tag.get_text())
            for header in slow_headers:
                parent = header.parent
                ul = parent.find('ul')
                if ul:
                    slow_download_section = ul
                    break
        
        if slow_download_section:
            links = slow_download_section.select('a[href*="/slow_download/"]')
            base_url = page.url.split('/md5/')[0]
            
            for link in links[:3]: # Get first 3 as requested
                href = link.get('href')
                if href:
                    if href.startswith('http'):
                        slow_download_urls.append(href)
                    else:
                        slow_download_urls.append(f"{base_url}{href}")
            
            if slow_download_urls:
                debug_print(f"Found {len(slow_download_urls)} slow download links")
                for i, url in enumerate(slow_download_urls):
                    print(f"[INFO] Slow Download link {i+1}: {url[:80]}...")
        
    except Exception as e:
        debug_print(f"Error finding slow download links: {e}")

    return slow_download_urls

def handle_countdown_timer(page) -> bool:
    """
    Handle countdown timer on slow download page.
    Returns True if countdown was handled successfully or button appeared.
    """
    debug_print("=== Handling countdown timer ===")
    
    # Wait for the download button or countdown to appear
    start_time = time.time()
    max_wait = 180 # Increased wait time to be safe
    
    while time.time() - start_time < max_wait:
        content = page.content()
        
        # Check if the final download URL span or button is present
        # Based on: body > main > div > p:nth-child(8) > span > button
        if 'bg-gray-200' in content or 'navigator.clipboard.writeText' in content:
            debug_print("Download button/URL detected!")
            # Small extra wait to ensure everything is rendered
            time.sleep(1)
            return True
            
        # Check for countdown text (English and Bulgarian)
        # "seconds remaining" or "секунди остават" or "остават още"
        match = re.search(r'(\d+)\s*(seconds? remaining|секунди остават|остават още|секунди|seconds)', content, re.IGNORECASE)
        if match:
            sec = match.group(1)
            print(f"[INFO] Countdown: {sec}s remaining...", end='\r')
        
        time.sleep(2)
    
    debug_print("Countdown wait timed out or failed.")
    return False

def extract_download_links_after_countdown(page) -> Optional[str]:
    """
    Extract the final direct download URL from the page after countdown finishes.
    Uses direct link extraction patterns first, then falls back to "Download now" search.
    Includes GUI user confirmation before returning the link.
    """
    debug_print("=== Extracting final download URL (with GUI Confirmation) ===")
    
    try:
        content = page.content()
        
        # Strategy 1: Use direct link extraction logic (span, onclick, etc.)
        found_url = _extract_direct_link_from_html(content)
        
        # Strategy 2: Fallback to looking for "Download now" link directly
        if not found_url:
            soup = BeautifulSoup(content, 'html.parser')
            download_now_links = soup.select('a[target="_blank"]')
            
            for a in download_now_links:
                text = a.get_text(strip=True).lower()
                if 'download' in text and 'now' in text:
                    href = a.get('href')
                    if href and _is_valid_download_link(href):
                        found_url = href
                        break
        
        if found_url:
            debug_print(f"Found URL: {found_url}")
            return found_url
        
        print(f"[ERROR] 'Download now' button or direct link not found!")
        debug_print("STRICT: Download link not found on this page.")

    except Exception as e:
        debug_print(f"Error extracting final download URL: {e}")

    return None

def find_mirror_links(page) -> Dict[str, List[str]]:
    """
    Find mirror links as fallback when no slow download button is found.
    Returns dict with keys: 'direct', 'mirrors', 'ipfs'
    """
    debug_print("=== STRATEGY 2: Looking for mirror links ===")
    
    content = page.content()
    soup = BeautifulSoup(content, 'html.parser')
    
    links = {
        'direct': [],
        'mirrors': [],
        'ipfs': []
    }
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    debug_print(f"Found {len(all_links)} total links on page")
    
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True).lower()
        
        # Skip empty or javascript links
        if not href or href.startswith('javascript:'):
            continue
        
        # Mirror sites (only full URLs)
        mirror_domains = ['libgen', 'library.lol', 'z-lib', 'zlib', 'singlelogin', 'skland']
        if any(domain in href.lower() for domain in mirror_domains) and href.startswith('http'):
            debug_print(f"Found mirror link: {href[:60]}...")
            links['mirrors'].append(href)
            continue
        
        # Links from download buttons (only full URLs)
        if 'download' in text and href.startswith('http'):
            debug_print(f"Found download button link: {href[:60]}...")
            links['mirrors'].append(href)
    
    return links

def get_download_links(browser_manager, book_url: str) -> Dict[str, List[str]]:
    """
    Extract download links from book detail page.
    
    Strategy: 
    1. Find top 3 Slow Download URLs on the MD5 page.
    2. For each, wait for countdown and look STRICTLY for "Download now" button.
    3. If not found, move to next slow link.
    
    Returns dict with keys: 'direct', 'mirrors', 'ipfs'
    """
    debug_print(f"get_download_links: {book_url}")
    print(f"[INFO] Fetching book details: {book_url}")
    
    debug_print("Navigating to book page...")
    try:
        browser_manager._page.goto(book_url, wait_until='domcontentloaded', timeout=45000)
    except Exception as e:
        debug_print(f"Initial navigation failed: {e}")
        return {'direct': [], 'mirrors': [], 'ipfs': []}
    
    browser_manager.wait_for_cloudflare(browser_manager._page)
    random_delay(2, 4)
    
    links = {
        'direct': [],
        'mirrors': [],
        'ipfs': []
    }
    
    # 1. Find up to 3 slow download links from MD5 page
    slow_download_urls = find_slow_download_button(browser_manager._page)
    
    if slow_download_urls:
        for i, slow_url in enumerate(slow_download_urls):
            debug_print(f"Trying slow download link {i+1}/3: {slow_url}")
            try:
                # Navigate to the slow download page
                browser_manager._page.goto(slow_url, wait_until='domcontentloaded', timeout=45000)
                
                # Handle countdown timer
                if handle_countdown_timer(browser_manager._page):
                    # Wait an additional 5 seconds as requested to ensure button is rendered
                    print("[INFO] Countdown finished. Waiting 5s for button to render...")
                    time.sleep(5)
                    
                    # Extract final download URL (Strictly "Download now")
                    final_url = extract_download_links_after_countdown(browser_manager._page)
                    
                    if final_url:
                        links['direct'].append(final_url)
                        debug_print(f"Successfully found 'Download now' link on slow server {i+1}")
                        # We found a valid link for this MD5, we can stop here for this book
                        break
                    else:
                        debug_print(f"Slow server {i+1} did not provide a 'Download now' button after countdown.")
                
            except Exception as e:
                debug_print(f"Failed to process slow download link {i+1}: {e}")
                continue
    
    # Mirror/IPFS fallbacks are kept only as a last resort if 'direct' is empty,
    # but the tool's main loop in annas_archive_tool.py will try other books first.
    if not links['direct']:
        debug_print("No 'Download now' links found for this book result.")
    
    return links
    