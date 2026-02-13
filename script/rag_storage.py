import os
import warnings
import json
import re
from typing import List, Optional, Dict, Any, Tuple
from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

try:
    import networkx as nx
except ImportError:
    nx = None
    print("[WARNING] NetworkX not found. GraphRAG features will be disabled.")

# New import for HuggingFaceEmbeddings
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback to older import if new package not installed, but warn
    warnings.warn(
        "The `langchain-huggingface` package is not installed. "
        "Falling back to `langchain_community.embeddings.HuggingFaceEmbeddings`. "
        "Consider running `pip install -U langchain-huggingface`."
    )
    from langchain_community.embeddings import HuggingFaceEmbeddings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

class RAGStorage:
    def __init__(self, persist_directory: str = "crews/shared/rag_db", llm=None):
        self.persist_directory = persist_directory
        self.llm = llm # Use provided LLM
        
        # Graph storage path
        self.graph_path = os.path.join(self.persist_directory, "knowledge_graph.gml")
        self.graph = nx.Graph() if nx else None
        
        # Load existing graph if available
        if self.graph and os.path.exists(self.graph_path):
            try:
                self.graph = nx.read_gml(self.graph_path)
                print(f"[INFO] Loaded Knowledge Graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
            except Exception as e:
                print(f"[WARNING] Could not load existing graph: {e}. Starting fresh.")
                self.graph = nx.Graph()

        # If no LLM is provided, initialize a default one for summarization
        if self.llm is None:
            try:
                from crewai import LLM
                model = os.getenv("OLLAMA_MODEL", "llama3")
                base_url = os.getenv("OLLAMA_BASE_URL") or f"http://{os.getenv('OLLAMA_SERVER', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}"
                self.llm = LLM(model=f"ollama/{model}", base_url=base_url)
                print(f"[INFO] RAGStorage initialized with default Ollama LLM for summarization: {model} at {base_url}")
            except Exception as e:
                print(f"[WARNING] Could not initialize default Ollama LLM for RAG summarization: {e}")
                print("Summarization will be skipped unless an LLM is explicitly provided.")
        
        # Use a real embedding model if possible (Upgraded to BGE-M3 for superior RAG quality)
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        except Exception:
            print("Warning: HuggingFaceEmbeddings (bge-m3) not available. Using fake embeddings.")
            from langchain_community.embeddings import DeterministicFakeEmbedding
            self.embeddings = DeterministicFakeEmbedding(size=1024)
            
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

    def is_book_indexed(self, book_id: str) -> bool:
        """Checks if a book with the given book_id is already indexed."""
        # Querying with a specific book_id and limit 1 to check existence
        # The query text can be anything, as we are filtering by book_id
        # We need to explicitly load the collection first
        try:
            # Check vector store
            collection = self.vector_store.get_or_create_collection(self.vector_store._collection_name)
            results = collection.get(
                where={"book_id": book_id},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            print(f"[WARNING] Could not check if book '{book_id}' is indexed: {e}")
            return False

    def save_graph(self):
        """Saves the NetworkX graph to disk."""
        if self.graph and nx:
            try:
                os.makedirs(self.persist_directory, exist_ok=True)
                nx.write_gml(self.graph, self.graph_path)
                print(f"[INFO] Knowledge Graph saved to {self.graph_path}")
            except Exception as e:
                print(f"[ERROR] Failed to save graph: {e}")

    def _extract_graph_elements(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Uses LLM to extract entities and relationships from text.
        Returns (nodes, edges).
        """
        if not self.llm:
            return [], []

        prompt = (
            "Extract the main Entities (Characters, Locations, Organizations, Key Objects) and Relationships from the following text.\n"
            "Return JSON format with 'entities' (name, type, description) and 'relationships' (source, target, relation, description).\n"
            "Keep descriptions concise.\n\n"
            f"Text: {text[:4000]}\n\n" # Limit text context
            "JSON Output:"
        )
        
        try:
            response = self.llm.call(prompt)
            # Basic cleanup to find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("entities", []), data.get("relationships", [])
            else:
                # Fallback simple parsing if JSON fails (regex-based)
                return [], [] # Too risky to parse unstructured text here
        except Exception as e:
            print(f"[DEBUG] Graph extraction failed: {e}")
            return [], []

    def update_graph_from_text(self, text: str, source_id: str):
        """Updates the graph with entities from a text segment."""
        if not self.graph:
            return

        entities, relationships = self._extract_graph_elements(text)
        
        for entity in entities:
            name = entity.get("name")
            if name:
                if not self.graph.has_node(name):
                    self.graph.add_node(name, type=entity.get("type", "Unknown"), description=entity.get("description", ""))
                else:
                    # Merge description if needed
                    pass

        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            relation = rel.get("relation")
            if source and target and relation:
                if self.graph.has_node(source) and self.graph.has_node(target):
                    self.graph.add_edge(source, target, relation=relation, description=rel.get("description", ""))

    def add_book(self, file_path: str, book_id: str):
        """Indexes a book into the vector store and generates hierarchical summaries."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        if self.is_book_indexed(book_id):
            print(f"Book '{book_id}' is already indexed. Skipping re-indexing.")
            return True

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

        chunks = self.text_splitter.split_documents(documents)
        # Enrich chunks with character positions
        current_pos = 0
        for chunk in chunks:
            chunk.metadata["start_char"] = current_pos
            chunk.metadata["end_char"] = current_pos + len(chunk.page_content)
            current_pos += len(chunk.page_content)

        self.vector_store.add_documents(chunks)
        print(f"Successfully indexed {len(chunks)} chunks from {book_id}.")

        # --- GraphRAG & Summarization Step ---
        # We perform this AFTER vector indexing to ensure basic search works first.
        if len(full_text) > 5000:
            self.generate_hierarchical_summaries(full_text, book_id, file_path)
        
        return True

    def generate_hierarchical_summaries(self, text: str, book_id: str, source_path: str):
        """Generates section-level summaries and updates the Knowledge Graph."""
        if not self.llm:
            print("No LLM provided for summarization. Skipping.")
            return

        print(f"Generating hierarchical summaries & Knowledge Graph for {book_id}...")
        
        # Split into sections (approx 50k chars each)
        section_size = 50000
        sections = [text[i:i + section_size] for i in range(0, len(text), section_size)]
        
        # Limit sections for very long books
        if len(sections) > 20:
            sections = sections[:20] 

        section_summaries = []
        for i, section in enumerate(sections):
            prompt = f"Summarize this section of the book (approx. 300 words). Focus on key plot points, character development, and themes:\n\n{section[:15000]}" # Limit context
            try:
                summary = self.llm.call(prompt) 
                
                # 1. Add to Summary Store
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
                
                # 2. Update Graph from this summary (Much faster than processing raw text)
                if self.graph:
                    print(f"  [Graph] Extracting entities from section {i+1}/{len(sections)} summary...")
                    self.update_graph_from_text(summary, f"{book_id}_section_{i}")
                    
            except Exception as e:
                print(f"Error processing section {i}: {e}")

        if section_summaries:
            self.summary_store.add_documents(section_summaries)
            
            # Master summary
            combined_summaries = "\n\n".join([s.page_content for s in section_summaries])
            master_prompt = f"Generate a comprehensive book summary (1-2 pages) based on these section summaries. Include main character arcs and themes:\n\n{combined_summaries[:20000]}"
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
        
        # Save graph after processing all sections
        self.save_graph()

    def query(self, query_text: str, book_id: Optional[str] = None, k: int = 5, query_type: str = "SPECIFIC") -> List[Document]:
        """Queries the vector store with adaptive retrieval and re-ranking."""
        filter_dict = {"book_id": book_id} if book_id else None
        
        if query_type == "BROAD" or query_type == "GRAPH":
            return self._query_mixed(query_text, book_id, filter_dict, use_graph=(query_type == "GRAPH"))
        else:
            # SPECIFIC
            initial_chunks = self.vector_store.similarity_search(query_text, k=min(k * 3, 50), filter=filter_dict)
            return self.rerank_for_relevance(initial_chunks, query_text, k)

    def _query_graph(self, query_text: str, k: int = 3) -> List[Document]:
        """Retrieves relevant context from the Knowledge Graph."""
        if not self.graph:
            return []
            
        # 1. Extract potential entities from query (simple heuristic or LLM)
        # Simple heuristic: Capitalized words (not perfect but fast)
        potential_entities = re.findall(r'\b[A-Z][a-z]+\b', query_text)
        
        found_nodes = []
        for entity in potential_entities:
            # Case-insensitive search in graph nodes
            for node in self.graph.nodes():
                if entity.lower() in node.lower():
                    found_nodes.append(node)
        
        graph_context = []
        for node in found_nodes[:5]: # Limit to top 5 matching nodes
            # Get neighbors
            neighbors = list(self.graph.neighbors(node))
            
            # Construct description
            desc = f"Entity: {node} ({self.graph.nodes[node].get('type', 'Unknown')})\n"
            desc += f"Description: {self.graph.nodes[node].get('description', '')}\n"
            desc += "Relationships:\n"
            
            for neighbor in neighbors[:5]: # Limit neighbors
                edge_data = self.graph.get_edge_data(node, neighbor)
                rel_type = edge_data.get('relation', 'related to')
                desc += f"  - {rel_type} -> {neighbor}\n"
            
            graph_context.append(Document(
                page_content=desc,
                metadata={"type": "graph_context", "entity": node}
            ))
            
        return graph_context

    def _query_mixed(self, query_text: str, book_id: str, filter_dict: dict, use_graph: bool = True) -> List[Document]:
        """Combines summaries, graph context, and specific relevant chunks."""
        results = []
        
        # 1. Graph Context
        if use_graph:
            graph_docs = self._query_graph(query_text)
            results.extend(graph_docs)
            print(f"[DEBUG] Retrieved {len(graph_docs)} graph context documents")
        
        # 2. Broad Summaries
        summary_filter = {"book_id": book_id, "type": "book_summary"} if book_id else {"type": "book_summary"}
        summaries = self.summary_store.similarity_search(query_text, k=1, filter=summary_filter)
        results.extend(summaries)
        
        # 3. Chapter Summaries (Mid-level)
        chapter_filter = {"book_id": book_id, "type": "chapter_summary"} if book_id else {"type": "chapter_summary"}
        chapter_summaries = self.summary_store.similarity_search(query_text, k=3, filter=chapter_filter)
        results.extend(chapter_summaries)
        
        # 4. Specific Chunks (Low-level)
        specific = self.vector_store.similarity_search(query_text, k=10, filter=filter_dict)
        results.extend(specific)
        
        return self.rerank_for_relevance(results, query_text, k=15)

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
