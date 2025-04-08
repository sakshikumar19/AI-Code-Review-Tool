from typing import Dict, Any


from ..config import CodeReviewConfig
from repository_indexer import RepositoryIndexer
from pattern_extractor import PatternExtractor  
from rag_engine import RAGEngine
from difference_analyzer import DiffAnalyzer
from recommendation_generator import RecommendationGenerator

class AICodeReview:
    """Main class for AI Code Review."""
    
    def __init__(self, config: CodeReviewConfig):
        """
        Initialize the AI Code Review system.
        
        Args:
            config: Configuration for the AI Code Review system
        """
        self.config = config
        self.logger = config.logger
        
        # Initialize components
        self.indexer = RepositoryIndexer(config)
        self.pattern_extractor = PatternExtractor(config)
        self.rag_engine = RAGEngine(config)
        self.diff_analyzer = DiffAnalyzer(config, self.rag_engine)
        self.recommendation_generator = RecommendationGenerator(config, self.rag_engine)
    
    def learn_repository(self) -> bool:
        """
        Learn patterns from the repository.
        
        Returns:
            True if the repository was learned successfully, False otherwise
        """
        self.logger.info(f"Learning repository: {self.config.repo_path}")
        
        # Index repository
        files = self.indexer.index_repository()
        if not files:
            self.logger.error("Failed to index repository")
            return False
        
        # Extract patterns
        patterns = self.pattern_extractor.extract_patterns(files)
        
        # Build vector store
        self.rag_engine.build_vector_store(files)
        
        # Store patterns
        self.rag_engine.store_patterns(patterns)
        
        self.logger.info("Repository learned successfully")
        return True
    
    def load_knowledge(self) -> bool:
        """
        Load previously learned knowledge.
        
        Returns:
            True if knowledge was loaded successfully, False otherwise
        """
        self.logger.info("Loading previously learned knowledge")
        
        # Load vector store
        vector_store_loaded = self.rag_engine.load_vector_store()
        
        # Load patterns
        patterns_loaded = self.rag_engine.load_patterns()
        
        if not vector_store_loaded or not patterns_loaded:
            self.logger.warning("Failed to load knowledge")
            return False
        
        self.logger.info("Knowledge loaded successfully")
        return True
    
    def review_code(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Review a code snippet.
        
        Args:
            code: Code to review
            file_path: Path to the file being reviewed
            
        Returns:
            Review results
        """
        self.logger.info(f"Reviewing code: {file_path}")
        
        # Make sure knowledge is loaded
        if not self.rag_engine.patterns:
            loaded = self.load_knowledge()
            if not loaded:
                self.logger.error("Failed to load knowledge for review")
                return {"error": "Knowledge not loaded"}
        
        # Analyze code
        analysis = self.diff_analyzer.analyze_code(code, file_path)
        
        # Generate recommendations
        review = self.recommendation_generator.generate_recommendations(analysis, file_path)
        
        return review
    
    def review_diff(self, original_code: str, new_code: str, file_path: str) -> Dict[str, Any]:
        """
        Review a code diff.
        
        Args:
            original_code: Original code
            new_code: New code
            file_path: Path to the file being reviewed
            
        Returns:
            Review results
        """
        self.logger.info(f"Reviewing diff: {file_path}")
        
        # Make sure knowledge is loaded
        if not self.rag_engine.patterns:
            loaded = self.load_knowledge()
            if not loaded:
                self.logger.error("Failed to load knowledge for review")
                return {"error": "Knowledge not loaded"}
        
        # Analyze diff
        analysis = self.diff_analyzer.analyze_diff(original_code, new_code, file_path)
        
        # Generate recommendations
        review = self.recommendation_generator.generate_recommendations(analysis, file_path)
        
        return review