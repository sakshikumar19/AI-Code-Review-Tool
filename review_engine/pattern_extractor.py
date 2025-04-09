import os
import re
import ast
import numpy as np

from collections import Counter, defaultdict
from typing import Dict, Any

from review_engine.config import CodeReviewConfig

class PatternExtractor:
    """Extracts coding patterns and conventions from a codebase."""
    
    def __init__(self, config: CodeReviewConfig):
        """
        Initialize the pattern extractor.
        
        Args:
            config: Configuration for the pattern extractor
        """
        self.config = config
        self.logger = config.logger
        
    def extract_style_patterns(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract style patterns from the codebase.
        
        Args:
            files: Dictionary mapping file paths to their content
            
        Returns:
            Dictionary of style patterns
        """
        self.logger.info("Extracting style patterns from the codebase")
        
        # Initialize pattern collections
        indentation_patterns = Counter()
        line_length_patterns = []
        naming_patterns = {
            "variables": Counter(),
            "functions": Counter(),
            "classes": Counter(),
            "constants": Counter(),
        }
        
        # Regex patterns for different naming conventions
        naming_conventions = {
            "snake_case": re.compile(r'^[a-z][a-z0-9_]*$'),
            "camelCase": re.compile(r'^[a-z][a-zA-Z0-9]*$'),
            "PascalCase": re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
            "UPPER_SNAKE_CASE": re.compile(r'^[A-Z][A-Z0-9_]*$'),
            "kebab-case": re.compile(r'^[a-z][a-z0-9-]*$'),
        }
        
        # Process each file
        for file_path, content in files.items():
            ext = os.path.splitext(file_path)[1].lower()
            
            # Extract indentation patterns
            indentation_match = re.search(r'^(\s+)', content, re.MULTILINE)
            if indentation_match:
                indent = indentation_match.group(1)
                if '\t' in indent:
                    indentation_patterns["tabs"] += 1
                else:
                    indentation_patterns["spaces:" + str(len(indent))] += 1
            
            # Extract line length patterns
            for line in content.split('\n'):
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('//'):
                    line_length_patterns.append(len(line))
            
            # Extract naming patterns for Python files
            if ext == '.py':
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        # Extract variable names
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    name = target.id
                                    self._categorize_name(name, naming_patterns, naming_conventions)
                        
                        # Extract function names
                        elif isinstance(node, ast.FunctionDef):
                            name = node.name
                            for pattern, regex in naming_conventions.items():
                                if regex.match(name):
                                    naming_patterns["functions"][pattern] += 1
                                    break
                        
                        # Extract class names
                        elif isinstance(node, ast.ClassDef):
                            name = node.name
                            for pattern, regex in naming_conventions.items():
                                if regex.match(name):
                                    naming_patterns["classes"][pattern] += 1
                                    break
                except Exception as e:
                    self.logger.debug(f"Failed to parse Python file {file_path}: {e}")
            
            # Similar analysis for other languages can be added here
            
        # Calculate style statistics
        preferred_indentation = indentation_patterns.most_common(1)[0][0] if indentation_patterns else "spaces:4"
        avg_line_length = int(np.mean(line_length_patterns)) if line_length_patterns else 80
        max_line_length = int(np.percentile(line_length_patterns, 95)) if line_length_patterns else 100
        
        preferred_naming = {
            category: counter.most_common(1)[0][0] if counter else None
            for category, counter in naming_patterns.items()
        }
        
        return {
            "indentation": preferred_indentation,
            "line_length": {
                "average": avg_line_length,
                "preferred_max": max_line_length
            },
            "naming_conventions": preferred_naming
        }
    
    def _categorize_name(self, name: str, naming_patterns: Dict, naming_conventions: Dict):
        """Categorize a name based on its convention and context."""
        # Determine if it's likely a constant
        if re.match(r'^[A-Z][A-Z0-9_]*$', name):
            for pattern, regex in naming_conventions.items():
                if regex.match(name):
                    naming_patterns["constants"][pattern] += 1
                    return
        
        # Otherwise assume it's a variable
        for pattern, regex in naming_conventions.items():
            if regex.match(name):
                naming_patterns["variables"][pattern] += 1
                return
    
    def extract_architecture_patterns(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract architectural patterns from the codebase.
        
        Args:
            files: Dictionary mapping file paths to their content
            
        Returns:
            Dictionary of architectural patterns
        """
        self.logger.info("Extracting architectural patterns from the codebase")
        
        # Initialize pattern collections
        imports = defaultdict(Counter)
        file_structure = defaultdict(list)
        error_handling_patterns = Counter()
        
        # Process each file
        for file_path, content in files.items():
            ext = os.path.splitext(file_path)[1].lower()
            parent_dir = os.path.dirname(file_path)
            file_structure[parent_dir].append(os.path.basename(file_path))
            
            # Extract import patterns for Python files
            if ext == '.py':
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for name in node.names:
                                imports['direct'].update([name.name])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports['from'].update([node.module])
                        
                        # Extract error handling patterns
                        if isinstance(node, ast.Try):
                            error_handling_patterns['try_except'] += 1
                            for handler in node.handlers:
                                if handler.type:
                                    if isinstance(handler.type, ast.Name):
                                        error_handling_patterns[f'except_{handler.type.id}'] += 1
                                    elif isinstance(handler.type, ast.Tuple):
                                        for exc in handler.type.elts:
                                            if isinstance(exc, ast.Name):
                                                error_handling_patterns[f'except_{exc.id}'] += 1
                except Exception as e:
                    self.logger.debug(f"Failed to parse Python file {file_path}: {e}")
            
            # Extract import patterns for JavaScript/TypeScript files
            elif ext in ['.js', '.ts']:
                # Simple regex for import patterns
                import_matches = re.findall(r'import\s+(?:{[^}]+}|[^{]+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
                for match in import_matches:
                    imports['js_imports'].update([match])
                
                # Extract error handling patterns
                try_catch_matches = re.findall(r'try\s*{', content)
                error_handling_patterns['try_catch'] += len(try_catch_matches)
        
        # Extract common architectural patterns
        common_imports = {
            category: [item for item, count in counter.most_common(10)]
            for category, counter in imports.items()
        }
        
        directory_structure = {
            parent: files for parent, files in file_structure.items()
            if len(files) > 1  # Only include directories with multiple files
        }
        
        error_handling = {
            pattern: count for pattern, count in error_handling_patterns.most_common()
        }
        
        return {
            "common_imports": common_imports,
            "directory_structure": directory_structure,
            "error_handling": error_handling
        }
    
    def extract_functional_patterns(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract functional patterns from the codebase.
        
        Args:
            files: Dictionary mapping file paths to their content
            
        Returns:
            Dictionary of functional patterns
        """
        self.logger.info("Extracting functional patterns from the codebase")
        
        # Initialize pattern collections
        function_signatures = []
        common_functions = Counter()
        logging_patterns = Counter()
        test_patterns = Counter()
        
        # Process each file
        for file_path, content in files.items():
            ext = os.path.splitext(file_path)[1].lower()
            
            # Extract patterns for Python files
            if ext == '.py':
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        # Extract function signatures
                        if isinstance(node, ast.FunctionDef):
                            func_name = node.name
                            common_functions[func_name] += 1
                            
                            # Extract signature information
                            args = []
                            for arg in node.args.args:
                                arg_name = arg.arg
                                args.append(arg_name)
                            
                            signature = {
                                "name": func_name,
                                "args": args,
                                "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                            }
                            function_signatures.append(signature)
                            
                            # Check for logging patterns
                            for child_node in ast.walk(node):
                                if isinstance(child_node, ast.Call):
                                    if isinstance(child_node.func, ast.Attribute):
                                        if child_node.func.attr in ['debug', 'info', 'warning', 'error', 'critical']:
                                            if isinstance(child_node.func.value, ast.Name):
                                                logger_name = child_node.func.value.id
                                                logging_patterns[f"{logger_name}.{child_node.func.attr}"] += 1
                                    elif isinstance(child_node.func, ast.Name):
                                        if child_node.func.id in ['print']:
                                            logging_patterns['print'] += 1
                
                        # Extract test patterns
                        if 'test' in file_path.lower() or func_name.startswith('test_'):
                            if isinstance(node, ast.FunctionDef):
                                for child_node in ast.walk(node):
                                    if isinstance(child_node, ast.Call):
                                        if isinstance(child_node.func, ast.Attribute):
                                            if child_node.func.attr in ['assertEqual', 'assertTrue', 'assertFalse', 'assertRaises']:
                                                test_patterns[child_node.func.attr] += 1
                except Exception as e:
                    self.logger.debug(f"Failed to parse Python file {file_path}: {e}")
            
            # Similar analysis for other languages can be added here
        
        # Process function signatures for patterns
        common_arg_patterns = Counter()
        for signature in function_signatures:
            for arg in signature["args"]:
                common_arg_patterns[arg] += 1
        
        return {
            "common_functions": {name: count for name, count in common_functions.most_common(20)},
            "common_args": {name: count for name, count in common_arg_patterns.most_common(20)},
            "logging_patterns": {pattern: count for pattern, count in logging_patterns.most_common()},
            "test_patterns": {pattern: count for pattern, count in test_patterns.most_common()}
        }
    
    def extract_patterns(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract all patterns from the codebase.
        
        Args:
            files: Dictionary mapping file paths to their content
            
        Returns:
            Dictionary of extracted patterns
        """
        style_patterns = self.extract_style_patterns(files)
        architecture_patterns = self.extract_architecture_patterns(files)
        functional_patterns = self.extract_functional_patterns(files)
        
        return {
            "style": style_patterns,
            "architecture": architecture_patterns,
            "functional": functional_patterns
        }