"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - Main Tool Class
Refactored to use modular components for better maintainability.
"""

import os
import sys
import re
from pathlib import Path
import argparse
import logging
from typing import Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# Import from our modules
try:
    from annas_config import BookResult, debug_print, project_root
except ModuleNotFoundError:
    from script.annas_config import BookResult, debug_print, project_root
try:
    from annas_utils import resolve_download_dir, verify_file_type
except ModuleNotFoundError:
    from script.annas_utils import resolve_download_dir, verify_file_type
try:
    from annas_browser_manager import BrowserManager
except ModuleNotFoundError:
    from script.annas_browser_manager import BrowserManager
try:
    from annas_book_search import BookSearcher
except ModuleNotFoundError:
    from script.annas_book_search import BookSearcher
try:
    from annas_download_manager import DownloadManager
except ModuleNotFoundError:
    from script.annas_download_manager import DownloadManager
try:
    from annas_file_converter import read_file_content
except ModuleNotFoundError:
    from script.annas_file_converter import read_file_content

class AnnasArchiveInput(BaseModel):
    """Input schema for AnnasArchiveTool."""
    query: str = Field(..., description="The name and author of the book to search for.")

class AnnasArchiveTool(BaseTool):
    """
    Search for books on Anna's Archive, download them, and read their content.
    
    Uses Playwright for reliable Cloudflare bypass.
    Integrates with crewAI and supports RAG indexing.
    """
    
    name: str = "annas_archive_tool"
    description: str = (
        "Search for books on Anna's Archive, download them, and read their content. "
        "Uses Playwright for reliable Cloudflare bypass. "
        "Returns book content and supports RAG indexing."
    )
    args_schema: type[BaseModel] = AnnasArchiveInput
    
    # Non-Pydantic fields for internal use
    _browser_manager: Optional[BrowserManager] = None
    _book_searcher: Optional[BookSearcher] = None
    _download_manager: Optional[DownloadManager] = None
    _default_browser_mode: str = 'show'
    _default_crew_name: Optional[str] = None
    
    def __init__(self, browser_mode: str = 'show', crew_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        # Initialize managers on-demand (lazy initialization)
        self._browser_manager = None
        self._book_searcher = None
        self._download_manager = None
        self._default_browser_mode = browser_mode
        self._default_crew_name = crew_name
        
        # Set class variables for dynamic URLs
        self.__class__.BASE_URL = ""
        self.__class__.SEARCH_URL = ""
        self.__class__._working_domain = None
        
        # Ensure we don't trigger Pydantic validation errors
        # by avoiding setting attributes that aren't in the model
        self._initialized = True
    
    @property
    def browser_manager(self):
        """Lazy initialization of browser manager."""
        if self._browser_manager is None:
            self._browser_manager = BrowserManager()
        return self._browser_manager
    
    @property
    def book_searcher(self):
        """Lazy initialization of book searcher."""
        if self._book_searcher is None:
            self._book_searcher = BookSearcher(self.browser_manager)
        return self._book_searcher
    
    @property
    def download_manager(self):
        """Lazy initialization of download manager."""
        if self._download_manager is None:
            self._download_manager = DownloadManager(self.browser_manager)
        return self._download_manager

    def _find_working_domain(self) -> Optional[str]:
        """Find a working Anna's Archive domain by trying each one."""
        return self.browser_manager.find_working_domain()

    def _run(self, query: str, download_dir: Optional[str] = None, crew_name: Optional[str] = None, filename: Optional[str] = None, browser_mode: Optional[str] = None) -> str:
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
        # Prioritize arguments, then defaults
        browser_mode = browser_mode or self._default_browser_mode
        crew_name = crew_name or self._default_crew_name
        
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
            headless = (browser_mode == 'headless')
            
            # 2. Determine download path
            input_dir = resolve_download_dir(download_dir, crew_name)
            os.makedirs(input_dir, exist_ok=True)
            debug_print(f"Download directory created/verified: {input_dir}")

            # --- Early Check for existing downloaded book ---
            # Try to infer the base filename for the check
            check_base_filename = filename if filename else self._generate_filename(query)
            existing_file_path = None
            
            # 1. Exact filename check
            for ext in ['pdf', 'epub', 'mobi', 'txt', 'azw3']:
                potential_path = os.path.join(input_dir, f"{check_base_filename}.{ext}")
                if os.path.exists(potential_path):
                    existing_file_path = potential_path
                    break
            
            # 2. Fuzzy check: if any PDF/EPUB exists in the directory that might be this book
            if not existing_file_path:
                query_words = set(re.sub(r'[^\w\s]', '', query.lower()).split())
                for f in os.listdir(input_dir):
                    if f.lower().endswith(('.pdf', '.epub')):
                        f_words = set(re.sub(r'[^\w\s]', '', f.lower()).split())
                        # If more than 50% of query words are in the filename, it's likely the same book
                        if query_words and len(query_words & f_words) / len(query_words) > 0.5:
                            existing_file_path = os.path.join(input_dir, f)
                            debug_print(f"Fuzzy match found: {f}")
                            break
            
            if existing_file_path:
                debug_print(f"Book '{query}' found at: {existing_file_path}")
                print(f"[INFO] Book '{query}' already downloaded as {os.path.basename(existing_file_path)}. Skipping search.")
                
                # Optionally ensure it's indexed for RAG
                rag_status = ""
                try:
                    from rag_storage import RAGStorage
                    rag_db_path = ""
                    if crew_name:
                        rag_db_path = os.path.join(project_root, "crews", crew_name, "rag_db")
                    elif download_dir:
                        rag_db_path = os.path.join(input_dir, "rag_db") # Use input_dir directly for download_dir case
                    else:
                        rag_db_path = os.path.join(project_root, "crews", "shared", "rag_db")
                    
                    storage = RAGStorage(persist_directory=rag_db_path)
                    storage.add_book(existing_file_path, book_id=query) # Use query as book_id for consistency
                    rag_status = "\n[RAG] Book confirmed indexed for querying."
                    debug_print("RAG indexing confirmed for existing book")
                except Exception as e:
                    rag_status = f"\n[RAG] Failed to confirm indexing for existing book: {e}"
                    debug_print(f"RAG indexing confirmation failed: {e}")

                content_snippet = read_file_content(existing_file_path, os.path.splitext(existing_file_path)[1].lstrip('.'))
                
                return (
                    f"Book '{query}' already exists at '{existing_file_path}'\n"
                    f"Format: {os.path.splitext(existing_file_path)[1].lstrip('.').upper()}, Size: {os.path.getsize(existing_file_path):,} bytes\n\n"
                    f"Content Preview:\n{content_snippet}{rag_status}"
                )
            # --- End early check for existing book ---

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
            
            results = self.book_searcher.search_books(query, max_results=10, headless=headless)
            
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
            content_snippet = read_file_content(final_path, real_ext)
            
            # 8. RAG Indexing
            rag_status = ""
            try:
                try:
                    from rag_storage import RAGStorage
                except (ImportError, ValueError):
                    from script.rag_storage import RAGStorage
                
                # Determine RAG persist directory dynamically
                rag_db_path = ""
                if crew_name:
                    rag_db_path = os.path.join(project_root, "crews", crew_name, "rag_db")
                    print(f"[INFO] Using crew-specific RAG DB: {rag_db_path}")
                elif download_dir:
                    rag_db_path = os.path.join(download_dir, "rag_db")
                    print(f"[INFO] Using download_dir-specific RAG DB: {rag_db_path}")
                else:
                    rag_db_path = os.path.join(project_root, "crews", "shared", "rag_db")
                    print(f"[INFO] Using shared RAG DB: {rag_db_path}")

                storage = RAGStorage(persist_directory=rag_db_path)
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
        try:
            from annas_utils import score_book_relevance
        except ModuleNotFoundError:
            from script.annas_utils import score_book_relevance
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