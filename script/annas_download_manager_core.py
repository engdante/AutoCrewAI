"""
Anna's Archive Tool - Download Manager Core
Contains core DownloadManager class and main downloading methods.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Import from other modules
try:
    from annas_config import debug_print
    from annas_utils import random_delay, pause_for_input, verify_file_type
    from annas_browser_manager import BrowserManager
except ModuleNotFoundError:
    from script.annas_config import debug_print
    from script.annas_utils import random_delay, pause_for_input, verify_file_type
    from script.annas_browser_manager import BrowserManager

class DownloadManager:
    """Handles book downloading and file operations."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
    
    def _is_valid_download_link(self, href: str) -> bool:
        """
        Validate if a href is a valid download link and not a navigation link.
        """
        if not href or not href.startswith('http'):
            return False
        
        # Skip navigation/account links
        skip_patterns = [
            '/account/', '/login', '/register', '/signup', '/auth/',
            '/faq', '/contact', '/donate', '/blog', '/search',
            '/md5/', '/isbn/', '/doi/', '/torrents/', '/datasets/'
        ]
        
        for pattern in skip_patterns:
            if pattern in href.lower():
                return False
        
        # Should contain file extension or download keyword
        has_file_ext = any(href.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi', '.zip', '.torrent'])
        has_download_keyword = any(kw in href.lower() for kw in ['download', 'zlib', 'getfile', 'partner'])
        
        return has_file_ext or has_download_keyword
    
    def download_from_url(self, url: str, output_path: str, book_title: str = "Unknown") -> bool:
        """
        Download file from URL using direct HTTP request or browser fallback.
        """
        debug_print(f"download_from_url: Starting download")
        debug_print(f"  URL: {url}")
        debug_print(f"  Output path: {output_path}")
        
        print(f"[INFO] Attempting download: {url[:80]}...")
        
        # 1. Try with requests first (faster and more reliable for large files)
        try:
            cookies = {c['name']: c['value'] for c in self.browser_manager.get_browser_context().cookies()}
            headers = {
                'User-Agent': self.browser_manager._page.evaluate('navigator.userAgent'),
                'Referer': url,
            }
            
            import requests
            response = requests.get(url, cookies=cookies, headers=headers, stream=True, timeout=120)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type or 'pdf' in url.lower() or 'epub' in url.lower():
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                        debug_print(f"Download successful via requests: {output_path}")
                        return True
        except Exception as e:
            debug_print(f"Requests download failed: {e}")

        # 2. Browser Fallback (handles complex redirects/JS-based downloads)
        try:
            debug_print("Attempting browser-based download fallback...")
            print("[INFO] Trying browser-based download...")
            
            page = self.browser_manager._page
            # Playwright download handler
            with page.expect_download(timeout=60000) as download_info:
                page.goto(url)
            
            download = download_info.value
            download.save_as(output_path)
            
            if os.path.exists(output_path):
                debug_print(f"Download successful via browser: {output_path}")
                print(f"[INFO] Download successful: {os.path.basename(output_path)}")
                return True
        except Exception as e:
            debug_print(f"Browser download failed: {e}")
            print(f"[ERROR] All download methods failed for this link.")
            
        return False
    
    def download_book(self, book_url: str, output_dir: str, preferred_ext: str = 'pdf', filename: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Download a book, trying multiple sources.

        Returns (file_path, extension) or (None, error_message).
        """
        debug_print(f"download_book: Starting download for book: {book_url}")
        
        # Get download links
        try:
            from annas_link_extractor import get_download_links
        except ModuleNotFoundError:
            from script.annas_link_extractor import get_download_links
        links = get_download_links(self.browser_manager, book_url)
        debug_print(f"Found {len(links['direct'])} direct, {len(links['mirrors'])} mirrors, {len(links['ipfs'])} IPFS links")
        
        # Determine preferred extension
        if preferred_ext not in ['pdf', 'epub', 'mobi']:
            preferred_ext = 'pdf'
        
        # Generate filename
        if filename:
            base_filename = filename
        else:
            base_filename = "book"
        
        # Try direct links first
        for link in links['direct']:
            # Determine extension from link or use preferred
            ext = preferred_ext
            for e in ['pdf', 'epub', 'mobi', 'azw3', 'txt']:
                if f".{e}" in link.lower():
                    ext = e
                    break
            
            output_path = os.path.join(output_dir, f"{base_filename}.{ext}")
            debug_print(f"Attempting direct download: {link[:80]}...")
            if self.download_from_url(link, output_path, "Unknown"):
                return output_path, ext
        
        # Try mirrors
        for mirror_url in links['mirrors']:
            for ext in priority_exts:
                output_path = os.path.join(output_dir, f"{base_filename}.{ext}")
                if self.try_mirror_download(mirror_url, output_path, "Unknown"):
                    return output_path, ext
        
        # Try IPFS as last resort
        for ipfs_link in links['ipfs']:
            # Convert to public gateway if needed
            if 'localhost' in ipfs_link or '127.0.0.1' in ipfs_link:
                import re
                match = re.search(r'/ipfs/([a-zA-Z0-9]+)', ipfs_link)
                if match:
                    try:
                        from annas_config import IPFS_GATEWAYS
                    except ImportError:
                        from script.annas_config import IPFS_GATEWAYS
                    cid = match.group(1)
                    for gateway in IPFS_GATEWAYS:
                        full_ipfs_link = f"{gateway}{cid}"
                        output_path = os.path.join(output_dir, f"{base_filename}.{preferred_ext}")
                        if self.download_from_url(full_ipfs_link, output_path, "Unknown"):
                            return output_path, preferred_ext
            else:
                output_path = os.path.join(output_dir, f"{base_filename}.{preferred_ext}")
                if self.download_from_url(ipfs_link, output_path, "Unknown"):
                    return output_path, preferred_ext
        
        return None, "All download attempts failed"
    
    def try_mirror_download(self, mirror_url: str, output_path: str, book_title: str = "Unknown") -> bool:
        """
        Try to download from a mirror site (libgen, z-lib, etc.).
        """
        debug_print(f"try_mirror_download: {mirror_url}")
        print(f"[INFO] Trying mirror: {mirror_url[:80]}...")
        
        # Ensure URL is absolute
        mirror_url = self.browser_manager.make_absolute_url(mirror_url)
        
        # Skip onion/Tor links - they won't work without Tor
        if '.onion' in mirror_url.lower():
            debug_print(f"Skipping Tor link: {mirror_url}")
            print(f"[WARNING] Skipping Tor link (requires Tor browser)")
            return False
            
        # Filter problematic domains that cause navigation errors
        problematic_domains = [
            'z-lib.gd', 'z-lib.io', 'z-lib.is', 'z-lib.id', 'zlib.is', 'zlib.gd',
            'singlelogin.re', 'singlelogin.me', 'singlelogin.org'
        ]
        for domain in problematic_domains:
            if domain in mirror_url.lower():
                debug_print(f"Skipping problematic domain: {domain}")
                print(f"[WARNING] Skipping problematic domain {domain}")
                return False
        
        try:
            pause_for_input("Press ENTER to navigate to mirror page...")
            self.browser_manager._page.goto(mirror_url, wait_until='domcontentloaded')
            random_delay(2, 3)
            
            content = self.browser_manager._page.content()
            
            # Look for direct download links
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            download_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Skip onion/Tor links
                if '.onion' in href.lower():
                    continue
                    
                # Skip problematic domains
                skip_link = False
                for domain in problematic_domains:
                    if domain in href.lower():
                        skip_link = True
                        break
                if skip_link:
                    continue
                
                # Direct file links (but not from onion domains)
                if any(href.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi']):
                    full_url = self.browser_manager.make_absolute_url(href)
                    if full_url not in download_links:
                        download_links.append(full_url)
                        debug_print(f"Found direct file link on mirror: {full_url[:80]}...")
                
                # Links with download-related text (but not from onion domains)
                elif any(kw in text for kw in ['download', 'get', 'download now', 'get file', 'download file']):
                    full_url = self.browser_manager.make_absolute_url(href)
                    if full_url.startswith('http') and full_url not in download_links:
                        # Skip onion links even with download text
                        if '.onion' not in full_url.lower():
                            download_links.append(full_url)
                            debug_print(f"Found download text link on mirror: {full_url[:80]}...")
            
            # Try each download link
            for link in download_links[:5]:  # Try first 5
                debug_print(f"Attempting download from mirror link: {link[:80]}...")
                if self.download_from_url(link, output_path, book_title):
                    return True
            
            return False
            
        except Exception as e:
            debug_print(f"Mirror download failed: {e}")
            print(f"[WARNING] Mirror download failed: {e}")
            return False