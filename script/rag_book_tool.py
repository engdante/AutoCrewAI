import os
import re
import warnings
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# Aggressively suppress Pydantic and other UserWarnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["PYTHONWARNINGS"] = "ignore"

try:
    from .rag_storage import RAGStorage
except (ImportError, ValueError):
    from rag_storage import RAGStorage

class AskBookInput(BaseModel):
    """Input schema for AskBookTool."""
    query: str = Field(..., description="The question you want to ask about the book.")
    book_id: Optional[str] = Field(None, description="The ID or title of the book to search in.")
    query_type: Optional[str] = Field(None, description="The type of query: 'SPECIFIC', 'BROAD', 'GRAPH', or 'MIXED'.")
    k: Optional[int] = Field(None, description="The number of relevant sections to retrieve.")
    analyze: bool = Field(True, description="Whether to analyze the retrieved context.")
    custom_prompt: Optional[str] = Field(None, description="A custom prompt for the LLM analysis.")

class AskBookTool(BaseTool):
    name: str = "ask_book_tool"
    description: str = (
        "Ask a question about a book that has been downloaded and indexed. "
        "Returns context and LLM analysis."
    )
    args_schema: Type[BaseModel] = AskBookInput
    storage: Optional[RAGStorage] = None
    llm: Optional[Any] = None
    _persist_directory: str = "crews/shared/rag_db"
    
    # Connection parameters
    ollama_host: Optional[str] = None
    ollama_port: Optional[str] = None
    ollama_model: Optional[str] = None

    def __init__(self, persist_directory: Optional[str] = None, ollama_host=None, ollama_port=None, ollama_model=None, **kwargs):
        super().__init__(**kwargs)
        if persist_directory:
            self._persist_directory = persist_directory
        self.ollama_host = ollama_host
        self.ollama_port = ollama_port
        self.ollama_model = ollama_model

    def _init_llm(self):
        if self.llm is None:
            try:
                from crewai import LLM
                import os
                
                model = self.ollama_model or os.getenv("OLLAMA_MODEL", "llama3")
                host = self.ollama_host or os.getenv("OLLAMA_SERVER", "localhost")
                port = self.ollama_port or os.getenv("OLLAMA_PORT", "11434")
                
                # Check for full base_url in env if not provided via params
                base_url = os.getenv("OLLAMA_BASE_URL")
                if not base_url or self.ollama_host or self.ollama_port:
                    base_url = f"http://{host}:{port}"
                
                self.llm = LLM(model=f"ollama/{model}", base_url=base_url)
            except Exception as e:
                print(f"Warning: Could not initialize LLM: {e}")

    def _init_storage(self):
        if self.storage is None:
            self._init_llm()
            self.storage = RAGStorage(persist_directory=self._persist_directory, llm=self.llm)

    def get_stats(self):
        """Public method to get RAG statistics."""
        self._init_storage()
        stats = {
            "type": "Hybrid RAG (Vector + Knowledge Graph + Summaries)",
            "persist_dir": self._persist_directory,
            "total_chunks": 0,
            "total_summaries": 0,
            "graph_nodes": 0,
            "graph_edges": 0,
            "indexed_books": [],
            "embedding_model": "Unknown",
            "vector_store": "ChromaDB",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        try:
            if self.storage.vector_store:
                coll = self.storage.vector_store._collection
                stats["total_chunks"] = coll.count()
                
                # Get unique book_ids efficiently if possible
                try:
                    results = coll.get(include=['metadatas'], limit=1000)
                    books = set()
                    for meta in results['metadatas']:
                        if 'book_id' in meta: books.add(meta['book_id'])
                    stats["indexed_books"] = list(books)
                except:
                    pass
                
                if hasattr(self.storage, 'embeddings'):
                    if hasattr(self.storage.embeddings, 'model_name'):
                        stats["embedding_model"] = self.storage.embeddings.model_name
                    else:
                        stats["embedding_model"] = str(type(self.storage.embeddings).__name__)

            if self.storage.summary_store:
                stats["total_summaries"] = self.storage.summary_store._collection.count()
                
            if self.storage.graph:
                stats["graph_nodes"] = self.storage.graph.number_of_nodes()
                stats["graph_edges"] = self.storage.graph.number_of_edges()
                
            if self.storage.text_splitter:
                stats["chunk_size"] = getattr(self.storage.text_splitter, "_chunk_size", 1000)
                stats["chunk_overlap"] = getattr(self.storage.text_splitter, "_chunk_overlap", 200)
                
        except Exception as e:
            stats["error"] = str(e)
        return stats

    def _classify_query(self, query: str) -> tuple[str, float]:
        if not self.llm: return "SPECIFIC", 1.0
        prompt = (
            "Classify this query: 'GRAPH', 'BROAD', 'SPECIFIC', 'MIXED'.\n"
            "Return JSON: {\"type\": \"...\", \"confidence\": 0.9}\n"
            f"Query: {query}"
        )
        try:
            import json
            response = self.llm.call(prompt)
            match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data.get("type", "SPECIFIC").upper(), data.get("confidence", 0.0)
        except: pass
        return "SPECIFIC", 0.5

    def _run(self, query: str, book_id: Optional[str] = None, query_type: Optional[str] = None, k: Optional[int] = None, analyze: bool = True, custom_prompt: Optional[str] = None) -> str:
        try:
            self._init_storage()
            rag_stats = self.get_stats()
            
            if not query_type or query_type.upper() not in ["SPECIFIC", "BROAD", "GRAPH", "MIXED"]:
                query_type, _ = self._classify_query(query)
            
            if k is None:
                k = {"GRAPH": 10, "BROAD": 15, "SPECIFIC": 25}.get(query_type, 20)
            
            docs = self.storage.query(query, book_id=book_id, k=k, query_type=query_type)
            if not docs: return "No information found."

            context_blocks = []
            sources = set()
            for i, doc in enumerate(docs):
                src = doc.metadata.get('source', 'Unknown')
                sources.add(os.path.basename(src))
                block = f"--- Block {i+1} ({doc.metadata.get('type', 'Chunk').upper()}) ---\n{doc.page_content.strip()}"
                context_blocks.append(block)
            full_context = "\n\n".join(context_blocks)
            
            analysis_output = ""
            if analyze and self.llm:
                p = f"{custom_prompt}\n\n" if custom_prompt else "Answer based on context:\n\n"
                p += f"Context:\n{full_context}\n\nQuestion: {query}"
                analysis_output = self.llm.call(p)

            res = [f"QUERY TYPE: {query_type}"]
            res.append("=" * 60)
            res.append("RAG TECHNICAL INFO:")
            res.append(f"  - System Type: {rag_stats['type']}")
            res.append(f"  - Embedding Model: {rag_stats['embedding_model']}")
            res.append(f"  - Database Path: {rag_stats['persist_dir']}")
            res.append(f"  - Indexed Chunks: {rag_stats['total_chunks']}")
            res.append(f"  - Summaries: {rag_stats['total_summaries']}")
            res.append(f"  - Knowledge Graph: {rag_stats['graph_nodes']} nodes, {rag_stats['graph_edges']} edges")
            res.append(f"  - Indexed Books: {', '.join(rag_stats['indexed_books'])}")
            res.append(f"  - Active Sources for this query: {', '.join(sources)}")
            res.append("=" * 60)
            res.append("RELEVANT CONTEXT:")
            res.append("-" * 30)
            res.append(full_context)
            res.append("=" * 60)
            if analyze:
                res.append("LLM ANALYSIS:")
                res.append("-" * 30)
                res.append(analysis_output or "Analysis failed.")
            
            return "\n\n".join(res)
        except Exception as e:
            return f"Error: {str(e)}"
