"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - Browser Manager
Handles Playwright browser initialization, domain finding, and Cloudflare bypass.
"""

import os
import time
import random
import logging
from typing import Optional
from bs4 import BeautifulSoup

import sys
from pathlib import Path
# Import from config
try:
    from annas_config import logger, debug_print, DOMAINS, BASE_URL, SEARCH_URL, _working_domain, INTERACTIVE_MODE
except ModuleNotFoundError:
    from script.annas_config import logger, debug_print, DOMAINS, BASE_URL, SEARCH_URL, _working_domain, INTERACTIVE_MODE
try:
    from annas_utils import random_delay, pause_for_input
except ModuleNotFoundError:
    from script.annas_utils import random_delay, pause_for_input

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define dummy types for type hints when Playwright is not installed
    Page = None
    Browser = None
    BrowserContext = None

class BrowserManager:
    """Manages Playwright browser instance and related operations."""
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install it with:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )
    
    def find_working_domain(self) -> Optional[str]:
        """Find a working Anna's Archive domain by trying each one."""
        if _working_domain:
            return _working_domain
        
        debug_print("find_working_domain: Starting domain search")
        print("[INFO] Finding working Anna's Archive domain...")
        
        import requests
        for domain in DOMAINS:
            try:
                debug_print(f"Trying domain: {domain}")
                # Try a quick HEAD request to check if domain is accessible
                resp = requests.head(domain, timeout=10, allow_redirects=True)
                debug_print(f"Domain {domain} response: {resp.status_code}")
                if resp.status_code < 400:
                    print(f"[INFO] Found working domain: {domain}")
                    return domain
            except Exception as e:
                debug_print(f"Domain {domain} not accessible: {e}")
                print(f"[DEBUG] Domain {domain} not accessible: {e}")
                continue
        
        # If all fail, return first domain anyway (Playwright might still work)
        print("[WARNING] Could not verify any domain, using first one...")
        return DOMAINS[0]
    
    def init_browser(self, headless: bool = False) -> None:
        """Initialize Playwright browser instance."""
        debug_print(f"init_browser: Starting with headless={headless}")
        
        # If already initialized with different headless mode, close and re-init
        if self._browser is not None:
            # We can't easily check current headless mode from the object, 
            # so we'll store it if we need to be perfect, but for now we just
            # assume if it's already there and we are called again, we should check.
            # However, usually we just want to avoid re-initializing if possible.
            # To fix the 'headless' not working, we'll ensure we set it.
            return

        debug_print("Creating new Playwright instance")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        self._context = self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        # Add random delay to appear more human-like
        self._context.set_default_timeout(60000)  # 60 seconds timeout
        self._page = self._context.new_page()
        debug_print("Playwright browser initialized successfully")
        print("[INFO] Playwright browser initialized")
    
    def close_browser(self) -> None:
        """Close Playwright browser instance."""
        debug_print("close_browser: Closing browser")
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        debug_print("Playwright browser closed")
        print("[INFO] Playwright browser closed")
    
    def wait_for_cloudflare(self, page: Page, timeout: int = 30) -> bool:
        """Wait for Cloudflare challenge to complete. Captures screenshot if stuck."""
        debug_print(f"wait_for_cloudflare: Starting with timeout={timeout}s")
        print("[INFO] Checking for Cloudflare/DDoS protection...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for Cloudflare challenge elements
            is_blocked = page.evaluate('''() => {
                const text = document.body.innerText.toLowerCase();
                return text.includes('cloudflare') || 
                       text.includes('checking your browser') || 
                       text.includes('ddos protection') ||
                       text.includes('verify you are human') ||
                       !!document.querySelector('#challenge-running, .cf-challenge-running, #turnstile-wrapper');
            }''')
            
            if not is_blocked:
                debug_print("Cloudflare challenge not detected or passed")
                return True
            
            # If we are in interactive mode and have waited a bit, ask for help
            elapsed = time.time() - start_time
            if INTERACTIVE_MODE and elapsed > 10:
                print(f"\n[ALERT] Cloudflare challenge detected! Please check the browser.")
                pause_for_input("Solve the captcha in the browser and then press ENTER...")
                return True
                
            time.sleep(2)
        
        debug_print("Cloudflare challenge timeout")
        print("[WARNING] Could not verify Cloudflare passage.")
        return False
    
    def get_page_content(self, page: Page) -> str:
        """Get page content with fallback methods."""
        content = None
        try:
            debug_print("Getting page content directly...")
            content = page.content()
            debug_print(f"Got page content: {len(content)} characters")
        except Exception as e:
            debug_print(f"Failed to get content directly: {e}")
            # Try with evaluate
            try:
                debug_print("Trying with page.evaluate...")
                content = page.evaluate('() => document.documentElement.outerHTML')
                debug_print(f"Got page content via evaluate: {len(content)} characters")
            except Exception as e2:
                debug_print(f"Page.evaluate also failed: {e2}")
        
        if not content:
            debug_print("Failed to get page content")
            print("[ERROR] Failed to get page content")
            return ""
        
        return content
    
    def make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL."""
        if not url:
            return url
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('//'):
            return f"https:{url}"
        if url.startswith('/'):
            return f"{BASE_URL}{url}"
        return url
    
    def get_browser_context(self):
        """Get the browser context for external use."""
        return self._context
    
    def get_browser_page(self):
        """Get the browser page for external use."""
        return self._page