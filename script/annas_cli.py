"""
Anna's Archive Tool - Command Line Interface
Handles command-line argument parsing and user interaction.
"""

import os
import sys
import argparse
import logging
from typing import Optional
from dotenv import load_dotenv, find_dotenv # Import dotenv

# Add parent directory to path if needed (for running from parent dir)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from our modules - try both import styles
try:
    # Try direct import first (when running from script/ directory)
    from annas_archive_tool import AnnasArchiveTool
    from annas_config import AnnasArchiveInput, debug_print, DEBUG_MODE, INTERACTIVE_MODE
    from tools_registry import get_tool_agent_tools # Import get_tool_agent_tools
except ModuleNotFoundError:
    # Fall back to script.module import (when running from parent directory)
    from script.annas_archive_tool import AnnasArchiveTool
    from script.annas_config import AnnasArchiveInput, debug_print, DEBUG_MODE, INTERACTIVE_MODE
    from script.tools_registry import get_tool_agent_tools # Import get_tool_agent_tools

# Package information (moved from __init__.py)
__version__ = "2.0.0"
__all__ = ["AnnasArchiveTool", "AnnasArchiveInput", "BookResult"]

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Anna's Archive Tool - Search and download books from Anna's Archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search and download a book
  python annas_cli.py "The Great Gatsby"
  
  # Download to specific directory
  python annas_cli.py "1984" --download-dir /path/to/downloads
  
  # Use crew-specific directory
  python annas_cli.py "Dune" --crew-name my_crew
  
  # Search only (no download)
  python annas_cli.py "Harry Potter" --search-only
  
  # Debug mode
  python annas_cli.py "Brave New World" --debug
  
  # Non-interactive mode
  python annas_cli.py "Animal Farm" --non-interactive
        """
    )
    
    parser.add_argument(
        "query",
        help="Book title and/or author to search for"
    )
    
    parser.add_argument(
        "--download-dir",
        help="Explicit download directory (overrides default)"
    )
    
    parser.add_argument(
        "--crew-name",
        help="Crew name for crew-specific directory"
    )
    
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Only search for books, don't download"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--browser",
        choices=['show', 'hide', 'headless'],
        default='headless',
        help="Browser visibility: 'show' (visible), 'hide' (hidden), 'headless' (no browser window)"
    )
    
    parser.add_argument(
        "--filename",
        help="Custom filename without extension (e.g., 'Harry_Potter_Book_4')"
    )
    
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of search results to return (default: 10)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"Anna's Archive Tool v{__version__}"
    )
    
    return parser.parse_args()

def main():
    """Main CLI entry point."""
    try:
        # Load environment variables from .env file
        load_dotenv(find_dotenv())
        
        args = parse_args()
        
        # Set debug mode
        if args.debug:
            global DEBUG_MODE
            DEBUG_MODE = True
            logging.basicConfig(level=logging.DEBUG)
            debug_print("Debug mode enabled")
        
        # Always run in non-interactive mode (no pauses)
        global INTERACTIVE_MODE
        INTERACTIVE_MODE = False
        
        debug_print(f"Starting CLI with args: {args}")
        print(f"[INFO] Anna's Archive Tool v{__version__} - Query: '{args.query}'")
        
        # --- Configure Ollama environment variables for LiteLLM ---
        ollama_server = os.getenv("OLLAMA_SERVER")
        ollama_port = os.getenv("OLLAMA_PORT")
        ollama_model = os.getenv("OLLAMA_MODEL")

        if ollama_server and ollama_port:
            ollama_api_base = f"http://{ollama_server}:{ollama_port}"
            os.environ["OLLAMA_API_BASE"] = ollama_api_base
            debug_print(f"Set OLLAMA_API_BASE to: {ollama_api_base}")
        elif os.getenv("OLLAMA_API_BASE"):
            debug_print(f"Using OLLAMA_API_BASE from environment: {os.getenv('OLLAMA_API_BASE')}")
        else:
            debug_print("OLLAMA_SERVER and OLLAMA_PORT or OLLAMA_API_BASE not found in .env. LiteLLM will use its defaults (localhost:11434).")

        if ollama_model:
            os.environ["OLLAMA_MODEL"] = ollama_model
            debug_print(f"Set OLLAMA_MODEL to: {ollama_model}")
        else:
            debug_print("OLLAMA_MODEL not found in .env. Using default (llama3).")
        # --- End Ollama config ---

        # Get tools with dynamic RAG persist_directory
        tools = get_tool_agent_tools(
            crew_name=args.crew_name,
            download_dir=args.download_dir,
            browser_mode=args.browser # Pass browser_mode if any tool needs it for initialization
        )

        # Find the AnnasArchiveTool from the list of tools
        annas_archive_tool = None
        for tool_instance in tools:
            if tool_instance.name == "annas_archive_tool":
                annas_archive_tool = tool_instance
                break
        
        if not annas_archive_tool:
            raise ValueError("AnnasArchiveTool not found in tools registry.")
        
        # Create input object
        input_data = AnnasArchiveInput(
            query=args.query,
            download_dir=args.download_dir,
            crew_name=args.crew_name,
            search_only=args.search_only,
            max_results=args.max_results
        )
        
        debug_print(f"Input data: {input_data}")
        
        # Run the tool
        result = annas_archive_tool._run(
            query=args.query,
            download_dir=args.download_dir,
            crew_name=args.crew_name,
            filename=args.filename,
            browser_mode=args.browser
        )
        
        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(result)
        print("="*60)
        
        # Exit with appropriate code
        if "Successfully downloaded" in result:
            sys.exit(0)
        elif "No books found" in result or "Could not find" in result:
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()