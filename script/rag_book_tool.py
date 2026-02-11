import os
import re
import warnings
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
try:
    from .rag_storage import RAGStorage
except (ImportError, ValueError):
    from rag_storage import RAGStorage

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

class AskBookInput(BaseModel):
    """Input schema for AskBookTool."""
    query: str = Field(..., description="The question you want to ask about the book.")
    book_id: Optional[str] = Field(None, description="The ID or title of the book to search in. If not provided, searches all indexed books.")

class AskBookTool(BaseTool):
    name: str = "ask_book_tool"
    description: str = (
        "Ask a question about a book that has been downloaded and indexed. "
        "Returns the most relevant sections, summaries, and narrative spreads. "
        "Automatically adaptive: handles both broad story-wide questions and specific fact retrieval."
    )
    args_schema: Type[BaseModel] = AskBookInput
    storage: Optional[RAGStorage] = None
    llm: Optional[any] = None

    def _init_llm(self):
        if self.llm is None:
            try:
                from crewai import LLM
                import os
                model = os.getenv("OLLAMA_MODEL", "llama3")
                base_url = os.getenv("OLLAMA_BASE_URL") or f"http://{os.getenv('OLLAMA_SERVER', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
                self.llm = LLM(model=f"ollama/{model}", base_url=base_url)
            except Exception as e:
                print(f"Warning: Could not initialize LLM for AskBookTool: {e}")

    def _init_storage(self):
        if self.storage is None:
            self._init_llm()
            self.storage = RAGStorage(llm=self.llm)

    def _classify_query(self, query: str) -> tuple[str, float]:
        """Classifies the query as BROAD, SPECIFIC, or MIXED."""
        if not self.llm:
            return "SPECIFIC", 1.0
            
        prompt = (
            "Classify this query as 'BROAD' (needs full story context/themes), "
            "'SPECIFIC' (needs precise facts/events), or 'MIXED'. "
            "Return ONLY a JSON object: {\"type\": \"BROAD\"|\"SPECIFIC\"|\"MIXED\", \"confidence\": 0-1}\n"
            f"Query: {query}"
        )
        try:
            import json
            response = self.llm.call(prompt)
            print(f"[DEBUG] Raw LLM Response: {response}") # Debug print
            
            # 1. Clean Markdown code blocks
            clean_response = response.replace("```json", "").replace("```", "").strip()
            
            # 2. Extract first JSON object
            match = re.search(r'\{[^{}]*\}', clean_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    print(f"[DEBUG] Parsed Data: {data}") # Debug print
                    q_type = data.get("type", "SPECIFIC").upper()
                    conf = data.get("confidence", 0.0)
                    if conf < 0.7:
                        return "SPECIFIC", conf
                    return q_type, conf
                except json.JSONDecodeError:
                    pass
            
            print("[DEBUG] No valid JSON found in response")
        except Exception as e:
            print(f"Error classifying query: {e}")
        
        return "SPECIFIC", 0.5

    def _run(self, query: str, book_id: Optional[str] = None) -> str:
        try:
            self._init_storage()
            
            # 1. Classify Query
            query_type, confidence = self._classify_query(query)
            print(f"[RAG] Query classified as: {query_type} (Confidence: {confidence:.2f})")
            
            # 2. Determine k and context strategy
            k_map = {
                "BROAD": 15,
                "SPECIFIC": 25,
                "MIXED": 30
            }
            k = k_map.get(query_type, 20)
            
            # 3. Retrieve
            docs = self.storage.query(query, book_id=book_id, k=k, query_type=query_type)
            
            if not docs:
                return f"No relevant information found for '{query}' in the book(s)."

            # 4. Format and Token Budgeting
            context_blocks = []
            total_chars = 0
            max_chars = 15000 # Approx 4000 tokens as a safety budget
            
            for i, doc in enumerate(docs):
                header = f"--- Block {i+1} ({doc.metadata.get('type', 'Chunk').upper()}) ---"
                source = f"Source: {doc.metadata.get('source', 'Unknown')}"
                section = f"Section: {doc.metadata.get('section_index', 'N/A')}"
                content = doc.page_content.strip()
                
                block = f"{header}\n{source} | {section}\n{content}"
                
                if total_chars + len(block) > max_chars:
                    context_blocks.append(f"[Context truncated due to token budget]")
                    break
                    
                context_blocks.append(block)
                total_chars += len(block)

            intro = f"Query Type: {query_type}\n{'='*20}\n"
            return intro + "\n\n".join(context_blocks)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error querying the book: {str(e)}"

# Note: Hybrid Search (BM25) integration can be added here once storage supports it.
# For now, it uses high-quality vector search.
