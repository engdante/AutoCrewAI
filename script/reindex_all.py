import os
import sys
from dotenv import load_dotenv

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

load_dotenv(os.path.join(project_root, ".env"))

try:
    from script.rag_storage import RAGStorage
    from script.annas_config import project_root
except ImportError:
    from rag_storage import RAGStorage
    from annas_config import project_root

def reindex_crew(crew_name):
    crew_path = os.path.join(project_root, "crews", crew_name)
    input_dir = os.path.join(crew_path, "input")
    rag_db_path = os.path.join(crew_path, "rag_db")
    
    if not os.path.exists(input_dir):
        print(f"[ERROR] Input directory not found: {input_dir}")
        return

    print(f"--- Re-indexing Crew: {crew_name} ---")
    print(f"Target RAG DB: {rag_db_path}")
    
    # Initialize Storage with new BGE-M3 model
    storage = RAGStorage(persist_directory=rag_db_path)
    
    files_found = False
    for file in os.listdir(input_dir):
        if file.lower().endswith(('.pdf', '.epub', '.txt')):
            files_found = True
            file_path = os.path.join(input_dir, file)
            book_id = os.path.splitext(file)[0].replace("_", " ")
            
            print(f"
[+] Found file: {file}")
            print(f"[+] Indexing as: {book_id}")
            
            success = storage.add_book(file_path, book_id)
            if success:
                print(f"[OK] Successfully indexed {book_id}")
            else:
                print(f"[FAIL] Could not index {book_id}")

    if not files_found:
        print(f"[!] No valid files found in {input_dir}")
    else:
        print(f"
--- Done! You can now use ask_rag.py ---")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Re-index files for a specific crew.")
    parser.add_argument("--crew", type=str, required=True, help="Name of the crew to re-index.")
    args = parser.parse_args()
    
    reindex_crew(args.crew)
