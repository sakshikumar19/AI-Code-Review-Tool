from typing import List, Dict, Any, Optional
import os
import re
import ast
import difflib

from review_engine.config import CodeReviewConfig
from review_engine.rag_engine import RAGEngine

class DiffAnalyzer:
    """Analyzes code diffs against learned patterns."""
    
    def __init__(self, config: CodeReviewConfig, rag_engine: RAGEngine):
        """
        Initialize the diff analyzer.
        
        Args:
            config: Configuration for the diff analyzer
            rag_engine: RAG engine for pattern retrieval
        """
        self.config = config
        self.logger = config.logger
        self.rag_engine = rag_engine
    
    def analyze_style(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze style issues in the code.
        
        Args:
            code: Code to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of style issues
        """
        if not self.rag_engine.patterns:
            self.logger.warning("Patterns not loaded")
            return []
        
        self.logger.info(f"Analyzing style for {file_path}")
        
        issues = []
        style_patterns = self.rag_engine.patterns["style"]
        
        # Check indentation
        preferred_indentation = style_patterns["indentation"]
        indentation_match = re.search(r'^(\s+)', code, re.MULTILINE)
        if indentation_match:
            indent = indentation_match.group(1)
            current_indentation = "tabs" if '\t' in indent else f"spaces:{len(indent)}"
            
            if current_indentation != preferred_indentation:
                issues.append({
                    "type": "style",
                    "subtype": "indentation",
                    "message": f"Indentation uses {current_indentation}, but project standard is {preferred_indentation}",
                    "severity": "low"
                })
        
        # Check line length
        max_line_length = style_patterns["line_length"]["preferred_max"]
        long_lines = []
        
        for i, line in enumerate(code.split('\n')):
            if len(line.rstrip()) > max_line_length:
                long_lines.append(i + 1)
        
        if long_lines:
            if len(long_lines) <= 3:
                line_str = ", ".join(map(str, long_lines))
            else:
                line_str = f"{long_lines[0]}, {long_lines[1]}, ... and {len(long_lines) - 2} more"
            
            issues.append({
                "type": "style",
                "subtype": "line_length",
                "message": f"Lines exceed maximum length of {max_line_length} characters: {line_str}",
                "severity": "low"
            })
        
        # Check naming conventions (for Python)
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.py':
            try:
                tree = ast.parse(code)
                
                # Get preferred naming conventions
                preferred_naming = style_patterns["naming_conventions"]
                
                # Check variable names
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                issue = self._check_naming_convention(name, preferred_naming["variables"], "variable")
                                if issue:
                                    issues.append(issue)
                    
                    # Check function names
                    elif isinstance(node, ast.FunctionDef):
                        name = node.name
                        issue = self._check_naming_convention(name, preferred_naming["functions"], "function")
                        if issue:
                            issues.append(issue)
                    
                    # Check class names
                    elif isinstance(node, ast.ClassDef):
                        name = node.name
                        issue = self._check_naming_convention(name, preferred_naming["classes"], "class")
                        if issue:
                            issues.append(issue)
            except Exception as e:
                self.logger.debug(f"Failed to parse Python file for style analysis: {e}")
        
        return issues
    
    def _check_naming_convention(self, name: str, preferred_convention: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Check if a name follows the preferred naming convention."""
        naming_conventions = {
            "snake_case": re.compile(r'^[a-z][a-z0-9_]*$'),
            "camelCase": re.compile(r'^[a-z][a-zA-Z0-9]*$'),
            "PascalCase": re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
            "UPPER_SNAKE_CASE": re.compile(r'^[A-Z][A-Z0-9_]*$'),
            "kebab-case": re.compile(r'^[a-z][a-z0-9-]*$'),
        }
        
        if not preferred_convention or preferred_convention not in naming_conventions:
            return None
        
        if not naming_conventions[preferred_convention].match(name):
            current_convention = "unknown"
            for convention, pattern in naming_conventions.items():
                if pattern.match(name):
                    current_convention = convention
                    break
            
            return {
                "type": "style",
                "subtype": "naming_convention",
                "message": f"{entity_type.capitalize()} name '{name}' uses {current_convention} convention, but project standard is {preferred_convention}",
                "severity": "low"
            }
        
        return None
    
    def analyze_architecture(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze architectural issues in the code.
        
        Args:
            code: Code to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of architectural issues
        """
        if not self.rag_engine.patterns:
            self.logger.warning("Patterns not loaded")
            return []
        
        self.logger.info(f"Analyzing architecture for {file_path}")
        
        issues = []
        architecture_patterns = self.rag_engine.patterns["architecture"]
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check imports (for Python)
        if ext == '.py':
            try:
                tree = ast.parse(code)
                common_imports = architecture_patterns["common_imports"]
                
                # Extract imports from the code
                imports = []
                from_imports = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.append(name.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            from_imports.append(node.module)
                
                # Check for uncommon imports
                if "direct" in common_imports:
                    uncommon_imports = []
                    for imp in imports:
                        parts = imp.split('.')
                        if parts[0] not in common_imports["direct"]:
                            uncommon_imports.append(imp)
                    
                    if uncommon_imports:
                        issues.append({
                            "type": "architecture",
                            "subtype": "uncommon_import",
                            "message": f"Uncommon imports detected: {', '.join(uncommon_imports)}",
                            "severity": "medium"
                        })
                
                # Check for uncommon from imports
                if "from" in common_imports:
                    uncommon_from_imports = []
                    for imp in from_imports:
                        parts = imp.split('.')
                        if parts[0] not in common_imports["from"]:
                            uncommon_from_imports.append(imp)
                    
                    if uncommon_from_imports:
                        issues.append({
                            "type": "architecture",
                            "subtype": "uncommon_from_import",
                            "message": f"Uncommon from imports detected: {', '.join(uncommon_from_imports)}",
                            "severity": "low"
                        })
            except Exception as e:
                self.logger.debug(f"Failed to parse Python file for import analysis: {e}")
        
        # Check imports for JavaScript/TypeScript
        elif ext in ['.js', '.ts']:
            js_imports = re.findall(r'import\s+(?:{[^}]+}|[^{]+)\s+from\s+[\'"]([^\'"]+)[\'"]', code)
            
            if "js_imports" in architecture_patterns["common_imports"]:
                common_js_imports = architecture_patterns["common_imports"]["js_imports"]
                uncommon_imports = [imp for imp in js_imports if imp not in common_js_imports]
                
                if uncommon_imports:
                    issues.append({
                        "type": "architecture",
                        "subtype": "uncommon_js_import",
                        "message": f"Uncommon imports detected: {', '.join(uncommon_imports)}",
                        "severity": "low"
                    })
        
        # Check error handling patterns
        if ext == '.py':
            try:
                tree = ast.parse(code)
                has_try_except = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Try):
                        has_try_except = True
                        break
                
                # If there are function definitions but no try/except, suggest error handling
                if not has_try_except:
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and len(node.body) > 5:  # Non-trivial function
                            issues.append({
                                "type": "architecture",
                                "subtype": "error_handling",
                                "message": "Function lacks error handling. Consider adding try/except blocks based on project patterns.",
                                "severity": "medium"
                            })
                            break
            except Exception as e:
                self.logger.debug(f"Failed to parse Python file for error handling analysis: {e}")
        
        return issues
    
    def analyze_functionality(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze functional issues in the code.
        
        Args:
            code: Code to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of functional issues
        """
        if not self.rag_engine.patterns:
            self.logger.warning("Patterns not loaded")
            return []
        
        self.logger.info(f"Analyzing functionality for {file_path}")
        
        issues = []
        functional_patterns = self.rag_engine.patterns["functional"]
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check logging patterns (for Python)
        if ext == '.py':
            try:
                tree = ast.parse(code)
                has_logging = False
                has_print = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            if node.func.attr in ['debug', 'info', 'warning', 'error', 'critical']:
                                has_logging = True
                        elif isinstance(node.func, ast.Name):
                            if node.func.id == 'print':
                                has_print = True
                
                # If print is used but logging patterns exist in the codebase
                if has_print and not has_logging and functional_patterns["logging_patterns"] and not 'print' in functional_patterns["logging_patterns"]:
                    issues.append({
                        "type": "functionality",
                        "subtype": "logging",
                        "message": "Using print() for output, but project uses a logging framework. Consider using the appropriate logging methods.",
                        "severity": "medium"
                    })
            except Exception as e:
                self.logger.debug(f"Failed to parse Python file for logging analysis: {e}")
        
        # Check if test file follows project patterns
        if 'test' in file_path.lower():
            if ext == '.py':
                try:
                    tree = ast.parse(code)
                    has_assertions = False
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute):
                                if node.func.attr in ['assertEqual', 'assertTrue', 'assertFalse', 'assertRaises']:
                                    has_assertions = True
                                    break
                    
                    if not has_assertions:
                        issues.append({
                            "type": "functionality",
                            "subtype": "testing",
                            "message": "Test file lacks assertions. Consider adding appropriate test assertions.",
                            "severity": "high"
                        })
                except Exception as e:
                    self.logger.debug(f"Failed to parse Python test file: {e}")
        
        return issues
    
    def analyze_code(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze code against learned patterns.
        
        Args:
            code: Code to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            Dictionary with analysis results
        """
        self.logger.info(f"Analyzing code for {file_path}")
        
        style_issues = self.analyze_style(code, file_path)
        architecture_issues = self.analyze_architecture(code, file_path)
        functionality_issues = self.analyze_functionality(code, file_path)
        
        # Retrieve similar code for context
        similar_code = self.rag_engine.retrieve_similar_code(code)
        
        return {
            "issues": {
                "style": style_issues,
                "architecture": architecture_issues,
                "functionality": functionality_issues
            },
            "similar_code": similar_code
        }
    
    def analyze_diff(self, original_code: str, new_code: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze a code diff against learned patterns.
        
        Args:
            original_code: Original code
            new_code: New code
            file_path: Path to the file being analyzed
            
        Returns:
            Dictionary with analysis results
        """
        self.logger.info(f"Analyzing diff for {file_path}")
        
        # Analyze the new code
        analysis = self.analyze_code(new_code, file_path)
        
        # Generate diff
        diff_lines = list(difflib.unified_diff(
            original_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3
        ))
        
        diff_text = ''.join(diff_lines)
        
        # Add diff information to the analysis
        analysis["diff"] = diff_text
        
        return analysis
