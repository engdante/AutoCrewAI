import os
import warnings
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding # Default fallback, should use real ones
from langchain_core.documents import Document

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

class RAGStorage:
    def __init__(self, persist_directory: str = "crews/shared/rag_db"):
        self.persist_directory = persist_directory
        # Use a real embedding model if possible. For local, we'll try to use SentenceTransformers if available
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception:
            print("Warning: HuggingFaceEmbeddings not available. Using fake embeddings (not recommended for production).")
            self.embeddings = DeterministicFakeEmbedding(size=384)
            
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="books_collection"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True,
        )

    def add_book(self, file_path: str, book_id: str):
        """Indexes a book into the vector store."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        print(f"Indexing book: {book_id} from {file_path}...")
        
        ext = os.path.splitext(file_path)[1].lower()
        documents = []
        
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif ext == ".epub":
                loader = UnstructuredEPubLoader(file_path)
                documents = loader.load()
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    documents = [Document(page_content=text, metadata={"source": file_path})]
        except Exception as e:
            print(f"Error loading document: {e}")
            return False

        # Add book_id to metadata
        for doc in documents:
            doc.metadata["book_id"] = book_id

        chunks = self.text_splitter.split_documents(documents)
        self.vector_store.add_documents(chunks)
        print(f"Successfully indexed {len(chunks)} chunks from {book_id}.")
        return True

    def query(self, query_text: str, book_id: Optional[str] = None, k: int = 5) -> List[Document]:
        """Queries the vector store for relevant chunks."""
        filter_dict = {"book_id": book_id} if book_id else None
        return self.vector_store.similarity_search(query_text, k=k, filter=filter_dict)

if __name__ == "__main__":
    # Quick test
    storage = RAGStorage()
    print("RAG Storage initialized.")
