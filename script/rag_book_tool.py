import os
import warnings
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from .rag_storage import RAGStorage

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
        "Returns the most relevant sections of the book as context. "
        "Use this for retrieving specific facts or summarizing chapters."
    )
    args_schema: Type[BaseModel] = AskBookInput
    storage: Optional[RAGStorage] = None

    def _init_storage(self):
        if self.storage is None:
            self.storage = RAGStorage()

    def _run(self, query: str, book_id: Optional[str] = None) -> str:
        try:
            self._init_storage()
            docs = self.storage.query(query, book_id=book_id, k=5)
            
            if not docs:
                return f"No relevant information found for '{query}' in the book(s)."

            # Format the context
            context = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "Unknown Source")
                page = doc.metadata.get("page", "N/A")
                content = doc.page_content.strip()
                context.append(f"--- Chunk {i+1} (Source: {source}, Page: {page}) ---\n{content}")

            return "\n\n".join(context)
        except Exception as e:
            return f"Error querying the book: {str(e)}"

# Note: Hybrid Search (BM25) integration can be added here once storage supports it.
# For now, it uses high-quality vector search.
