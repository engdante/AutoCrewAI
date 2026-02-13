"""

# Dynamic path setup for imports (works from both script/ and parent directory)
_script_dir = Path(__file__).parent.absolute()
_parent_dir = _script_dir.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
Anna's Archive Tool - File Converter
Contains methods for converting file formats and reading file content.
"""

import os
import re
import shutil
from typing import Optional

import sys
from pathlib import Path
# Import from other modules
try:
    from annas_config import debug_print
except ModuleNotFoundError:
    from script.annas_config import debug_print

def convert_mobi_to_txt(mobi_path: str, output_dir: str) -> Optional[str]:
    """Converts a MOBI file to a TXT file using pymupdf (fitz)."""
    debug_print(f"convert_mobi_to_txt: Starting conversion for: {mobi_path}")
    try:
        # Try to import fitz
        try:
            import fitz
        except ImportError:
            debug_print("pymupdf not installed, falling back to HTML extraction")
            print("[WARNING] pymupdf not installed, falling back to HTML extraction")
            return convert_mobi_fallback(mobi_path, output_dir)
        
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
        return convert_mobi_fallback(mobi_path, output_dir)

def convert_mobi_fallback(mobi_path: str, output_dir: str) -> Optional[str]:
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

        from bs4 import BeautifulSoup
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

def read_file_content(path: str, ext: str) -> str:
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
                        from bs4 import BeautifulSoup
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