import json
from typing import Dict, Any, List

from review_engine.config import CodeReviewConfig
from review_engine.rag_engine import RAGEngine

try:
    from langchain.chains import LLMChain
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

class RecommendationGenerator:
    """Generates recommendations based on code analysis."""
    
    def __init__(self, config: CodeReviewConfig, rag_engine: RAGEngine):
        """
        Initialize the recommendation generator.
        
        Args:
            config: Configuration for the recommendation generator
            rag_engine: RAG engine for pattern retrieval
        """
        self.config = config
        self.logger = config.logger
        self.rag_engine = rag_engine
        self.llm = None
        
        # Initialize LLM if available
        if LANGCHAIN_AVAILABLE and self.config.groq_api_key:
            try:
                self.llm = ChatGroq(
                    model_name=self.config.llm_model,
                    api_key=self.config.groq_api_key,
                    temperature=0.7  # Example temperature setting
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize Groq LLM: {e}")

    def generate_recommendations(self, input_text: str) -> Dict[str, Any]:
        """
        Generate recommendations based on input text.
        
        Args:
            input_text: Text to analyze
        
        Returns:
            A dictionary containing recommendations.
        """
        if not self.llm:
            raise ValueError("LLM is not initialized.")
        
        try:
            # Define a prompt template for generating recommendations
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant for code review."),
                ("user", input_text)
            ])
            
            # Invoke the Groq model with the prompt
            result = self.llm.invoke(prompt_template)
            
            return json.loads(result.content)  # Assuming JSON output from Groq model
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return {}
    
    def generate_recommendations(self, analysis: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Generate recommendations based on code analysis.
        
        Args:
            analysis: Code analysis results
            file_path: Path to the file being analyzed
            
        Returns:
            Dictionary with recommendations
        """
        self.logger.info(f"Generating recommendations for {file_path}")
        
        # Extract issues and similar code
        issues = analysis["issues"]
        similar_code = analysis["similar_code"] if "similar_code" in analysis else []
        
        # Generate recommendations based on issues
        recommendations = []
        
        # Process style issues
        for issue in issues["style"]:
            recommendation = {
                "type": issue["type"],
                "subtype": issue["subtype"],
                "message": issue["message"],
                "suggestion": self._get_suggestion_for_issue(issue, similar_code),
                "severity": issue["severity"]
            }
            recommendations.append(recommendation)
        
        # Process architecture issues
        for issue in issues["architecture"]:
            recommendation = {
                "type": issue["type"],
                "subtype": issue["subtype"],
                "message": issue["message"],
                "suggestion": self._get_suggestion_for_issue(issue, similar_code),
                "severity": issue["severity"]
            }
            recommendations.append(recommendation)
        
        # Process functionality issues
        for issue in issues["functionality"]:
            recommendation = {
                "type": issue["type"],
                "subtype": issue["subtype"],
                "message": issue["message"],
                "suggestion": self._get_suggestion_for_issue(issue, similar_code),
                "severity": issue["severity"]
            }
            recommendations.append(recommendation)
        
        # Generate LLM recommendations if available
        if self.llm and "diff" in analysis:
            llm_recommendations = self._generate_llm_recommendations(analysis["diff"], file_path, similar_code)
            recommendations.extend(llm_recommendations)
        
        # Sort recommendations by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return {
            "file": file_path,
            "recommendations": recommendations
        }
    
    def _get_suggestion_for_issue(self, issue: Dict[str, Any], similar_code: List[Dict[str, Any]]) -> str:
        """
        Get a suggestion for an issue based on similar code.
        
        Args:
            issue: Issue to get a suggestion for
            similar_code: Similar code snippets
            
        Returns:
            Suggestion for the issue
        """
        issue_type = issue["type"]
        issue_subtype = issue["subtype"]
        
        # Default suggestions based on issue type and subtype
        suggestions = {
            "style": {
                "indentation": "Follow the project's indentation pattern.",
                "line_length": "Keep lines within the maximum length. Consider breaking long lines or using appropriate line continuation techniques.",
                "naming_convention": "Follow the project's naming convention for consistency."
            },
            "architecture": {
                "uncommon_import": "Consider if a standard library or commonly used import in the project would be more appropriate.",
                "uncommon_from_import": "Consider if a standard library or commonly used import in the project would be more appropriate.",
                "uncommon_js_import": "Consider if a standard library or commonly used import in the project would be more appropriate.",
                "error_handling": "Add appropriate error handling based on project patterns."
            },
            "functionality": {
                "logging": "Use the project's logging framework instead of print statements.",
                "testing": "Add appropriate test assertions following the project's testing patterns."
            }
        }
        
        if issue_type in suggestions and issue_subtype in suggestions[issue_type]:
            return suggestions[issue_type][issue_subtype]
        
        return "Review and adjust according to project standards."
    
    def _generate_llm_recommendations(self, diff: str, file_path: str, similar_code: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate recommendations using an LLM.
        
        Args:
            diff: Code diff
            file_path: Path to the file being analyzed
            similar_code: Similar code snippets
            
        Returns:
            List of LLM-generated recommendations
        """
        if not self.llm:
            return []
        
        self.logger.info("Generating LLM recommendations")
        
        # Prepare context from similar code
        context = ""
        if similar_code:
            context = "Similar code in the repository:\n\n"
            for idx, code in enumerate(similar_code[:3]):  # Only use top 3 similar code snippets
                context += f"Example {idx + 1} from {code['file']}:\n```\n{code['content']}\n```\n\n"
        
        # Enhanced prompt for more detailed analysis
        prompt_template = PromptTemplate(
            input_variables=["diff", "file_path", "context"],
            template="""
            You are a senior software engineer performing a detailed code review. Your reviews are known for being thorough, educational, and actionable.
            
            Analyze the following code in file {file_path}:
            ```
            {diff}
            ```
            
            {context}
            
            Perform a comprehensive review focusing on:
            1. Code quality and readability
                - Variable/function naming
                - Code structure and organization
                - Comment quality and documentation
                - Complexity and readability
            2. Performance optimizations
                - Algorithmic efficiency
                - Resource usage (memory, CPU)
                - Potential bottlenecks
            3. Security concerns
                - Input validation
                - Authentication/authorization issues
                - Data exposure risks
                - Common security vulnerabilities
            4. Bug prevention
                - Edge cases
                - Error handling
                - Input validation
                - State management
            5. Maintainability
                - Testing coverage
                - Modularity
                - Coupling and cohesion
                - Future extensibility
                
            For each issue found:
            1. Be specific about the line numbers or code sections
            2. Explain WHY it's an issue (educational component)
            3. Suggest a concrete solution with example code where appropriate
            4. Rate severity (high/medium/low)
            
            Format your response as a JSON list of recommendations:
            [
                {{
                    "type": "llm", 
                    "subtype": "specific_category",
                    "message": "Detailed issue description with line numbers",
                    "explanation": "Educational explanation of why this is an issue or best practice",
                    "suggestion": "Concrete solution with example code if applicable",
                    "severity": "high/medium/low"
                }},
                ...
            ]
            
            Provide at least 4-6 substantive recommendations that would truly help improve this code.
            """
        )
        
        # Generate recommendations
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            response = chain.run(diff=diff, file_path=file_path, context=context)
            
            # Parse JSON response
            try:
                recommendations = json.loads(response)
                if isinstance(recommendations, list):
                    return recommendations
                else:
                    self.logger.warning("LLM response is not a list")
                    return []
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON: {response[:100]}...")
                return []
        except Exception as e:
            self.logger.error(f"Failed to generate LLM recommendations: {e}")
            return []