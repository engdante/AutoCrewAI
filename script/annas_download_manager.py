"""
Anna's Archive Tool - Download Manager
Handles downloading books, extracting download links, and file conversion.
"""

import os
import re
import shutil
import time
import logging
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# Import from other modules
from annas_config import logger, debug_print, IPFS_GATEWAYS
from annas_utils import random_delay, pause_for_input, verify_file_type
from annas_browser_manager import BrowserManager

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
    
    def get_download_links(self, book_url: str) -> Dict[str, List[str]]:
        """
        Extract download links from book detail page.
        
        Strategy: Click "Slow Download" button to get the actual download link.
        Anna's Archive has Fast Download (paid) and Slow Download (free).
        
        Returns dict with keys: 'direct', 'mirrors', 'ipfs'
        """
        debug_print(f"get_download_links: {book_url}")
        print(f"[INFO] Fetching book details: {book_url}")
        debug_print("Starting download links extraction")
        
        pause_for_input("Press ENTER to navigate to book detail page...")
        
        debug_print("Navigating to book page...")
        self.browser_manager._page.goto(book_url, wait_until='domcontentloaded')
        debug_print("Book page loaded")
        
        self.browser_manager.wait_for_cloudflare(self.browser_manager._page)
        random_delay(2, 3)
        
        content = self.browser_manager._page.content()
        debug_print(f"Page content length: {len(content)} characters")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        links = {
            'direct': [],      # Direct file links
            'mirrors': [],     # Mirror pages (libgen, z-lib, etc.)
            'ipfs': []         # IPFS links
        }
        
        # ============================================================
        # STRATEGY 1: Find and click "Slow Download" button
        # ============================================================
        debug_print("=== STRATEGY 1: Looking for Slow Download button ===")
        
        slow_download_selectors = [
            'a:has-text("Slow download")',
            'a:has-text("Slow Download")',
            'button:has-text("Slow download")',
            'button:has-text("Slow Download")',
            'a[href*="slow_download"]',
            'a[href*="slow-download"]',
            '.slow-download',
            '[data-testid="slow-download"]',
        ]
        
        slow_download_url = None
        
        for selector in slow_download_selectors:
            try:
                debug_print(f"Trying selector: {selector}")
                element = self.browser_manager._page.query_selector(selector)
                if element:
                    # Get the href before clicking
                    href = element.get_attribute('href')
                    debug_print(f"Found Slow Download element with href: {href}")
                    
                    if href:
                        # Make URL absolute if relative
                        if href.startswith('/'):
                            slow_download_url = f"{self.browser_manager.make_absolute_url('')}{href}"
                        else:
                            slow_download_url = href
                        
                        debug_print(f"Slow Download URL: {slow_download_url}")
                        print(f"[INFO] Found Slow Download link: {slow_download_url}")
                        
                        # Click the slow download button
                        debug_print("Clicking Slow Download button...")
                        pause_for_input("Press ENTER to click Slow Download button...")
                        
                        element.click()
                        random_delay(2, 3)
                        
                        # Wait for navigation or new content
                        try:
                            self.browser_manager._page.wait_for_load_state('networkidle', timeout=30000)
                        except Exception as e:
                            debug_print(f"wait_for_load_state after click: {e}")
                        
                        # Get the new page content
                        new_content = self.browser_manager._page.content()
                        
                        # ============================================================
                        # CHECK FOR COUNTDOWN TIMER
                        # ============================================================
                        countdown_el = self.browser_manager._page.query_selector('.js-partner-countdown')
                        if countdown_el:
                            debug_print("Found countdown timer on page")
                            countdown_text = countdown_el.text_content()
                            debug_print(f"Countdown text: {countdown_text}")
                            
                            # Extract wait seconds from countdown
                            try:
                                wait_seconds = int(countdown_text.strip())
                                if wait_seconds > 0:
                                    print(f"[INFO] Waiting {wait_seconds} seconds for countdown...")
                                    debug_print(f"Waiting for countdown: {wait_seconds} seconds")
                                    
                                    # Wait for countdown to finish and page to refresh
                                    # The page will auto-refresh when countdown reaches 0
                                    max_wait = wait_seconds + 15
                                    start_time = time.time()
                                    
                                    while time.time() - start_time < max_wait:
                                        try:
                                            # Try to get countdown value
                                            countdown_el = self.browser_manager._page.query_selector('.js-partner-countdown')
                                            if not countdown_el:
                                                debug_print("Countdown element disappeared - page likely refreshed")
                                                break
                                            
                                            remaining = countdown_el.text_content()
                                            debug_print(f"Countdown remaining: {remaining}")
                                            try:
                                                remaining_sec = int(remaining.strip())
                                                if remaining_sec <= 0:
                                                    debug_print("Countdown finished!")
                                                    break
                                            except:
                                                pass
                                            time.sleep(1)
                                        except Exception as e:
                                            debug_print(f"Exception during countdown wait (page likely refreshing): {e}")
                                            break
                                    
                                    # Wait for page to stabilize after countdown
                                    debug_print("Waiting for page to stabilize after countdown...")
                                    time.sleep(3)
                                    
                                    # Wait for navigation to complete (page refreshes with download link)
                                    try:
                                        self.browser_manager._page.wait_for_load_state('networkidle', timeout=30000)
                                    except Exception as e:
                                        debug_print(f"wait_for_load_state after countdown: {e}")
                                    
                                    # Get the refreshed page content
                                    new_content = self.browser_manager._page.content()
                                    debug_print(f"Page content after countdown: {len(new_content)} characters")
                            except Exception as countdown_e:
                                debug_print(f"Error handling countdown: {countdown_e}")
                        
                        new_soup = BeautifulSoup(new_content, 'html.parser')
                        
                        # ============================================================
                        # Look for download button/link after countdown
                        # The page shows a download button after countdown finishes
                        # ============================================================
                        debug_print("Looking for download button after countdown...")
                        
                        # Check if we're still on countdown page or if download is ready
                        countdown_check = self.browser_manager._page.query_selector('.js-partner-countdown')
                        if countdown_check:
                            debug_print("Still on countdown page - download not ready yet")
                        else:
                            debug_print("Countdown page finished - looking for download link")
                            
                            # Use Playwright to find elements (more reliable than BeautifulSoup for dynamic content)
                            try:
                                # Priority 1: Look for the main "Download now" button
                                download_now_button = self.browser_manager._page.query_selector('a:has-text("Download now")')
                                if download_now_button:
                                    href = download_now_button.get_attribute('href')
                                    if href and href.startswith('http') and self._is_valid_download_link(href):
                                        full_url = href
                                        debug_print(f"Found 'Download now' button: {full_url}")
                                        if full_url not in links['direct']:
                                            links['direct'].append(full_url)
                                
                                # Priority 2: Look for any link with download-related text
                                download_text_selectors = [
                                    'a:has-text("Download")',
                                    'a:has-text("download")',
                                    'a:has-text("📚")',
                                    'button:has-text("Download")',
                                    'button:has-text("download")',
                                ]
                                
                                for selector in download_text_selectors:
                                    try:
                                        elements = self.browser_manager._page.query_selector_all(selector)
                                        for el in elements:
                                            href = el.get_attribute('href')
                                            if not href:
                                                href = el.get_attribute('data-href')
                                            if href and href.startswith('http') and self._is_valid_download_link(href):
                                                full_url = href
                                                debug_print(f"Found download link with text: {full_url}")
                                                if full_url not in links['direct']:
                                                    links['direct'].append(full_url)
                                    except Exception as e:
                                        debug_print(f"Text selector {selector} failed: {e}")
                                
                                # Priority 3: Look for file extension links (but filter out navigation links)
                                extension_links = self.browser_manager._page.query_selector_all('a[href$=".pdf"], a[href$=".epub"], a[href$=".mobi"]')
                                for link in extension_links:
                                    href = link.get_attribute('href')
                                    if href and href.startswith('http') and self._is_valid_download_link(href):
                                        full_url = href
                                        debug_print(f"Found extension link: {full_url}")
                                        if full_url not in links['direct']:
                                            links['direct'].append(full_url)
                                
                                # Priority 4: Look for any link containing "download" but filter out bad ones
                                download_links = self.browser_manager._page.query_selector_all('a[href*="download"]')
                                for link in download_links:
                                    href = link.get_attribute('href')
                                    if href and href.startswith('http') and self._is_valid_download_link(href):
                                        full_url = href
                                        debug_print(f"Found download link: {full_url}")
                                        if full_url not in links['direct']:
                                            links['direct'].append(full_url)
                                
                                # Priority 5: Fallback - look for all links and filter
                                if not links['direct']:
                                    debug_print("Trying HTML content fallback...")
                                    for link in new_soup.find_all('a', href=True):
                                        href = link.get('href', '')
                                        if href and href.startswith('http') and self._is_valid_download_link(href):
                                            if any(href.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi']):
                                                full_url = href
                                                debug_print(f"Found HTML fallback download link: {full_url}")
                                                if full_url not in links['direct']:
                                                    links['direct'].append(full_url)
                            
                            except Exception as e:
                                debug_print(f"Error finding download links with Playwright: {e}")
                                # Fallback to BeautifulSoup method
                                debug_print("Falling back to BeautifulSoup method...")
                                
                                download_button_selectors = [
                                    'a[href*="/dyn/api/"]',
                                    'a[href*="download"]',
                                    'a.js-download-link',
                                    'button.js-download-link',
                                    'a[href$=".pdf"]',
                                    'a[href$=".epub"]',
                                    'a[href$=".mobi"]',
                                    '.download-link',
                                    '[data-download-link]',
                                    '#download-button',
                                    '.download-button',
                                    'button:has-text("Download")',
                                    'a:has-text("Download")',
                                    'button:has-text("download")',
                                    'a:has-text("download")',
                                    '[data-testid="download-button"]',
                                    'a.btn-download',
                                    'button.btn-download',
                                ]
                                
                                for sel in download_button_selectors:
                                    try:
                                        download_els = new_soup.select(sel)
                                        for el in download_els:
                                            href = el.get('href', '')
                                            if not href:
                                                href = el.get('data-href', '')
                                            if not href and el.name == 'button':
                                                parent_form = el.find_parent('form')
                                                if parent_form:
                                                    href = parent_form.get('action', '')
                                            if href and self._is_valid_download_link(href):
                                                full_url = self.browser_manager.make_absolute_url(href)
                                                debug_print(f"Found download link with selector '{sel}': {full_url}")
                                                if full_url not in links['direct']:
                                                    links['direct'].append(full_url)
                                    except Exception as e:
                                        debug_print(f"Selector {sel} failed: {e}")
                                
                                # Also look for the usual patterns with validation
                                for link in new_soup.find_all('a', href=True):
                                    href = link.get('href', '')
                                    if href and self._is_valid_download_link(href):
                                        if any(href.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi']):
                                            full_url = self.browser_manager.make_absolute_url(href)
                                            if full_url not in links['direct']:
                                                debug_print(f"Found direct download link: {full_url}")
                                                links['direct'].append(full_url)
                                        elif 'ipfs' in href.lower() or '/ipfs/' in href:
                                            full_url = self.browser_manager.make_absolute_url(href)
                                            if full_url not in links['ipfs']:
                                                debug_print(f"Found IPFS link: {full_url}")
                                                links['ipfs'].append(full_url)
                                        elif any(kw in link.get_text(strip=True).lower() for kw in ['download', 'get file']):
                                            full_url = self.browser_manager.make_absolute_url(href)
                                            if full_url.startswith('http') and full_url not in links['direct']:
                                                debug_print(f"Found download link: {full_url}")
                                                links['direct'].append(full_url)
                        
                        if any(links.values()):
                            debug_print(f"Successfully extracted links from Slow Download page")
                            break
                        
            except Exception as e:
                debug_print(f"Selector {selector} failed: {e}")
                continue
        
        # ============================================================
        # STRATEGY 2: If no slow download, look for mirrors
        # ============================================================
        if not any(links.values()):
            debug_print("=== STRATEGY 2: Looking for mirror links ===")
            
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
        
        debug_print(f"Links found: direct={len(links['direct'])}, mirrors={len(links['mirrors'])}, ipfs={len(links['ipfs'])}")
        print(f"[INFO] Found {len(links['direct'])} direct, {len(links['mirrors'])} mirrors, {len(links['ipfs'])} IPFS links")
        
        # Debug: Save page if no links found
        if not any(links.values()):
            debug_print("WARNING: No download links found!")
            print("[DEBUG] Page content saved to debug_book_page.html")
        
        return links
    
    def download_from_url(self, url: str, output_path: str, book_title: str = "Unknown") -> bool:
        """
        Download file from URL using direct HTTP request with browser session.

        Returns True if successful.
        """
        debug_print(f"download_from_url: Starting download")
        debug_print(f"  URL: {url}")
        debug_print(f"  Output path: {output_path}")
        debug_print(f"  Book title: {book_title}")
        
        print(f"[INFO] Attempting download from: {url[:80]}...")
        
        try:
            # Get browser cookies and headers to maintain session
            cookies = {c['name']: c['value'] for c in self.browser_manager.get_browser_context().cookies()}
            headers = {
                'User-Agent': self.browser_manager._page.evaluate('navigator.userAgent'),
                'Referer': url,
                'Accept': 'application/pdf,application/epub+zip,application/octet-stream,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
            
            debug_print("Downloading file with requests...")
            
            import requests
            
            # First, check if the URL is accessible
            head_response = requests.head(url, cookies=cookies, headers=headers, timeout=30, allow_redirects=True)
            if head_response.status_code != 200:
                debug_print(f"HEAD request failed: {head_response.status_code}")
                print(f"[WARNING] HEAD request failed: {head_response.status_code}")
                return False
            
            # Get the actual content type and content length
            content_type = head_response.headers.get('content-type', '').lower()
            content_length = head_response.headers.get('content-length', '0')
            
            debug_print(f"HEAD Response - Status: {head_response.status_code}, Content-Type: {content_type}, Content-Length: {content_length}")
            
            # If it's HTML, this might be a redirect or error page
            if 'text/html' in content_type:
                debug_print("HEAD Response is HTML, checking with GET request...")
                print(f"[WARNING] HEAD response is HTML, trying GET request...")
            
            # Make the actual GET request with streaming
            response = requests.get(url, cookies=cookies, headers=headers, stream=True, timeout=120)
            
            if response.status_code != 200:
                debug_print(f"Download failed: HTTP {response.status_code}")
                print(f"[WARNING] Download failed: HTTP {response.status_code}")
                return False
            
            # Check content type again
            content_type = response.headers.get('content-type', '').lower()
            debug_print(f"GET Response Content-Type: {content_type}")
            
            # If it's HTML, this is not a direct download
            if 'text/html' in content_type and 'pdf' not in url.lower() and 'epub' not in url.lower():
                debug_print("Response is HTML, not a file")
                print("[WARNING] Response is HTML, not a file")
                return False
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the file with progress indication
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            debug_print(f"Saving file to: {output_path} (Size: {total_size} bytes)")
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress indication
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if int(percent) % 10 == 0 and downloaded > 0:
                                print(f"[INFO] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='\r')
            
            # Print final progress
            if total_size > 0:
                print(f"[INFO] Download completed: 100% ({downloaded}/{total_size} bytes)")
            else:
                print(f"[INFO] Download completed: {downloaded} bytes")
            
            # Verify file was actually saved
            if not os.path.exists(output_path):
                debug_print("File was not saved")
                print("[ERROR] File was not saved")
                return False
            
            file_size = os.path.getsize(output_path)
            debug_print(f"DOWNLOAD_SUMMARY: book='{book_title}' url='{url[:60]}...' output_path='{output_path}' size={file_size} bytes")
            print(f"[INFO] Downloaded: {file_size} bytes")
            
            # Verify it's not an HTML file
            with open(output_path, 'rb') as f:
                header = f.read(1024)
            
            if b'<!DOCTYPE' in header or b'<html' in header.lower():
                debug_print("File is HTML, removing...")
                print("[WARNING] File is HTML, removing...")
                os.remove(output_path)
                return False
            
            debug_print("Download successful")
            return True
            
        except Exception as e:
            debug_print(f"Download failed with exception: {e}")
            print(f"[ERROR] Download failed: {e}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return False
    
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
            soup = BeautifulSoup(content, 'html.parser')
            
            # Save for debugging
            self.browser_manager.save_debug_page(content, "debug_mirror_page.html")
            
            # Look for direct download links
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
    
    def download_book(self, book_url: str, output_dir: str, preferred_ext: str = 'pdf', filename: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Download a book, trying multiple sources.

        Returns (file_path, extension) or (None, error_message).
        """
        debug_print(f"download_book: Starting download for book: {book_url}")
        
        # Get download links
        links = self.get_download_links(book_url)
        debug_print(f"Found {len(links['direct'])} direct, {len(links['mirrors'])} mirrors, {len(links['ipfs'])} IPFS links")
        
        # Determine preferred extension
        if preferred_ext not in ['pdf', 'epub', 'mobi']:
            preferred_ext = 'pdf'
        
        # Generate filename
        if filename:
            base_filename = filename
        else:
            base_filename = "book"
        
        # Try direct links first (PDF > EPUB > MOBI)
        priority_exts = ['pdf', 'epub', 'mobi']
        
        for ext in priority_exts:
            for link in links['direct']:
                if link.lower().endswith(f'.{ext}'):
                    output_path = os.path.join(output_dir, f"{base_filename}.{ext}")
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
                match = re.search(r'/ipfs/([a-zA-Z0-9]+)', ipfs_link)
                if match:
                    cid = match.group(1)
                    for gateway in IPFS_GATEWAYS:
                        ipfs_link = f"{gateway}{cid}"
                        output_path = os.path.join(output_dir, f"{base_filename}.{preferred_ext}")
                        if self.download_from_url(ipfs_link, output_path, "Unknown"):
                            return output_path, preferred_ext
            else:
                output_path = os.path.join(output_dir, f"{base_filename}.{preferred_ext}")
                if self.download_from_url(ipfs_link, output_path, "Unknown"):
                    return output_path, preferred_ext
        
        return None, "All download attempts failed"
    
    def convert_mobi_to_txt(self, mobi_path: str, output_dir: str) -> Optional[str]:
        """Converts a MOBI file to a TXT file using pymupdf (fitz)."""
        debug_print(f"convert_mobi_to_txt: Starting conversion for: {mobi_path}")
        try:
            # Try to import fitz
            try:
                import fitz
            except ImportError:
                debug_print("pymupdf not installed, falling back to HTML extraction")
                print("[WARNING] pymupdf not installed, falling back to HTML extraction")
                return self.convert_mobi_fallback(mobi_path, output_dir)
            
            doc = fitz.open(mobi_path)
            text_parts = []
            
            for page in doc:
                text_parts.append(page.get_text())
            
            full_text = "\n\n".join(text_parts)
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)
            full_text = full_text.strip()
            
            doc.close()
            
            output_txt_path = os.path.join(output_dir, os.path.splitext(os.path.basename(mobi_path))[0] + ".txt")
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            debug_print(f"Successfully converted {mobi_path} to TXT")
            print(f"[INFO] Successfully converted {mobi_path} to TXT")
            return output_txt_path
        except Exception as e:
            debug_print(f"Error converting with pymupdf: {e}")
            print(f"[ERROR] Error converting with pymupdf: {e}")
            return self.convert_mobi_fallback(mobi_path, output_dir)
    
    def convert_mobi_fallback(self, mobi_path: str, output_dir: str) -> Optional[str]:
        """Fallback method to convert MOBI to TXT using HTML extraction."""
        debug_print(f"convert_mobi_fallback: Starting for: {mobi_path}")
        try:
            # Try to import mobi
            try:
                import mobi
            except ImportError:
                debug_print("mobi library not installed")
                print("[ERROR] mobi library not installed")
                return None
                
            extraction_result = mobi.extract(mobi_path)
            temp_dir, html_file_path = extraction_result
            
            try:
                with open(html_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(html_file_path, "r", encoding="latin-1") as f:
                    content = f.read()

            soup = BeautifulSoup(content, "html.parser")
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            
            output_txt_path = os.path.join(output_dir, os.path.splitext(os.path.basename(mobi_path))[0] + ".txt")
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            shutil.rmtree(temp_dir)
            debug_print(f"Successfully converted {mobi_path} to TXT (fallback)")
            print(f"[INFO] Successfully converted {mobi_path} to TXT (fallback)")
            return output_txt_path
        except Exception as e:
            debug_print(f"Error converting MOBI to TXT (fallback): {e}")
            print(f"[ERROR] Error converting MOBI to TXT (fallback): {e}")
            return None
    
    def read_file_content(self, path: str, ext: str) -> str:
        """Extracts a snippet of text from the downloaded file."""
        debug_print(f"read_file_content: Reading file: {path}")
        if not os.path.exists(path):
            debug_print(f"File does not exist: {path}")
            return "File download failed or path incorrect."
            
        try:
            if ext == "pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(path)
                    total_pages = len(reader.pages)
                    text = reader.pages[0].extract_text() or ""
                    debug_print(f"Read PDF with {total_pages} pages")
                    return f"[PDF - {total_pages} pages]\n{text[:1000]}..."
                except ImportError:
                    debug_print("pypdf not installed")
                    return "[PDF]\nPDF reading requires pypdf library."
            elif ext == "epub":
                try:
                    import ebooklib
                    from ebooklib import epub
                    book = epub.read_epub(path)
                    for item in book.get_items():
                        if item.get_type() == ebooklib.ITEM_DOCUMENT:
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            text = soup.get_text()
                            debug_print("Read EPUB content")
                            return f"[EPUB]\n{text[:1000]}..."
                except ImportError:
                    debug_print("ebooklib not installed")
                    return "[EPUB]\nEPUB reading requires ebooklib library."
            elif ext == "mobi":
                debug_print("MOBI format - text extraction not supported")
                return "[MOBI]\nFile is in MOBI format. Text extraction not currently supported."
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(1000)
                    debug_print(f"Read text file: {len(content)} chars")
                    return content + "..."
        except Exception as e:
            debug_print(f"Error reading file: {e}")
            return f"Error reading file content: {str(e)}"