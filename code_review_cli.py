import os
import json
import logging
import argparse
import textwrap
import colorama
from colorama import Fore, Style

from review_engine.AI_code_review import AICodeReview
from review_engine.config import CodeReviewConfig

# Initialize colorama
colorama.init()

def setup_logger(log_level):
    """Set up logger with the specified log level."""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * 80)
    print(f" {text}")
    print("=" * 80 + f"{Style.RESET_ALL}\n")

def print_section(title):
    """Print a section title."""
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}" + "-" * len(title) + f"{Style.RESET_ALL}")

def print_severity_badge(severity):
    """Print a colored badge for severity level."""
    severity = severity.upper()
    if severity == "CRITICAL":
        return f"{Fore.WHITE}{Style.BRIGHT}{Fore.RED} CRITICAL {Style.RESET_ALL}"
    elif severity == "HIGH":
        return f"{Fore.RED} HIGH {Style.RESET_ALL}"
    elif severity == "MEDIUM":
        return f"{Fore.YELLOW} MEDIUM {Style.RESET_ALL}"
    elif severity == "LOW":
        return f"{Fore.GREEN} LOW {Style.RESET_ALL}"
    else:
        return f"{Fore.BLUE} INFO {Style.RESET_ALL}"

def print_score_bar(score, label, width=20):
    """Print a visual score bar."""
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    print(f"{label.ljust(15)}: [{Fore.CYAN}{bar}{Style.RESET_ALL}] {score:.2f}/1.0")

def print_review(review, detailed):
    if "recommendations" in review:
        print_section("RECOMMENDATIONS")
        for i, rec in enumerate(review["recommendations"], 1):
            if isinstance(rec, dict):
                print(f"{i}. Type: {rec.get('type', 'N/A')} ({rec.get('subtype', 'N/A')})")
                print(f"   Message   : {rec.get('message', '')}")
                print(f"   Suggestion: {rec.get('suggestion', '')}")
                print(f"   Severity  : {rec.get('severity', '')}\n")
            else:
                # Fallback if it's just a plain string
                print(f"{i}. {textwrap.fill(str(rec), width=80, subsequent_indent='   ')}")

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="AI Code Review Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Learn from a repository
          python code_review_cli.py learn ./my-project
          
          # Review a specific file
          python code_review_cli.py review ./my-project/file.py
          
          # Review multiple files
          python code_review_cli.py review ./my-project/file1.py ./my-project/file2.py
          
          # Review all files in a directory
          python code_review_cli.py review-dir ./my-project/src
        """)
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Learn from a repository")
    learn_parser.add_argument("repo_path", help="Path or URL to the repository")
    learn_parser.add_argument("--groq-api-key", help="Groq API key")
    learn_parser.add_argument("--vector-db-path", default="./vector_db", help="Path to store the vector database")
    learn_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                            help="Logging level")
    learn_parser.add_argument("--force", action="store_true", help="Force relearning even if knowledge exists")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review one or more files")
    review_parser.add_argument("file_paths", nargs="+", help="Paths to the files to review")
    review_parser.add_argument("--groq-api-key", help="Groq API key")
    review_parser.add_argument("--vector-db-path", default="./vector_db", help="Path to the vector database")
    review_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                            help="Logging level")
    review_parser.add_argument("--output", choices=["console", "json"], default="console", help="Output format")
    review_parser.add_argument("--output-file", help="Output file path (if not specified, prints to stdout)")
    review_parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    
    # Review directory command
    review_dir_parser = subparsers.add_parser("review-dir", help="Review all files in a directory")
    review_dir_parser.add_argument("dir_path", help="Path to the directory to review")
    review_dir_parser.add_argument("--groq-api-key", help="Groq API key")
    review_dir_parser.add_argument("--vector-db-path", default="./vector_db", help="Path to the vector database")
    review_dir_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                                help="Logging level")
    review_dir_parser.add_argument("--output", choices=["console", "json"], default="console", help="Output format")
    review_dir_parser.add_argument("--output-file", help="Output file path (if not specified, prints to stdout)")
    review_dir_parser.add_argument("--extensions", default=".py,.js,.java,.c,.cpp,.go,.rb,.php,.ts",
                                 help="Comma-separated list of file extensions to review")
    review_dir_parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    review_dir_parser.add_argument("--recursive", action="store_true", help="Review files recursively")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if a command was provided
    if not args.command:
        parser.print_help()
        return
    
    # Get API key from environment if not provided
    groq_api_key = args.groq_api_key or os.environ.get("GROQ_API_KEY")
    if not groq_api_key and args.command != "help":
        print(f"{Fore.RED}Error: Groq API key not provided. Set it with --groq-api-key or GROQ_API_KEY environment variable.{Style.RESET_ALL}")
        return
    
    # Convert log level string to logging constant
    log_level = getattr(logging, args.log_level)
    setup_logger(log_level)
    
    if args.command == "learn":
        # Create configuration
        config = CodeReviewConfig(
            repo_path=args.repo_path,
            groq_api_key=groq_api_key,
            vector_db_path=args.vector_db_path,
            log_level=log_level
        )
        
        # Create AI Code Review
        ai_review = AICodeReview(config)
        
        # Check if knowledge already exists
        if os.path.exists(args.vector_db_path) and not args.force:
            print(f"{Fore.YELLOW}Knowledge base already exists at {args.vector_db_path}. Use --force to relearn.{Style.RESET_ALL}")
            return
        
        # Learn repository
        print(f"{Fore.CYAN}Learning repository: {args.repo_path}...{Style.RESET_ALL}")
        success = ai_review.learn_repository()
        if success:
            print(f"{Fore.GREEN}Repository learned successfully! Knowledge stored at {args.vector_db_path}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to learn repository{Style.RESET_ALL}")
    
    elif args.command == "review":
        # Get repository path from first file's path
        repo_path = os.path.dirname(os.path.abspath(args.file_paths[0]))
        
        # Create configuration
        config = CodeReviewConfig(
            repo_path=repo_path,
            groq_api_key=groq_api_key,
            vector_db_path=args.vector_db_path,
            log_level=log_level
        )
        
        # Create AI Code Review
        ai_review = AICodeReview(config)
        
        # Load knowledge
        print(f"{Fore.CYAN}Loading knowledge from {args.vector_db_path}...{Style.RESET_ALL}")
        success = ai_review.load_knowledge()
        if not success:
            print(f"{Fore.YELLOW}Warning: Failed to load knowledge. Reviews may be less accurate.{Style.RESET_ALL}")
        
        # Review each file
        all_reviews = {}
        for file_path in args.file_paths:
            print(f"{Fore.CYAN}Reviewing {file_path}...{Style.RESET_ALL}")
            
            # Read file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                print(f"{Fore.RED}Failed to read file {file_path}: {e}{Style.RESET_ALL}")
                continue
            
            # Review code
            review = ai_review.review_code(code, os.path.basename(file_path))
            
            # Store or print review
            if args.output == "console":
                print_review(review, args.detailed)
            else:
                all_reviews[file_path] = review
        
        # Output JSON if requested
        if args.output == "json":
            if args.output_file:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    json.dump(all_reviews, f, indent=2)
                print(f"{Fore.GREEN}Reviews written to {args.output_file}{Style.RESET_ALL}")
            else:
                print(json.dumps(all_reviews, indent=2))
    
    elif args.command == "review-dir":
        # Create configuration
        config = CodeReviewConfig(
            repo_path=args.dir_path,
            groq_api_key=groq_api_key,
            vector_db_path=args.vector_db_path,
            log_level=log_level
        )
        
        # Create AI Code Review
        ai_review = AICodeReview(config)
        
        # Load knowledge
        print(f"{Fore.CYAN}Loading knowledge from {args.vector_db_path}...{Style.RESET_ALL}")
        success = ai_review.load_knowledge()
        if not success:
            print(f"{Fore.YELLOW}Warning: Failed to load knowledge. Reviews may be less accurate.{Style.RESET_ALL}")
        
        # Get file extensions to review
        extensions = args.extensions.split(",")
        
        # Find files to review
        files_to_review = []
        if args.recursive:
            for root, _, files in os.walk(args.dir_path):
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        files_to_review.append(os.path.join(root, file))
        else:
            for file in os.listdir(args.dir_path):
                file_path = os.path.join(args.dir_path, file)
                if os.path.isfile(file_path) and any(file.endswith(ext) for ext in extensions):
                    files_to_review.append(file_path)
        
        print(f"{Fore.CYAN}Found {len(files_to_review)} files to review{Style.RESET_ALL}")
        
        # Review each file
        all_reviews = {}
        for file_path in files_to_review:
            print(f"{Fore.CYAN}Reviewing {file_path}...{Style.RESET_ALL}")
            
            # Read file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                print(f"{Fore.RED}Failed to read file {file_path}: {e}{Style.RESET_ALL}")
                continue
            
            # Review code
            review = ai_review.review_code(code, os.path.basename(file_path))
            
            # Store or print review
            if args.output == "console":
                print_review(review, args.detailed)
            else:
                all_reviews[file_path] = review
        
        # Output JSON if requested
        if args.output == "json":
            if args.output_file:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    json.dump(all_reviews, f, indent=2)
                print(f"{Fore.GREEN}Reviews written to {args.output_file}{Style.RESET_ALL}")
            else:
                print(json.dumps(all_reviews, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()