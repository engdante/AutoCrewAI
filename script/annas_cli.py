"""
Anna's Archive Tool - Command Line Interface
Handles command-line argument parsing and user interaction.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Import from our modules
from annas_archive_tool import AnnasArchiveTool
from annas_config import AnnasArchiveInput, debug_print, DEBUG_MODE, INTERACTIVE_MODE

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
        
        # Create tool instance
        tool = AnnasArchiveTool()
        
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
        result = tool._run(
            query=args.query,
            download_dir=args.download_dir,
            crew_name=args.crew_name
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