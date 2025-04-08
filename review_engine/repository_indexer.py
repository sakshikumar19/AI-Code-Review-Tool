import os
import git
from typing import Dict

class RepositoryIndexer:
    """Indexes a repository to find all code files."""
    
    def __init__(self, config):
        """
        Initialize the repository indexer.
        
        Args:
            config: Configuration for the repository indexer
        """
        self.config = config
        self.logger = config.logger
        
    def index_repository(self) -> Dict[str, str]:
        """
        Index the repository specified in the config.
        
        Returns:
            Dictionary mapping file paths to their content
        """
        self.logger.info(f"Indexing repository: {self.config.repo_path}")
        
        # Handle if the repo path is a URL
        if self.config.repo_path.startswith(('http://', 'https://')):
            temp_dir = os.path.join(os.path.dirname(self.config.vector_db_path), "repo_clone")
            try:
                self.logger.info(f"Repository is a URL. Cloning to {temp_dir}")
                if os.path.exists(temp_dir):
                    self.logger.info(f"Removing existing clone directory {temp_dir}")
                    import shutil
                    shutil.rmtree(temp_dir)
                
                git.Repo.clone_from(self.config.repo_path, temp_dir)
                self.logger.info(f"Successfully cloned repository to {temp_dir}")
                repo_path = temp_dir
            except Exception as e:
                self.logger.error(f"Failed to clone repository: {e}")
                return {}
        else:
            repo_path = self.config.repo_path
        
        # Make sure the path exists
        if not os.path.exists(repo_path):
            self.logger.error(f"Repository path does not exist: {repo_path}")
            return {}
        
        files = {}
        code_extensions = self.config.code_extensions if hasattr(self.config, 'code_extensions') else [
            '.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.ts'
        ]
        
        # Walk through the repository
        for root, _, filenames in os.walk(repo_path):
            for filename in filenames:
                # Check if file has a code extension
                _, ext = os.path.splitext(filename)
                if ext.lower() not in code_extensions:
                    continue
                
                # Build file path
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, repo_path)
                
                # Skip files in directories to ignore
                ignore_dirs = self.config.ignore_dirs if hasattr(self.config, 'ignore_dirs') else [
                    '.git', 'node_modules', 'venv', '__pycache__', '.venv'
                ]
                
                should_ignore = False
                for ignore_dir in ignore_dirs:
                    if ignore_dir in relative_path.split(os.sep):
                        should_ignore = True
                        break
                
                if should_ignore:
                    continue
                
                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    files[relative_path] = content
                except Exception as e:
                    self.logger.warning(f"Failed to read file {file_path}: {e}")
        
        self.logger.info(f"Indexed {len(files)} files from the repository")
        
        # If no files were found, log potential issues
        if len(files) == 0:
            self.logger.error("No files were indexed. Possible issues:")
            self.logger.error(f"- Repository path exists: {os.path.exists(repo_path)}")
            self.logger.error(f"- Repository path contents: {os.listdir(repo_path) if os.path.exists(repo_path) else 'N/A'}")
            self.logger.error(f"- Code extensions being searched: {code_extensions}")
            self.logger.error(f"- Directories being ignored: {ignore_dirs if hasattr(self.config, 'ignore_dirs') else 'default'}")
        
        return files