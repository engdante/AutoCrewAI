import os
import re
import sys
import argparse
import requests
import warnings
import mobi
import tempfile
import shutil
from typing import Type, Optional, ClassVar, List
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

# Suppress Pydantic V2 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')

# Define project root
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(script_dir)

# For reading files
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    ebooklib = None

class AnnasArchiveInput(BaseModel):
    """Input schema for AnnasArchiveTool."""
    query: str = Field(..., description="The name and author of the book to search for.")

class AnnasArchiveTool(BaseTool):
    name: str = "annas_archive_tool"
    description: str = (
        "Search for books on Anna's Archive, download them, and read their content. "
        "Input: book title and optionally the author. "
        "Returns the path of the downloaded file and a summary or snippet of its content."
    )
    args_schema: Type[BaseModel] = AnnasArchiveInput

    IPFS_GATEWAYS: ClassVar[List[str]] = [
        "https://ipfs.io/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/",
        "https://gateway.pinata.cloud/ipfs/",
        "https://dweb.link/ipfs/"
    ]

    def _convert_to_public_gateway(self, url: str) -> str:
        """Converts a local IPFS URL or generic IPFS hash to a public gateway URL."""
        # Check for localhost/127.0.0.1 IPFS links
        if "localhost" in url or "127.0.0.1" in url:
            # Extract the IPFS hash (CID)
            # Pattern: .../ipfs/<hash>...
            match = re.search(r'/ipfs/([a-zA-Z0-9]+)', url)
            if match:
                cid = match.group(1)
                # Use the first gateway (ipfs.io) as default, others as fallback?
                # For now just picking one, or we could rotate.
                # Let's return the CID and handle rotation in the caller if needed, 
                # or just return a constructed URL with cloudflare (usually fast).
                return f"https://cloudflare-ipfs.com/ipfs/{cid}?filename=book.pdf"
        
        return url

    def _convert_mobi_to_txt(self, mobi_path: str, output_dir: str) -> Optional[str]:
        """Converts a MOBI/EPUB file to a TXT file using pymupdf (fitz)."""
        try:
            if not fitz:
                print(f"[WARNING] pymupdf not installed, falling back to HTML extraction")
                return self._convert_mobi_fallback(mobi_path, output_dir)
            
            # Use fitz to open the MOBI/EPUB file and extract text
            doc = fitz.open(mobi_path)
            text_parts = []
            
            # Extract text from all pages
            for page in doc:
                text_parts.append(page.get_text())
            
            # Combine and clean the text
            full_text = "\n\n".join(text_parts)
            
            # Clean up the text - remove excessive whitespace
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)
            full_text = full_text.strip()
            
            doc.close()
            
            # Save the extracted text to a .txt file
            output_txt_path = os.path.join(output_dir, os.path.splitext(os.path.basename(mobi_path))[0] + ".txt")
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            
            print(f"[INFO] Successfully converted {mobi_path} to TXT using pymupdf")
            return output_txt_path
        except Exception as e:
            print(f"[ERROR] Error converting with pymupdf: {e}")
            print(f"[INFO] Trying fallback method...")
            return self._convert_mobi_fallback(mobi_path, output_dir)
    
    def _convert_mobi_fallback(self, mobi_path: str, output_dir: str) -> Optional[str]:
        """Fallback method to convert MOBI to TXT using HTML extraction."""
        try:
            # Extract MOBI, which returns a tuple (temp_dir, html_file_path)
            extraction_result = mobi.extract(mobi_path)
            temp_dir, html_file_path = extraction_result
            
            # Read the HTML file content carefully
            try:
                with open(html_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Fallback to latin-1 if utf-8 fails
                with open(html_file_path, "r", encoding="latin-1") as f:
                    content = f.read()

            # Parse the HTML content and extract text with better formatting
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text with better separation
            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up excessive newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            
            # Save the extracted text to a .txt file
            output_txt_path = os.path.join(output_dir, os.path.splitext(os.path.basename(mobi_path))[0] + ".txt")
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)
            print(f"[INFO] Successfully converted {mobi_path} to TXT using fallback method")
            return output_txt_path
        except Exception as e:
            print(f"[ERROR] Error converting MOBI to TXT (fallback): {e}")
            return None

    def _run(self, query: str, download_dir: Optional[str] = None, crew_name: Optional[str] = None) -> str:
        try:
            # 1. Determine download path
            input_dir = self._resolve_download_dir(download_dir, crew_name)
            os.makedirs(input_dir, exist_ok=True)

            # 2. Search
            search_url = f"https://bg.annas-archive.li/search?q={query.replace(' ', '+')}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(search_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                return f"Error searching Anna's Archive: HTTP {resp.status_code}"

            # 3. Parse results to find first md5 link
            md5_match = re.search(r'href=["\'](/md5/[0-9a-f]{32})["\']', resp.text)
            if not md5_match:
                return f"No books found for query: {query}"
            
            md5_path = md5_match.group(1)
            detail_url = f"https://bg.annas-archive.li{md5_path}"
            
            # 4. Visit detail page to find download mirrors, prioritizing PDF
            detail_resp = requests.get(detail_url, headers=headers, timeout=30)
            if detail_resp.status_code != 200:
                return f"Error fetching book details from {detail_url}"

            # Priority mirror: PDF first, then EPUB, then MOBI as last resort
            # Extract all potential download links
            ext_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', detail_resp.text)
            
            download_url = None
            preferred_ext = "pdf"  # Default preference
            
            # Extract mirror section specifically for better URL extraction
            mirror_section = re.search(r'<h4>Mirrors:</h4>(.*?)(?=</div>|<h4>)', detail_resp.text, re.DOTALL)
            mirror_links = []
            if mirror_section:
                mirror_text = mirror_section.group(1)
                mirror_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', mirror_text)
                # Add mirror links to the front of the list for priority
                ext_links = mirror_links + ext_links

            # First pass: Look for direct file links with preferred extensions
            print(f"[INFO] Searching for download links among {len(ext_links)} candidates...")
            
            # Prioritize non-IPFS mirrors due to connectivity issues
            for link in ext_links:
                # Skip IPFS links if possible (connectivity issues)
                if any(skip in link.lower() for skip in ['ipfs', 'cloudflare-ipfs', 'gateway.ipfs']):
                    continue
                    
                # Check for direct file extensions
                if link.lower().endswith('.pdf'):
                    download_url = link
                    preferred_ext = "pdf"
                    print(f"[INFO] Found direct PDF link: {download_url}")
                    break
                elif link.lower().endswith('.epub'):
                    download_url = link
                    preferred_ext = "epub"
                    print(f"[INFO] Found direct EPUB link: {download_url}")
                    break
                elif link.lower().endswith('.mobi'):
                    # Only use MOBI if no other options
                    if not download_url:
                        download_url = link
                        preferred_ext = "mobi"
                        print(f"[INFO] Found direct MOBI link: {download_url}")

            # Second pass: Try libgen.li and library.lol with more robust patterns
            if not download_url:
                print(f"[INFO] No direct file links found, trying mirror pages...")
                
                for link in ext_links:
                    if "libgen.li" in link:
                        try:
                            lib_resp = requests.get(link, headers=headers, timeout=30)
                            # Extract all file links from the page
                            file_links = re.findall(r'href=["\'](https?://[^"\']*\.(pdf|epub|mobi))["\']', lib_resp.text, re.IGNORECASE)
                            for file_link, ext in file_links:
                                download_url = file_link
                                preferred_ext = ext.lower()
                                print(f"[INFO] Found {ext.upper()} link from libgen.li: {download_url}")
                                break
                        except Exception as e:
                            print(f"[WARNING] Error accessing libgen.li page: {e}")
                        if download_url:
                            break
                    
                    elif "library.lol" in link:
                        try:
                            lol_resp = requests.get(link, headers=headers, timeout=30)
                            file_links = re.findall(r'href=["\'](https?://[^"\']*\.(pdf|epub|mobi))["\']', lol_resp.text, re.IGNORECASE)
                            for file_link, ext in file_links:
                                download_url = file_link
                                preferred_ext = ext.lower()
                                print(f"[INFO] Found {ext.upper()} link from library.lol: {download_url}")
                                break
                        except Exception as e:
                            print(f"[WARNING] Error accessing library.lol page: {e}")
                        if download_url:
                            break

            # Third pass: Fallback to IPFS if no other options
            if not download_url:
                print(f"[INFO] No direct mirrors found, trying IPFS as last resort...")
                for link in ext_links:
                    if any(ipfs in link.lower() for ipfs in ['ipfs', 'cloudflare-ipfs']):
                        download_url = link
                        preferred_ext = "epub"  # Most IPFS links are EPUB
                        print(f"[INFO] Using IPFS link: {download_url}")
                        break

            if not download_url:
                return f"Found the book but couldn't identify a reliable download mirror on {detail_url}. Please try manual download."

            # 5. Extract filename and initial extension guess, favoring PDF
            base_filename = query.replace(" ", "_").replace("/", "_").replace("\\", "_")[:50]
            
            # Check for format on the detail page, giving preference to PDF
            fmt_match = re.search(r'([a-z0-9]+)\s*,\s*[\d.]+\s*[MKBG]B', detail_resp.text, re.IGNORECASE)
            if fmt_match:
                guessed_ext = fmt_match.group(1).lower()
                if guessed_ext == "pdf":
                    initial_ext = "pdf"
                    preferred_ext = "pdf"
                else:
                    initial_ext = guessed_ext
            else:
                initial_ext = "pdf" # Default to pdf if no format info
                preferred_ext = "pdf"

            # Try each link until we get a valid book file
            valid_download = False
            final_download_url = None
            
            # Build list of URLs to try: prioritized URL first, then all ext_links
            raw_urls = [download_url] + [link for link in ext_links if link != download_url]
            urls_to_try = []

            for url in raw_urls:
                if not url: continue
                
                # Check for localhost/127.0.0.1 links (usually local IPFS gateways from libgen)
                if "localhost" in url or "127.0.0.1" in url:
                    # Extract the IPFS hash (CID)
                    # Pattern: .../ipfs/<hash>...
                    match = re.search(r'/ipfs/([a-zA-Z0-9]+)', url)
                    if match:
                        cid = match.group(1)
                        print(f"[INFO] Detected local IPFS link. Expanding to public gateways for CID: {cid}")
                        # Add all public gateways
                        for gateway in self.IPFS_GATEWAYS:
                            urls_to_try.append(f"{gateway}{cid}?filename={base_filename}.{initial_ext}")
                    else:
                        # Can't parse CID, just add as is
                        urls_to_try.append(url)
                else:
                    urls_to_try.append(url)
            
            for attempt_url in urls_to_try:
                print(f"[INFO] Attempting to download from: {attempt_url}")
                local_path = os.path.join(input_dir, f"{base_filename}.{initial_ext}")
                
                try:
                    # Download with stream
                    dl_resp = requests.get(attempt_url, headers=headers, stream=True, timeout=60)
                    
                    if dl_resp.status_code != 200:
                        print(f"[WARNING] Failed to download from {attempt_url}. HTTP {dl_resp.status_code}")
                        continue
                    
                    # Check Content-Type
                    content_type = dl_resp.headers.get('Content-Type', '').lower()
                    print(f"[INFO] Content-Type: {content_type}")
                    
                    if 'text/html' in content_type:
                        print(f"[WARNING] URL returned HTML instead of book file. Trying next link...")
                        # Clean up the invalid file if partially downloaded
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except OSError:
                                pass
                        continue
                    
                    # Download the file
                    with open(local_path, "wb") as f:
                        for chunk in dl_resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # Check file size - reject if too small (HTML pages are usually small)
                    file_size = os.path.getsize(local_path)
                    if file_size < 50000:  # Less than 50KB is likely an HTML page
                        print(f"[WARNING] Downloaded file is too small ({file_size} bytes). Likely an HTML page. Trying next link...")
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                        continue
                    
                    # Verify file type by checking header
                    with open(local_path, "rb") as f:
                        header = f.read(1024)
                    
                    # Check if it's actually an HTML file
                    if header.startswith(b'<!DOCTYPE') or header.startswith(b'<html') or b'<html' in header.lower():
                        print(f"[WARNING] Downloaded file appears to be HTML. Trying next link...")
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                        continue
                    
                    # If we got here, we have a valid book file
                    valid_download = True
                    final_download_url = attempt_url
                    print(f"[INFO] Successfully downloaded valid book file ({file_size} bytes)")
                    break
                    
                except Exception as e:
                    print(f"[WARNING] Error downloading from {attempt_url}: {e}")
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                    continue
            
            if not valid_download:
                return f"Failed to download a valid book file. All links returned HTML or invalid files. Please try manual download from {detail_url}."

            # 7. Post-download extension verification and renaming
            final_path, real_ext = self._verify_and_rename(local_path, initial_ext)

            # 8. Handle MOBI conversion if it's a MOBI file
            path_for_rag = final_path
            if real_ext == "mobi":
                print(f"[INFO] Detected MOBI file '{final_path}'. Converting to TXT for indexing...")
                converted_txt_path = self._convert_mobi_to_txt(final_path, input_dir)
                if converted_txt_path:
                    # Remove the original MOBI file to save space
                    try:
                        os.remove(final_path)
                    except OSError as e:
                        print(f"[WARNING] Could not remove original MOBI file: {e}")
                    path_for_rag = converted_txt_path
                    real_ext = "txt"
                    final_path = converted_txt_path
                else:
                    return f"Successfully downloaded '{query}' but failed to convert MOBI to TXT for indexing."

            # 9. Reading logic (Short snippet)
            content_snippet = self._read_file(final_path, real_ext)
            
            # 10. RAG Indexing (Auto-index after download)
            try:
                try:
                    from .rag_storage import RAGStorage
                except (ImportError, ValueError):
                    from rag_storage import RAGStorage
                    
                storage = RAGStorage()
                storage.add_book(path_for_rag, book_id=query)
                rag_status = "\n[RAG] Book indexed successfully for querying."
            except Exception as e:
                rag_status = f"\n[RAG] Failed to index book: {e}"

            return f"Successfully downloaded '{query}' to '{final_path}' (Format: {real_ext.upper()}).\n\nContent Preview:\n{content_snippet}{rag_status}"

        except Exception as e:
            return f"Error executing AnnasArchiveTool: {str(e)}"

    def _resolve_download_dir(self, download_dir: Optional[str], crew_name: Optional[str]) -> str:
        if download_dir:
            path = os.path.abspath(download_dir)
            print(f"Using explicit download directory: {path}")
            return path
        
        # Determine the actual project root (parent of 'script' directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # If we have a crew name, use its dedicated input folder
        if crew_name:
            path = os.path.abspath(os.path.join(project_root, "crews", crew_name, "input"))
            print(f"Using crew-specific input directory: {path}")
            return path
            
        # Use CREW_OUTPUT_DIR environment variable to find the corresponding input folder
        env_output_dir = os.environ.get("CREW_OUTPUT_DIR")
        if env_output_dir:
            # If output dir is crews/Name/output, then input dir is crews/Name/input
            crew_base_dir = os.path.dirname(os.path.abspath(env_output_dir))
            path = os.path.join(crew_base_dir, "input")
            print(f"Using environment-derived input directory: {path}")
            return os.path.abspath(path)
        
        # Final fallback to a global input directory in the project root
        path = os.path.abspath(os.path.join(PROJECT_ROOT, "input"))
        print(f"Using default project input directory: {path}")
        return path

    def _verify_and_rename(self, path: str, initial_ext: str) -> tuple[str, str]:
        """Verifies file type using magic bytes and renames if necessary."""
        if not os.path.exists(path):
            return path, initial_ext
            
        with open(path, "rb") as f:
            header = f.read(1024)
        
        real_ext = initial_ext
        if header.startswith(b"%PDF"):
            real_ext = "pdf"
        elif header.startswith(b"PK\x03\x04"):
            # Could be EPUB or other Zip-based format
            if b"mimetypeapplication/epub+zip" in header:
                real_ext = "epub"
            else:
                # Basic EPUB check failed, but PK is usually EPUB for books
                real_ext = "epub" 
        elif b"BOOKMOBI" in header:
            real_ext = "mobi"
        elif header.startswith(b"\xef\xbb\xbf") or all(32 <= b <= 126 or b in [9, 10, 13] for b in header[:100]):
            real_ext = "txt"

        if real_ext != initial_ext:
            new_path = os.path.splitext(path)[0] + f".{real_ext}"
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(path, new_path)
                return new_path, real_ext
            except Exception as e:
                print(f"Warning: Could not rename file: {e}")
                return path, real_ext
        
        return path, real_ext

    def _read_file(self, path: str, ext: str) -> str:
        """Extracts a snippet of text from the downloaded file."""
        if not os.path.exists(path):
            return "File download failed or path incorrect."
            
        try:
            if ext == "pdf" and PdfReader:
                reader = PdfReader(path)
                total_pages = len(reader.pages)
                text = reader.pages[0].extract_text() or ""
                return f"[PDF - {total_pages} pages]\n{text[:1000]}..."
            elif ext == "epub" and ebooklib:
                book = epub.read_epub(path)
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text = soup.get_text()
                        return f"[EPUB]\n{text[:1000]}..."
            elif ext == "mobi":
                return "[MOBI]\nFile is in MOBI format. Text extraction not currently supported. Please convert to EPUB or PDF for analysis."
            else:
                # For txt or other files
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(1000) + "..."
        except Exception as e:
            return f"Error reading file content: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Anna's Archive Tool - Search and download books.")
    parser.add_argument("query", nargs="?", help="The book title and author to search for.")
    parser.add_argument("--download-dir", help="Explicit directory to download the file to.")
    parser.add_argument("--crew", help="Crew name to use for determining the download path (crews/{crew}/input).")
    
    args = parser.parse_args()
    
    if not args.query:
        parser.print_help()
        sys.exit(0)
        
    tool = AnnasArchiveTool()
    result = tool._run(query=args.query, download_dir=args.download_dir, crew_name=args.crew)
    print(result)

if __name__ == "__main__":
    main()