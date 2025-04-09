import os
import re
import json
import logging
import argparse
import requests
import tempfile
import subprocess
from typing import Dict, List, Any, Optional

from review_engine.AI_code_review import AICodeReview
from review_engine.config import CodeReviewConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_review_bot")

class ReviewScores:
    """Class to calculate and format review scores."""
    
    def __init__(self, issues: List[Dict[str, Any]]):
        self.issues = issues
        self.severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2,
            "info": 0.1
        }
        
        # Category mappings
        self.maintainability_keywords = ["maintainability", "readability", "complexity", "duplication", "technical debt"]
        self.style_keywords = ["style", "formatting", "naming", "convention", "consistency"]
        self.structure_keywords = ["structure", "architecture", "design", "organization", "pattern"]
        self.performance_keywords = ["performance", "efficiency", "speed", "optimization", "memory"]
        self.security_keywords = ["security", "vulnerability", "injection", "authentication", "authorization"]
        
    def calculate_scores(self) -> Dict[str, float]:
        """Calculate scores for different categories."""
        # Initialize counters
        categories = {
            "maintainability": {"score": 0, "weight": 0},
            "style": {"score": 0, "weight": 0},
            "structure": {"score": 0, "weight": 0},
            "overall": {"score": 0, "weight": 0}
        }
        
        # Process each issue
        for issue in self.issues:
            severity = issue.get("severity", "medium").lower()
            weight = self.severity_weights.get(severity, 0.5)
            
            # Update overall score
            categories["overall"]["weight"] += weight
            categories["overall"]["score"] += weight
            
            # Determine which categories the issue belongs to
            title = issue.get("title", "").lower()
            description = issue.get("description", "").lower()
            content = title + " " + description
            
            # Check for maintainability issues
            if any(keyword in content for keyword in self.maintainability_keywords):
                categories["maintainability"]["weight"] += weight
                categories["maintainability"]["score"] += weight
            
            # Check for style issues
            if any(keyword in content for keyword in self.style_keywords):
                categories["style"]["weight"] += weight
                categories["style"]["score"] += weight
            
            # Check for structure issues
            if any(keyword in content for keyword in self.structure_keywords):
                categories["structure"]["weight"] += weight
                categories["structure"]["score"] += weight
        
        # Calculate final scores (1.0 is perfect, 0.0 is worst)
        scores = {}
        for category, data in categories.items():
            if data["weight"] > 0:
                # Inverse the score: higher weight means more issues, so lower score
                scores[category] = max(0, min(1, 1 - (data["score"] / (data["weight"] + 5))))
            else:
                scores[category] = 1.0  # Perfect score if no issues
        
        return scores
    
    def format_score_bar(self, score: float, width: int = 20) -> str:
        """Format a score as a visual bar."""
        filled = int(score * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
    
    def get_score_emoji(self, score: float) -> str:
        """Get an emoji representing a score."""
        if score >= 0.9:
            return "🟢"  # Excellent
        elif score >= 0.7:
            return "🟡"  # Good
        elif score >= 0.5:
            return "🟠"  # Fair
        else:
            return "🔴"  # Poor

class GitHubAPI:
    """Class to interact with GitHub API."""
    
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Get pull request details."""
        url = f"{self.base_url}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_pull_request_files(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get files changed in a pull request."""
        url = f"{self.base_url}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, path: str, ref: str) -> str:
        """Get file content at a specific reference."""
        url = f"{self.base_url}/contents/{path}?ref={ref}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        content_data = response.json()
        import base64
        return base64.b64decode(content_data["content"]).decode("utf-8")
    
    def comment_on_pull_request(self, pr_number: int, comment: str) -> Optional[Dict[str, Any]]:
        """Add a comment to a pull request."""
        url = f"{self.base_url}/issues/{pr_number}/comments"
        data = {"body": comment}
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print("\n==== COMMENT THAT WOULD HAVE BEEN POSTED ====")
                print(f"Pull Request #{pr_number}")
                print(comment)
                print("==== END OF COMMENT ====\n")
                print(f"Error: 403 Forbidden - Unable to post comment to PR #{pr_number}")
                print("This is likely because you don't have permission to comment on this repository.")
                return None
            else:
                raise
            
    def comment_on_pull_request_file(self, pr_number: int, commit_id: str, path: str, 
                                     line_number: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a specific line in a file in a pull request."""
        url = f"{self.base_url}/pulls/{pr_number}/comments"
        data = {
            "body": comment,
            "commit_id": commit_id,
            "path": path,
            "line": line_number,
            "side": "RIGHT"
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

class GitLabAPI:
    """Class to interact with GitLab API."""
    
    def __init__(self, token: str, project_id: str):
        self.token = token
        self.project_id = project_id
        self.base_url = f"https://gitlab.com/api/v4/projects/{project_id}"
        self.headers = {
            "PRIVATE-TOKEN": token
        }
    
    def get_merge_request(self, mr_iid: int) -> Dict[str, Any]:
        """Get merge request details."""
        url = f"{self.base_url}/merge_requests/{mr_iid}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_merge_request_changes(self, mr_iid: int) -> Dict[str, Any]:
        """Get changes in a merge request."""
        url = f"{self.base_url}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, path: str, ref: str) -> str:
        """Get file content at a specific reference."""
        url = f"{self.base_url}/repository/files/{requests.utils.quote(path, safe='')}/raw"
        params = {"ref": ref}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.text
    
    def comment_on_merge_request(self, mr_iid: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a merge request."""
        url = f"{self.base_url}/merge_requests/{mr_iid}/notes"
        data = {"body": comment}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def comment_on_merge_request_file(self, mr_iid: int, commit_id: str, path: str, 
                                     line_number: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a specific line in a file in a merge request."""
        url = f"{self.base_url}/merge_requests/{mr_iid}/discussions"
        data = {
            "body": comment,
            "position[base_sha]": commit_id,
            "position[head_sha]": commit_id,
            "position[position_type]": "text",
            "position[new_path]": path,
            "position[new_line]": line_number
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

class ReviewBot:
    """Bot to perform code reviews on PRs/MRs."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform = config.get("platform", "github")
        self.api = self._initialize_api()
        
        self.groq_api_key = config.get("groq_api_key") or os.environ.get("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("Groq API key not provided")
        
        self.vector_db_path = config.get("vector_db_path", "./vector_db")
        self.log_level = getattr(logging, config.get("log_level", "INFO"))
        
        # Set up logger
        self.logger = logger
        self.logger.setLevel(self.log_level)
    
    def _initialize_api(self) -> Any:
        """Initialize the API client based on the platform."""
        if self.platform == "github":
            token = self.config.get("token") or os.environ.get("GITHUB_TOKEN")
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            
            if not all([token, owner, repo]):
                raise ValueError("GitHub token, owner, and repo must be provided")
            
            return GitHubAPI(token, owner, repo)
        
        elif self.platform == "gitlab":
            token = self.config.get("token") or os.environ.get("GITLAB_TOKEN")
            project_id = self.config.get("project_id")
            
            if not all([token, project_id]):
                raise ValueError("GitLab token and project_id must be provided")
            
            return GitLabAPI(token, project_id)
        
        else:
            raise ValueError(f"Unsupported platform: {self.platform}")
    
    def review_pull_request(self, pr_number: int) -> None:
        """Review a GitHub pull request."""
        if self.platform == "github":
            self._review_github_pr(pr_number)
        else:
            self._review_gitlab_mr(pr_number)
    
    def _review_github_pr(self, pr_number: int) -> None:
        """Review a GitHub pull request."""
        self.logger.info(f"Reviewing GitHub PR #{pr_number}")
        
        # Get PR details
        pr = self.api.get_pull_request(pr_number)
        
        # Get files changed in the PR
        files = self.api.get_pull_request_files(pr_number)
        
        # Filter files by extension
        allowed_extensions = self.config.get("extensions", [".py", ".js", ".java", ".c", ".cpp", ".go", ".rb", ".php", ".ts"])
        files_to_review = [f for f in files if any(f["filename"].endswith(ext) for ext in allowed_extensions)]
        
        self.logger.info(f"Found {len(files_to_review)} files to review")
        
        # Clone repository to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            self.logger.info(f"Cloning repository to {temp_dir}")
            
            clone_url = pr["head"]["repo"]["clone_url"]
            branch = pr["head"]["ref"]
            
            subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, clone_url, temp_dir], check=True)
            
            # Create AI Code Review
            review_config = CodeReviewConfig(
                repo_path=temp_dir,
                groq_api_key=self.groq_api_key,
                vector_db_path=self.vector_db_path,
                log_level=self.log_level
            )
            
            ai_review = AICodeReview(review_config)
            
            # Learn repository if needed
            if self.config.get("learn_repo", True):
                self.logger.info("Learning repository...")
                ai_review.learn_repository()
            else:
                self.logger.info("Loading existing knowledge...")
                ai_review.load_knowledge()
            
            # Review each file
            all_reviews = {}
            all_issues = []
            
            for file in files_to_review:
                filename = file["filename"]
                self.logger.info(f"Reviewing {filename}")
                
                # Get file content
                try:
                    filepath = os.path.join(temp_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception as e:
                    self.logger.error(f"Error reading file {filename}: {e}")
                    continue
                
                # Review code
                review = ai_review.review_code(code, os.path.basename(filename))
                all_reviews[filename] = review
                
                # Extract issues
                if "issues" in review:
                    for issue in review["issues"]:
                        issue["file"] = filename
                        all_issues.append(issue)
            
            # Calculate scores
            score_calculator = ReviewScores(all_issues)
            scores = score_calculator.calculate_scores()
            
            # Generate summary comment
            comment = self._generate_summary_comment(scores, all_reviews)
            
            # Post summary comment
            self.api.comment_on_pull_request(pr_number, comment)
            
            # Post issue comments
            if self.config.get("comment_on_lines", False):
                self._comment_on_issues(pr_number, pr["head"]["sha"], all_reviews)
    
    def _review_gitlab_mr(self, mr_iid: int) -> None:
        """Review a GitLab merge request."""
        self.logger.info(f"Reviewing GitLab MR !{mr_iid}")
        
        # Get MR details
        mr = self.api.get_merge_request(mr_iid)
        
        # Get changes in the MR
        changes = self.api.get_merge_request_changes(mr_iid)
        
        # Filter files by extension
        allowed_extensions = self.config.get("extensions", [".py", ".js", ".java", ".c", ".cpp", ".go", ".rb", ".php", ".ts"])
        files_to_review = [f for f in changes["changes"] if any(f["new_path"].endswith(ext) for ext in allowed_extensions)]
        
        self.logger.info(f"Found {len(files_to_review)} files to review")
        
        # Clone repository to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            self.logger.info(f"Cloning repository to {temp_dir}")
            
            source_project = mr["source_project_id"]
            branch = mr["source_branch"]
            
            # Get project URL
            project_url = f"https://gitlab.com/api/v4/projects/{source_project}"
            response = requests.get(project_url, headers=self.api.headers)
            response.raise_for_status()
            project_data = response.json()
            
            clone_url = project_data["http_url_to_repo"]
            
            subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, clone_url, temp_dir], check=True)
            
            # Create AI Code Review
            review_config = CodeReviewConfig(
                repo_path=temp_dir,
                groq_api_key=self.groq_api_key,
                vector_db_path=self.vector_db_path,
                log_level=self.log_level
            )
            
            ai_review = AICodeReview(review_config)
            
            # Learn repository if needed
            if self.config.get("learn_repo", True):
                self.logger.info("Learning repository...")
                ai_review.learn_repository()
            else:
                self.logger.info("Loading existing knowledge...")
                ai_review.load_knowledge()
            
            # Review each file
            all_reviews = {}
            all_issues = []
            
            for file in files_to_review:
                filename = file["new_path"]
                self.logger.info(f"Reviewing {filename}")
                
                # Get file content
                try:
                    filepath = os.path.join(temp_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception as e:
                    self.logger.error(f"Error reading file {filename}: {e}")
                    continue
                
                # Review code
                review = ai_review.review_code(code, os.path.basename(filename))
                all_reviews[filename] = review
                
                # Extract issues
                if "issues" in review:
                    for issue in review["issues"]:
                        issue["file"] = filename
                        all_issues.append(issue)
            
            # Calculate scores
            score_calculator = ReviewScores(all_issues)
            scores = score_calculator.calculate_scores()
            
            # Generate summary comment
            comment = self._generate_summary_comment(scores, all_reviews)
            
            # Post summary comment
            self.api.comment_on_merge_request(mr_iid, comment)
            
            # Post issue comments
            if self.config.get("comment_on_lines", False):
                commit_id = changes["changes"][0]["diff_refs"]["head_sha"]
                self._comment_on_issues_gitlab(mr_iid, commit_id, all_reviews)
    
    def _generate_summary_comment(self, scores: Dict[str, float], reviews: Dict[str, Dict[str, Any]]) -> str:
        """Generate a summary comment for the PR/MR."""
        score_calculator = ReviewScores([])  # Just for score formatting
        
        # Build comment
        comment = "# 🤖 AI Code Review Summary\n\n"
        
        # Add scores
        comment += "## 📊 Review Scores\n\n"
        comment += "| Category | Score | Rating |\n"
        comment += "|----------|-------|--------|\n"
        
        for category, score in scores.items():
            emoji = score_calculator.get_score_emoji(score)
            bar = score_calculator.format_score_bar(score)
            comment += f"| **{category.capitalize()}** | `{bar}` {score:.2f}/1.0 | {emoji} |\n"
        
        comment += "\n"
        
        # Add overall summary
        total_issues = sum(len(review.get("issues", [])) for review in reviews.values())
        
        comment += f"## 📝 Summary\n\n"
        comment += f"Reviewed {len(reviews)} files and found {total_issues} issues.\n\n"
        
        # Add file summaries
        comment += "## 📂 Files Reviewed\n\n"
        
        for filename, review in reviews.items():
            issues = review.get("issues", [])
            severity_counts = {}
            
            for issue in issues:
                severity = issue.get("severity", "medium").lower()
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            severity_text = ", ".join(f"{count} {severity}" for severity, count in severity_counts.items())
            severity_text = severity_text if severity_text else "no issues"
            
            comment += f"* **{filename}**: {len(issues)} issues ({severity_text})\n"
        
        # Add top issues
        if total_issues > 0:
            comment += "\n## 🔎 Top Issues\n\n"
            
            # Sort issues by severity
            all_issues = []
            for filename, review in reviews.items():
                for issue in review.get("issues", []):
                    issue["file"] = filename
                    all_issues.append(issue)
            
            # Map severity to numeric value for sorting
            severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
            all_issues.sort(key=lambda x: severity_map.get(x.get("severity", "medium").lower(), 0), reverse=True)
            
            # Show top 5 issues
            for i, issue in enumerate(all_issues[:5]):
                severity = issue.get("severity", "medium").upper()
                title = issue.get("title", "")
                description = issue.get("description", "")
                filename = issue.get("file", "")
                
                comment += f"### {i+1}. [{severity}] {title}\n\n"
                comment += f"**File**: `{filename}`\n\n"
                comment += f"{description}\n\n"
                
                if "suggestion" in issue:
                    comment += f"**Suggestion**: {issue['suggestion']}\n\n"
        
        # Add footer
        comment += "---\n"
        comment += "This review was generated automatically by the AI Code Review Bot. "
        comment += "The scores are based on the detected issues and code patterns.\n"
        
        return comment
    
    def _comment_on_issues(self, pr_number: int, commit_id: str, reviews: Dict[str, Dict[str, Any]]) -> None:
        """Comment on specific issues in the files."""
        for filename, review in reviews.items():
            for issue in review.get("issues", []):
                # Skip low severity issues if configured
                severity = issue.get("severity", "medium").lower()
                if severity == "low" and not self.config.get("comment_on_low_severity", False):
                    continue
                
                # Try to find line number
                line_number = self._find_line_number(issue)
                if not line_number:
                    continue
                
                # Create comment
                comment = f"**{severity.upper()}**: {issue['title']}\n\n"
                comment += issue["description"]
                
                if "suggestion" in issue:
                    comment += f"\n\n**Suggestion**: {issue['suggestion']}"
                
                # Add comment to PR
                try:
                    self.api.comment_on_pull_request_file(pr_number, commit_id, filename, line_number, comment)
                    self.logger.info(f"Added comment on {filename}:{line_number}")
                except Exception as e:
                    self.logger.error(f"Failed to add comment: {e}")
    
    def _comment_on_issues_gitlab(self, mr_iid: int, commit_id: str, reviews: Dict[str, Dict[str, Any]]) -> None:
        """Comment on specific issues in the files for GitLab."""
        for filename, review in reviews.items():
            for issue in review.get("issues", []):
                # Skip low severity issues if configured
                severity = issue.get("severity", "medium").lower()
                if severity == "low" and not self.config.get("comment_on_low_severity", False):
                    continue
                
                # Try to find line number
                line_number = self._find_line_number(issue)
                if not line_number:
                    continue
                
                # Create comment
                comment = f"**{severity.upper()}**: {issue['title']}\n\n"
                comment += issue["description"]
                
                if "suggestion" in issue:
                    comment += f"\n\n**Suggestion**: {issue['suggestion']}"
                
                # Add comment to MR
                try:
                    self.api.comment_on_merge_request_file(mr_iid, commit_id, filename, line_number, comment)
                    self.logger.info(f"Added comment on {filename}:{line_number}")
                except Exception as e:
                    self.logger.error(f"Failed to add comment: {e}")
    
    def _find_line_number(self, issue: Dict[str, Any]) -> Optional[int]:
        """Try to find a line number from the issue."""
        # Check if line number is directly provided
        if "line_number" in issue:
            return issue["line_number"]
        
        # Try to find line number from code snippet
        if "code_snippet" in issue:
            lines = issue["code_snippet"].split("\n")
            if len(lines) > 0:
                # Look for line numbers in the code snippet (e.g., "Line 42: code")
                line_match = re.search(r"Line (\d+):", lines[0])
                if line_match:
                    return int(line_match.group(1))
                
                # Default to the middle of the snippet
                return len(lines) // 2
        
        return None

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)

def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="AI Code Review Bot for GitHub/GitLab")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--pr", type=int, help="Pull/Merge request number to review")
    parser.add_argument("--platform", choices=["github", "gitlab"], help="Platform (github or gitlab)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command-line arguments
    if args.platform:
        config["platform"] = args.platform
    
    # Create bot
    bot = ReviewBot(config)
    
    # Review PR/MR
    if args.pr:
        bot.review_pull_request(args.pr)
    else:
        parser.error("--pr argument is required")

if __name__ == "__main__":
    main()