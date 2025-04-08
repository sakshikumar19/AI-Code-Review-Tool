import os
import json
from typing import Dict, Any, List

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..config import CodeReviewConfig

class RAGEngine:
    """Retrieval-Augmented Generation engine for code analysis."""
    
    def __init__(self, config: CodeReviewConfig):
        """
        Initialize the RAG engine.
        
        Args:
            config: Configuration for the RAG engine
        """
        self.config = config
        self.logger = config.logger
        self.vector_store = None
        self.patterns = None
        
        if not LANGCHAIN_AVAILABLE:
            self.logger.warning("LangChain not available. RAG capabilities will be limited.")
    
    def build_vector_store(self, files: Dict[str, str]) -> None:
        """
        Build a vector store from the repository files.
        
        Args:
            files: Dictionary mapping file paths to their content
        """
        if not LANGCHAIN_AVAILABLE or not self.config.groq_api_key:
            self.logger.warning("Skipping vector store creation due to missing dependencies or API key")
            return
        
        self.logger.info("Building vector store from repository files")
        
        embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embedding_model,
            model_kwargs={"device": "cpu"}
        )
        
        # Initialize text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # Prepare documents
        documents = []
        for file_path, content in files.items():
            chunks = text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                documents.append({
                    "content": chunk,
                    "metadata": {
                        "file": file_path,
                        "chunk": i
                    }
                })
        
        # Create vector store
        texts = [doc["content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        self.vector_store = FAISS.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas
        )
        
        # Save vector store
        self.vector_store.save_local(self.config.vector_db_path)
        self.logger.info(f"Vector store built and saved to {self.config.vector_db_path}")
    
    def load_vector_store(self) -> bool:
        """
        Load the vector store from disk.
        
        Returns:
            True if the vector store was loaded successfully, False otherwise
        """
        if not LANGCHAIN_AVAILABLE or not self.config.groq_api_key:
            self.logger.warning("Skipping vector store loading due to missing dependencies or API key")
            return False
        
        self.logger.info(f"Loading vector store from {self.config.vector_db_path}")
        
        try:
            # Initialize embeddings
            embeddings = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model,
                model_kwargs={"device": "cpu"}
            )
            
            # Load vector store
            self.vector_store = FAISS.load_local(
                self.config.vector_db_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            self.logger.info("Vector store loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load vector store: {e}")
            return False
    
    def store_patterns(self, patterns: Dict[str, Any]) -> None:
        """
        Store extracted patterns for later use.
        
        Args:
            patterns: Dictionary of patterns extracted from the codebase
        """
        self.patterns = patterns
        
        # Save patterns to disk
        patterns_path = os.path.join(self.config.vector_db_path, "patterns.json")
        os.makedirs(os.path.dirname(patterns_path), exist_ok=True)
        
        with open(patterns_path, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        self.logger.info(f"Patterns stored to {patterns_path}")
    
    def load_patterns(self) -> bool:
        """
        Load patterns from disk.
        
        Returns:
            True if patterns were loaded successfully, False otherwise
        """
        patterns_path = os.path.join(self.config.vector_db_path, "patterns.json")
        
        if not os.path.exists(patterns_path):
            self.logger.warning(f"Patterns file not found at {patterns_path}")
            return False
        
        try:
            with open(patterns_path, 'r') as f:
                self.patterns = json.load(f)
            self.logger.info("Patterns loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load patterns: {e}")
            return False
    
    def retrieve_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve similar code snippets from the vector store.
        
        Args:
            code_snippet: Code snippet to find similar code for
            top_k: Number of similar snippets to retrieve
            
        Returns:
            List of similar code snippets with metadata
        """
        if not self.vector_store:
            self.logger.warning("Vector store not initialized")
            return []
        
        self.logger.info(f"Retrieving top {top_k} similar code snippets")
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=code_snippet,
                k=top_k
            )
            
            similar_code = []
            for doc, score in results:
                similar_code.append({
                    "content": doc.page_content,
                    "file": doc.metadata["file"],
                    "chunk": doc.metadata["chunk"],
                    "similarity": float(score)
                })
            
            return similar_code
        except Exception as e:
            self.logger.error(f"Failed to retrieve similar code: {e}")
            return []