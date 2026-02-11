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
    def __init__(self, persist_directory: str = "crews/shared/rag_db", llm=None):
        self.persist_directory = persist_directory
        # Use a real embedding model if possible
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            except Exception:
                print("Warning: HuggingFaceEmbeddings not available. Using fake embeddings.")
                self.embeddings = DeterministicFakeEmbedding(size=384)
            
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="books_collection"
        )
        self.summary_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="summaries_collection"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True,
        )
        self.llm = llm

    def add_book(self, file_path: str, book_id: str):
        """Indexes a book into the vector store and generates hierarchical summaries."""
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

        # Add metadata and token counts
        full_text = ""
        for i, doc in enumerate(documents):
            doc.metadata["book_id"] = book_id
            doc.metadata["type"] = "chunk"
            doc.metadata["chunk_index"] = i
            full_text += doc.page_content + " "

        # Generate summaries if book is long enough
        if len(full_text) > 5000:
            self.generate_hierarchical_summaries(full_text, book_id, file_path)

        chunks = self.text_splitter.split_documents(documents)
        # Enrich chunks with character positions
        current_pos = 0
        for chunk in chunks:
            chunk.metadata["start_char"] = current_pos
            chunk.metadata["end_char"] = current_pos + len(chunk.page_content)
            current_pos += len(chunk.page_content)

        self.vector_store.add_documents(chunks)
        print(f"Successfully indexed {len(chunks)} chunks from {book_id}.")
        return True

    def generate_hierarchical_summaries(self, text: str, book_id: str, source_path: str):
        """Generates section-level and book-level summaries."""
        if not self.llm:
            print("No LLM provided for summarization. Skipping.")
            return

        print(f"Generating hierarchical summaries for {book_id}...")
        
        # Split into sections (approx 50k chars each)
        section_size = 50000
        sections = [text[i:i + section_size] for i in range(0, len(text), section_size)]
        
        # Limit sections for very long books
        if len(sections) > 20:
            sections = sections[:20] 

        section_summaries = []
        for i, section in enumerate(sections):
            prompt = f"Summarize this section of the book (approx. 300 words). Focus on key plot points and characters:\n\n{section[:10000]}"
            try:
                summary = self.llm.call(prompt) # Assuming crewai.LLM.call or similar
                summary_doc = Document(
                    page_content=summary,
                    metadata={
                        "book_id": book_id,
                        "type": "chapter_summary",
                        "section_index": i,
                        "source": source_path
                    }
                )
                section_summaries.append(summary_doc)
            except Exception as e:
                print(f"Error generating section summary {i}: {e}")

        if section_summaries:
            self.summary_store.add_documents(section_summaries)
            
            # Master summary
            combined_summaries = "\n\n".join([s.page_content for s in section_summaries])
            master_prompt = f"Generate a comprehensive book summary (1-2 pages) based on these section summaries:\n\n{combined_summaries[:20000]}"
            try:
                master_summary = self.llm.call(master_prompt)
                master_doc = Document(
                    page_content=master_summary,
                    metadata={
                        "book_id": book_id,
                        "type": "book_summary",
                        "source": source_path
                    }
                )
                self.summary_store.add_documents([master_doc])
            except Exception as e:
                print(f"Error generating master summary: {e}")

    def query(self, query_text: str, book_id: Optional[str] = None, k: int = 5, query_type: str = "SPECIFIC") -> List[Document]:
        """Queries the vector store with adaptive retrieval and re-ranking."""
        filter_dict = {"book_id": book_id} if book_id else None
        
        if query_type == "BROAD":
            return self._query_broad(query_text, book_id, filter_dict)
        elif query_type == "MIXED":
            return self._query_mixed(query_text, book_id, filter_dict)
        else:
            # SPECIFIC
            initial_chunks = self.vector_store.similarity_search(query_text, k=min(k * 3, 50), filter=filter_dict)
            return self.rerank_for_relevance(initial_chunks, query_text, k)

    def _query_broad(self, query_text: str, book_id: str, filter_dict: dict) -> List[Document]:
        """Retrieves book summary and a diverse sample of chunks."""
        results = []
        
        # 1. Get book summary
        summary_filter = {"book_id": book_id, "type": "book_summary"} if book_id else {"type": "book_summary"}
        summaries = self.summary_store.similarity_search(query_text, k=1, filter=summary_filter)
        results.extend(summaries)
        
        # 2. Get diversified sample of chunks
        # High k to get a pool for sampling
        pool = self.vector_store.similarity_search(query_text, k=50, filter=filter_dict)
        results.extend(self.diversified_sample(pool, n=15))
        
        return results

    def _query_mixed(self, query_text: str, book_id: str, filter_dict: dict) -> List[Document]:
        """Combines summaries and specific relevant chunks."""
        results = self._query_broad(query_text, book_id, filter_dict)
        # Add more specific chunks
        specific = self.vector_store.similarity_search(query_text, k=15, filter=filter_dict)
        results.extend(specific)
        return self.rerank_for_relevance(results, query_text, k=30)

    def diversified_sample(self, chunks: List[Document], n: int = 10) -> List[Document]:
        """Samples chunks proportionally across the narrative arc."""
        if not chunks:
            return []
            
        # Sort by temporal order (start_char)
        sorted_chunks = sorted(chunks, key=lambda x: x.metadata.get("start_char", 0))
        
        if len(sorted_chunks) <= n:
            return sorted_chunks
            
        # Divide into thirds
        m1 = len(sorted_chunks) // 3
        m2 = 2 * len(sorted_chunks) // 3
        
        s1 = sorted_chunks[:m1]
        s2 = sorted_chunks[m1:m2]
        s3 = sorted_chunks[m2:]
        
        # Sample proportionally
        k_each = n // 3
        sample = s1[:k_each] + s2[:k_each] + s3[:k_each + (n % 3)]
        return sample

    def rerank_for_relevance(self, chunks: List[Document], query: str, k: int) -> List[Document]:
        """Removes near-duplicates and returns top k."""
        if not chunks:
            return []
            
        seen_content = set()
        unique_chunks = []
        
        for doc in chunks:
            content = doc.page_content.strip()[:200] # Use prefix for diversity check
            if content not in seen_content:
                unique_chunks.append(doc)
                seen_content.add(content)
        
        return unique_chunks[:k]

if __name__ == "__main__":
    # Quick test
    storage = RAGStorage()
    print("RAG Storage initialized.")
