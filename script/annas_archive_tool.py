"""
Anna's Archive Tool - Main Tool Class
Refactored to use modular components for better maintainability.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Import from our modules
from annas_config import AnnasArchiveInput, BookResult, debug_print
from annas_utils import resolve_download_dir, verify_file_type
from annas_browser_manager import BrowserManager
from annas_book_search import BookSearcher
from annas_download_manager import DownloadManager

class AnnasArchiveTool:
    """
    Search for books on Anna's Archive, download them, and read their content.
    
    Uses Playwright for reliable Cloudflare bypass.
    Integrates with crewAI and supports RAG indexing.
    """
    
    def __init__(self, **kwargs):
        # Initialize managers
        self.browser_manager = BrowserManager()
        self.book_searcher = BookSearcher(self.browser_manager)
        self.download_manager = DownloadManager(self.browser_manager)
        
        # Set class variables for dynamic URLs
        self.__class__.BASE_URL = ""
        self.__class__.SEARCH_URL = ""
        self.__class__._working_domain = None

    def _find_working_domain(self) -> Optional[str]:
        """Find a working Anna's Archive domain by trying each one."""
        return self.browser_manager.find_working_domain()

    def _run(self, query: str, download_dir: Optional[str] = None, crew_name: Optional[str] = None, filename: Optional[str] = None, browser_mode: str = 'show') -> str:
        """
        Main execution method.

        Args:
            query: Book title and/or author to search for
            download_dir: Optional explicit download directory
            crew_name: Optional crew name for crew-specific directory
            filename: Optional custom filename without extension
            browser_mode: Browser visibility mode ('show', 'hide', 'headless')

        Returns:
            Result message with file path and content preview
        """
        debug_print("="*60)
        debug_print("_run: Starting main execution")
        debug_print(f"  query: '{query}'")
        debug_print(f"  download_dir: {download_dir}")
        debug_print(f"  crew_name: {crew_name}")
        debug_print(f"  filename: {filename}")
        debug_print(f"  browser_mode: {browser_mode}")
        debug_print("="*60)
        
        try:
            # 1. Configure browser mode
            if browser_mode == 'headless':
                self.browser_manager.set_headless(True)
            elif browser_mode == 'hide':
                self.browser_manager.set_headless(False)
            # 'show' mode uses default settings
            
            # 2. Determine download path
            input_dir = resolve_download_dir(download_dir, crew_name)
            os.makedirs(input_dir, exist_ok=True)
            debug_print(f"Download directory created/verified: {input_dir}")

            # 3. Find working domain and set URLs
            working_domain = self._find_working_domain()
            if not working_domain:
                debug_print("Could not find working domain")
                return "Could not find a working Anna's Archive domain. Please check your internet connection."
            
            self.__class__.BASE_URL = working_domain
            self.__class__.SEARCH_URL = f"{working_domain}/search?q={{query}}"
            debug_print(f"BASE_URL set to: {working_domain}")

            # 4. Search for books
            print(f"\n{'='*60}")
            print(f"[INFO] Searching for: {query}")
            print(f"[INFO] Using domain: {working_domain}")
            print(f"[INFO] Browser mode: {browser_mode}")
            print(f"{'='*60}\n")
            
            results = self.book_searcher.search_books(query, max_results=5)
            
            if not results:
                debug_print("No books found")
                return f"No books found for query: {query}"
            
            # 5. Score and sort results by relevance
            sorted_results = self.book_searcher.score_and_sort_results(results, query)
            
            # 6. Try to download best matching result
            book = sorted_results[0]
            best_score = self._calculate_relevance_score(book.title, query)
            debug_print(f"Best match: '{book.title}' with score {best_score:.1f}")
            print(f"[INFO] Best match: '{book.title}' (score: {best_score:.0f})")
            
            # Warn if score is low
            if best_score < 50:
                print(f"[WARNING] Low relevance score ({best_score:.0f}). The book might not be an exact match.")
            
            file_path, ext_or_error = self._download_book_with_fallbacks(book, input_dir, filename)
            
            if not file_path:
                # Try next best results
                for book in sorted_results[1:3]:
                    debug_print(f"Trying alternative: {book.title}")
                    print(f"[INFO] Trying alternative: '{book.title}'")
                    file_path, ext_or_error = self._download_book_with_fallbacks(book, input_dir, filename)
                    if file_path:
                        break
            
            if not file_path:
                debug_print("All download attempts failed")
                self.browser_manager.close_browser()
                return f"Failed to download book. {ext_or_error}"

            # 5. Verify file type
            debug_print(f"Verifying file type for: {file_path}")
            final_path, real_ext = verify_file_type(file_path, ext_or_error)
            
            # 6. Handle MOBI conversion
            path_for_rag = final_path
            if real_ext == "mobi":
                debug_print("Converting MOBI to TXT...")
                print(f"[INFO] Converting MOBI to TXT...")
                converted_txt_path = self.download_manager.convert_mobi_to_txt(final_path, input_dir)
                if converted_txt_path:
                    try:
                        os.remove(final_path)
                    except OSError as e:
                        debug_print(f"Could not remove original MOBI file: {e}")
                        print(f"[WARNING] Could not remove original MOBI file: {e}")
                    path_for_rag = converted_txt_path
                    real_ext = "txt"
                    final_path = converted_txt_path
                else:
                    self.browser_manager.close_browser()
                    return f"Successfully downloaded '{query}' but failed to convert MOBI to TXT."

            # 7. Read content snippet
            content_snippet = self.download_manager.read_file_content(final_path, real_ext)
            
            # 8. RAG Indexing
            rag_status = ""
            try:
                try:
                    from rag_storage import RAGStorage
                except (ImportError, ValueError):
                    from rag_storage import RAGStorage
                    
                storage = RAGStorage()
                storage.add_book(path_for_rag, book_id=query)
                rag_status = "\n[RAG] Book indexed successfully for querying."
                debug_print("RAG indexing successful")
            except Exception as e:
                rag_status = f"\n[RAG] Failed to index book: {e}"
                debug_print(f"RAG indexing failed: {e}")

            # 9. Close browser
            self.browser_manager.close_browser()
            
            file_size = os.path.getsize(final_path)
            debug_print("="*60)
            debug_print("_run: Execution completed successfully")
            debug_print(f"  Final path: {final_path}")
            debug_print(f"  File size: {file_size} bytes")
            debug_print("="*60)
            
            return (
                f"Successfully downloaded '{book.title}' to '{final_path}'\n"
                f"Format: {real_ext.upper()}, Size: {file_size:,} bytes\n\n"
                f"Content Preview:\n{content_snippet}{rag_status}"
            )

        except Exception as e:
            debug_print(f"Exception in _run: {e}")
            import traceback
            debug_print(traceback.format_exc())
            self.browser_manager.close_browser()
            return f"Error executing AnnasArchiveTool: {str(e)}"
    
    def _calculate_relevance_score(self, book_title: str, query: str) -> float:
        """Calculate relevance score for a book title."""
        from annas_utils import score_book_relevance
        return score_book_relevance(book_title, query)
    
    def _download_book_with_fallbacks(self, book: BookResult, input_dir: str, filename: Optional[str] = None) -> tuple[Optional[str], str]:
        """Download a book with fallback options."""
        # Determine preferred extension
        preferred_ext = book.format.lower() if book.format else 'pdf'
        if preferred_ext not in ['pdf', 'epub', 'mobi']:
            preferred_ext = 'pdf'
        
        # Generate filename
        if filename:
            base_filename = filename
        else:
            base_filename = self._generate_filename(book.title)
        
        # Try direct download first
        result = self.download_manager.download_book(book.url, input_dir, preferred_ext, base_filename)
        if result[0]:
            return result
        
        # If direct download fails, try with different extensions
        for ext in ['pdf', 'epub', 'mobi']:
            if ext != preferred_ext:
                result = self.download_manager.download_book(book.url, input_dir, ext, base_filename)
                if result[0]:
                    return result
        
        return None, "All download attempts failed"
    
    def _generate_filename(self, title: str) -> str:
        """Generate a safe filename from book title."""
        import re
        base_filename = re.sub(r'[^\w\s-]', '', title)[:50].strip()
        return re.sub(r'[-\s]+', '_', base_filename)