import os
import re
import sys
import argparse
import requests
import warnings
from typing import Type, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# Suppress Pydantic V2 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')

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
            
            # 4. Visit detail page to find download mirrors
            detail_resp = requests.get(detail_url, headers=headers, timeout=30)
            if detail_resp.status_code != 200:
                return f"Error fetching book details from {detail_url}"

            # Priority mirror: Libgen (for ease of automation)
            ext_links = re.findall(r'href=["\'](https?://(?:libgen\.li|library\.lol|gateway\.ipfs|cloudflare-ipfs)[^"\']+)["\']', detail_resp.text)
            
            download_url = None
            for link in ext_links:
                if "libgen.li" in link:
                    lib_resp = requests.get(link, headers=headers, timeout=30)
                    direct_match = re.search(r'href=["\'](get\.php[^"\']+)["\']', lib_resp.text)
                    if direct_match:
                        base = "/".join(link.split("/")[:3])
                        download_url = f"{base}/{direct_match.group(1)}"
                        break
                elif "library.lol" in link:
                    lol_resp = requests.get(link, headers=headers, timeout=30)
                    direct_match = re.search(r'href=["\'](https?://[^"\']+/main/[^"\']+)["\']', lol_resp.text)
                    if direct_match:
                        download_url = direct_match.group(1)
                        break
            
            if not download_url and ext_links:
                download_url = ext_links[0]

            if not download_url:
                return f"Found the book but couldn't identify a reliable download mirror on {detail_url}. Please try manual download."

            # 5. Extract filename and initial extension guess
            base_filename = query.replace(" ", "_").replace("/", "_").replace("\\", "_")[:50]
            fmt_match = re.search(r'([a-z0-9]+)\s*,\s*[\d.]+\s*[MKBG]B', detail_resp.text, re.IGNORECASE)
            initial_ext = fmt_match.group(1).lower() if fmt_match else "pdf"
            if initial_ext not in ["pdf", "epub", "mobi", "txt"]:
                initial_ext = "pdf"
            
            local_path = os.path.join(input_dir, f"{base_filename}.{initial_ext}")

            # 6. Download
            dl_resp = requests.get(download_url, headers=headers, stream=True, timeout=60)
            if dl_resp.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in dl_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                return f"Failed to download file from {download_url}. HTTP {dl_resp.status_code}"

            # 7. Post-download extension verification and renaming
            final_path, real_ext = self._verify_and_rename(local_path, initial_ext)

            # 8. Reading logic (Short snippet)
            content_snippet = self._read_file(final_path, real_ext)
            
            return f"Successfully downloaded '{query}' to '{final_path}' (Format: {real_ext.upper()}).\n\nContent Preview:\n{content_snippet}"

        except Exception as e:
            return f"Error executing AnnasArchiveTool: {str(e)}"

    def _resolve_download_dir(self, download_dir: Optional[str], crew_name: Optional[str]) -> str:
        if download_dir:
            return os.path.abspath(download_dir)
        
        # Try to find project root by looking for 'crews' folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = script_dir
        while project_root and not os.path.exists(os.path.join(project_root, "crews")):
            parent = os.path.dirname(project_root)
            if parent == project_root: # Reached root of FS
                break
            project_root = parent
            
        if crew_name:
            path = os.path.join(project_root, "crews", crew_name, "input")
            return os.path.abspath(path)
            
        # Default fallback
        output_dir = os.environ.get("CREW_OUTPUT_DIR")
        if output_dir:
            return os.path.abspath(os.path.join(os.path.dirname(output_dir), "input"))
        
        return os.path.abspath(os.path.join(project_root, "input"))

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
