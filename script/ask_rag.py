import os
import sys
import argparse
import warnings
from dotenv import load_dotenv

# Suppress Pydantic and other UserWarnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["PYTHONWARNINGS"] = "ignore"

# Add project root to path to allow imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, ".env"))

try:
    from script.rag_book_tool import AskBookTool
    from script.annas_config import project_root
except ImportError:
    from rag_book_tool import AskBookTool
    from annas_config import project_root

def main():
    parser = argparse.ArgumentParser(description="Query or inspect the RAG database.")
    parser.add_argument("query", type=str, nargs='?', help="The question to ask the RAG.")
    parser.add_argument("--crew", type=str, default="shared", help="The name of the crew.")
    parser.add_argument("--type", type=str, choices=["SPECIFIC", "BROAD", "GRAPH", "MIXED", "AUTO"], default="AUTO", 
                        help="The type of query to perform.")
    parser.add_argument("--k", type=int, default=None, help="Number of results to retrieve.")
    parser.add_argument("--book_id", type=str, default=None, help="Filter by specific book ID.")
    parser.add_argument("--prompt", type=str, default=None, help="Custom prompt for analysis.")
    parser.add_argument("--spec", action="store_true", help="Show only RAG technical specifications and exit.")
    parser.add_argument("--no-analyze", action="store_false", dest="analyze", help="Skip LLM analysis.")
    
    # Ollama connection overrides
    parser.add_argument("--ollama", type=str, default=None, help="Ollama server IP/host.")
    parser.add_argument("--port", type=str, default=None, help="Ollama server port.")
    parser.add_argument("--model", type=str, default=None, help="Ollama model name.")
    
    parser.set_defaults(analyze=True)

    args = parser.parse_args()

    # Determine RAG persist directory
    rag_db_path = os.path.join(project_root, "crews", args.crew, "rag_db")
    if not os.path.exists(rag_db_path):
        shared_path = os.path.join(project_root, "crews", "shared", "rag_db")
        if os.path.exists(shared_path):
            rag_db_path = shared_path
        else:
            if not args.spec:
                print(f"[ERROR] RAG DB not found for crew '{args.crew}'.")
                sys.exit(1)

    # Initialize tool with potential overrides
    tool = AskBookTool(
        persist_directory=rag_db_path,
        ollama_host=args.ollama,
        ollama_port=args.port,
        ollama_model=args.model
    )

    if args.spec:
        stats = tool.get_stats()
        print("\n" + "="*60)
        print(" RAG TECHNICAL SPECIFICATIONS")
        print("="*60)
        print(f" Crew Name:      {args.crew}")
        print(f" DB Location:    {stats['persist_dir']}")
        print(f" System Type:    {stats['type']}")
        print(f" Vector Store:   {stats.get('vector_store', 'ChromaDB')}")
        print(f" Embedding Mod:  {stats.get('embedding_model', 'Unknown')}")
        print("-" * 60)
        print(f" Indexed Chunks: {stats['total_chunks']}")
        print(f" Summaries:      {stats['total_summaries']}")
        print(f" Graph Nodes:    {stats['graph_nodes']}")
        print(f" Graph Edges:    {stats['graph_edges']}")
        print(f" Chunk Size:     {stats.get('chunk_size', 'N/A')}")
        print(f" Chunk Overlap:  {stats.get('chunk_overlap', 'N/A')}")
        print("-" * 60)
        
        # Connection info
        host = args.ollama or os.getenv("OLLAMA_SERVER", "localhost")
        port = args.port or os.getenv("OLLAMA_PORT", "11434")
        model = args.model or os.getenv("OLLAMA_MODEL", "llama3")
        print(f" LLM Host:       {host}")
        print(f" LLM Port:       {port}")
        print(f" LLM Model:      {model}")
        print("-" * 60)
        
        books = stats['indexed_books']
        if books:
            print(f" Indexed Books ({len(books)}):")
            for b in sorted(books):
                print(f"  - {b}")
        else:
            print(" Indexed Books:  None found in this collection")
            
        print("="*60 + "\n")
        return

    if not args.query:
        print("[ERROR] A query is required unless --spec is used.")
        parser.print_help()
        sys.exit(1)

    # Execute normal query
    q_type = args.type if args.type != "AUTO" else None
    result = tool._run(
        query=args.query, 
        book_id=args.book_id, 
        query_type=q_type, 
        k=args.k,
        analyze=args.analyze,
        custom_prompt=args.prompt
    )
    
    print("\n" + "#"*60)
    print(" RAG SYSTEM RESPONSE")
    print("#"*60 + "\n")
    print(result)
    print("\n" + "#"*60)

if __name__ == "__main__":
    main()
