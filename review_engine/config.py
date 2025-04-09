import logging
from typing import List, Optional

import nest_asyncio
nest_asyncio.apply()

class CodeReviewConfig:
    """Configuration for the AI Code Review system."""
    
    def __init__(
        self,
        repo_path: str,
        vector_db_path: str = "./vector_db",
        groq_api_key: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "llama-3.3-70b-versatile",
        log_level: int = logging.INFO,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        code_extensions: Optional[List[str]] = None,
        ignore_dirs: Optional[List[str]] = None,
        review_depth: int = 3
    ):
        """
        Initialize the configuration.
        
        Args:
            repo_path: Path to the repository
            vector_db_path: Path to store the vector database
            groq_api_key: Groq API key for LLM calls
            embedding_model: Model to use for embeddings
            log_level: Logging level
            chunk_size: Size of chunks for text splitting
            chunk_overlap: Overlap of chunks for text splitting
            code_extensions: List of file extensions to index
            ignore_dirs: List of directories to ignore when indexing
        """
        self.repo_path = repo_path
        self.vector_db_path = vector_db_path
        self.groq_api_key = groq_api_key
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Set default code extensions if not provided
        self.code_extensions = code_extensions or [
            '.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.ts'
        ]
        
        # Set default ignore directories if not provided
        self.ignore_dirs = ignore_dirs or [
            '.git', 'node_modules', 'venv', '__pycache__', '.venv'
        ]
                
        # Set up logger
        self.logger = logging.getLogger("AI-CodeReview")
        self.logger.setLevel(log_level)
        
        self.review_depth = max(1, min(5, review_depth))
        
        # Check if handler already exists to prevent duplicate logs
        if not self.logger.handlers:
            # Create console handler
            handler = logging.StreamHandler()
            handler.setLevel(log_level)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(handler)