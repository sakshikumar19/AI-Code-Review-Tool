import os
import json
import logging
import argparse

from review_engine.AI_code_review import AICodeReview
from config import CodeReviewConfig

def main():
    """Main function for command-line usage."""
    
    parser = argparse.ArgumentParser(description="AI Code Review Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Learn from a repository")
    learn_parser.add_argument("repo_path", help="Path or URL to the repository")
    learn_parser.add_argument("--groq-api-key", help="Groq API key")
    learn_parser.add_argument("--vector-db-path", default="./vector_db", help="Path to store the vector database")
    learn_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                             help="Logging level")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review a file")
    review_parser.add_argument("file_path", help="Path to the file to review")
    review_parser.add_argument("--groq-api-key", help="Groq API key")
    review_parser.add_argument("--vector-db-path", default="./vector_db", help="Path to the vector database")
    review_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                             help="Logging level")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Convert log level string to logging constant
    log_level = getattr(logging, args.log_level)
    
    if args.command == "learn":
        # Create configuration
        config = CodeReviewConfig(
            repo_path=args.repo_path,
            groq_api_key=args.groq_api_key,
            vector_db_path=args.vector_db_path,
            log_level=log_level
        )
        
        # Create AI Code Review
        ai_review = AICodeReview(config)
        
        # Learn repository
        success = ai_review.learn_repository()
        if success:
            print("Repository learned successfully")
        else:
            print("Failed to learn repository")
    
    elif args.command == "review":
        # Get repository path from file_path
        repo_path = os.path.dirname(os.path.abspath(args.file_path))
        
        # Create configuration
        config = CodeReviewConfig(
            repo_path=repo_path,
            groq_api_key=args.groq_api_key,
            vector_db_path=args.vector_db_path,
            log_level=log_level
        )
        
        # Create AI Code Review
        ai_review = AICodeReview(config)
        
        # Load knowledge
        success = ai_review.load_knowledge()
        if not success:
            print("Failed to load knowledge")
            return
        
        # Read file
        try:
            with open(args.file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            print(f"Failed to read file: {e}")
            return
        
        # Review code
        review = ai_review.review_code(code, os.path.basename(args.file_path))
        
        # Print review
        print(json.dumps(review, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()