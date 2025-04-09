import streamlit as st
import os
import json
import tempfile
import pandas as pd
from datetime import datetime

from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate

from review_engine.AI_code_review import AICodeReview
from review_engine.config import CodeReviewConfig

def create_temp_file(content, filename):
    """Create a temporary file with the given content and filename."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path, temp_dir

def main():
    st.set_page_config(
        page_title="AI Code Review Tool",
        page_icon="🤖",
        layout="wide",
    )

    st.title("🤖 AI Code Review Tool")
    st.markdown("""
    This tool provides intelligent code reviews by leveraging language models and your codebase knowledge.
    """)

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        vector_db_path = st.text_input("Vector DB Path", value="./vector_db")
        
        st.subheader("Mode")
        tab_selection = st.radio("Select Mode", ["Learn Repository", "Review Code"])
    
    groq_api_key = os.getenv("GROQ_API_KEY")

    if tab_selection == "Learn Repository":
        learn_repository_tab(groq_api_key, vector_db_path)
    else:
        review_code_tab(groq_api_key, vector_db_path)

def learn_repository_tab(groq_api_key, vector_db_path):
    st.header("📚 Learn Repository")
    st.markdown("""
    This mode helps the AI learn from a repository to understand coding patterns and best practices.
    """)

    repo_input_type = st.radio("Repository Source", ["GitHub URL", "Local Path"])
    
    if repo_input_type == "Local Path":
        repo_path = st.text_input("Enter the local repository path", value="")
    else:
        repo_path = st.text_input("Enter the GitHub repository URL", value="")

    if st.button("Learn Repository", key="learn_repo_button", use_container_width=True):
        if not repo_path:
            st.error("Please provide a repository path or URL.")
            return
        
        if not groq_api_key:
            st.error("Please provide a Groq API key.")
            return

        with st.spinner("Learning repository..."):
            try:
                config = CodeReviewConfig(
                    repo_path=repo_path,
                    groq_api_key=groq_api_key,
                    vector_db_path=vector_db_path,
                    log_level="INFO"
                )
                
                ai_review = AICodeReview(config)
                success = ai_review.learn_repository()
                
                if success:
                    st.success("Repository learned successfully! 🎉")
                    st.info(f"Knowledge base saved to {vector_db_path}")
                else:
                    st.error("Failed to learn repository.")
            except Exception as e:
                st.error(f"Error learning repository: {str(e)}")
    
    # Show repository learning tips
    with st.expander("Tips for Repository Learning"):
        st.markdown("""
        - For GitHub URLs, use the HTTPS clone URL (e.g., https://github.com/username/repo.git)
        - For local paths, ensure the directory exists and contains a valid git repository
        - The learning process may take several minutes depending on repository size
        - Larger repositories will require more tokens and processing time
        """)

def review_code_tab(groq_api_key, vector_db_path):
    st.header("🔍 Review Code")
    
    # Determine which tab should be active
    active_tab = 0  # Default to first tab
    if "active_tab" in st.session_state and st.session_state.active_tab == "results":
        active_tab = 1  # Set to second tab
    
    # Add tabs for different review modes - use the active_tab index
    tab1, tab2 = st.tabs(["📝 Submit Code", "🧠 Review Results"])
    
    with tab1:
        st.markdown("""
        Upload a file or paste code directly to get an AI-powered code review.
        """)

        review_type = st.radio("Select input method", ["Upload File", "Paste Code"])
        
        file_content = None
        file_name = None
        
        if review_type == "Upload File":
            uploaded_file = st.file_uploader("Choose a file", type=["py", "js", "java", "c", "cpp", "cs", "go", "rb", "php", "ts", "html", "css"])
            if uploaded_file is not None:
                file_content = uploaded_file.getvalue().decode("utf-8")
                file_name = uploaded_file.name
                # Show a preview of the file
                with st.expander("File Preview", expanded=True):
                    st.code(file_content[:1000] + ("..." if len(file_content) > 1000 else ""))
        else:
            file_name = st.text_input("Enter file name (with extension)", value="code_sample.py")
            file_content = st.text_area("Paste your code here:", height=300)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            load_repo = st.checkbox("Learn from custom repository before review")
            
            if load_repo:
                repo_input_type = st.radio("Repository Source for Context", ["Local Path", "GitHub URL"])
                if repo_input_type == "Local Path":
                    repo_path = st.text_input("Enter the local repository path for context", value="")
                else:
                    repo_path = st.text_input("Enter the GitHub repository URL for context", value="")
            else:
                repo_path = ""  # Use default or previously learned repository
        
        with col2:
            # Review depth slider
            review_depth = st.slider("Review Depth", min_value=1, max_value=5, value=3, 
                                     help="Higher values produce more detailed reviews but take longer")
            
            # Review aspects with colorful multiselect
            review_aspects = st.multiselect(
                "Select review aspects",
                ["Code Quality", "Performance", "Security", "Documentation", "Style", "Maintainability"],
                default=["Code Quality", "Performance", "Style"]
            )
        
        # Use a prominent button with custom styling
        if st.button("🔍 Generate Review", key="review_button", use_container_width=True):
            if not file_content:
                st.error("Please provide code to review.")
                return
            
            if not groq_api_key:
                st.error("Please provide a Groq API key.")
                return
            
            # Create a temporary file with the content
            try:
                # Create a temporary file with the content
                temp_file_path, temp_dir = create_temp_file(file_content, file_name)
                
                # Set repo path to the temp directory if not provided
                actual_repo_path = repo_path if repo_path else os.path.dirname(temp_file_path)
                
                config = CodeReviewConfig(
                    repo_path=actual_repo_path,
                    groq_api_key=groq_api_key,
                    vector_db_path=vector_db_path,
                    log_level="INFO",
                    review_depth=review_depth  # Pass the depth parameter
                )
                
                ai_review = AICodeReview(config)
                
                # If custom repo specified, learn it first
                if load_repo and repo_path:
                    with st.status("Learning repository..."):
                        learn_success = ai_review.learn_repository()
                        if not learn_success:
                            st.error("Failed to learn repository. Using existing knowledge.")
                
                # Load knowledge
                load_success = ai_review.load_knowledge()
                if not load_success:
                    st.warning("No existing knowledge found. Review may be less accurate.")
                
                # Review code (with progress indicator)
                with st.spinner("🔍 Analyzing code..."):
                    review_results = ai_review.review_code(file_content, file_name)
                    
                # Store results in session state
                st.session_state.review_results = review_results
                # Set active tab to results
                st.session_state.active_tab = "results"
                
                # Clean up temp files
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
                
                # Force a rerun to display the results tab
                st.rerun()
                
            except Exception as e:
                st.error(f"Error during code review: {str(e)}")
    
    with tab2:
        if "review_results" in st.session_state:
            display_enhanced_review_results(st.session_state.review_results)
        else:
            st.info("📝 Submit your code in the 'Submit Code' tab to get a review")
            
def display_enhanced_review_results(review_results):
    """Display the review results with enhanced visuals and interactive elements."""
    st.subheader("📊 Review Results")
    
    # Create a summary metrics section at the top
    col1, col2, col3 = st.columns(3)
    
    # Count issues by severity
    issues_count = {"high": 0, "medium": 0, "low": 0, "total": 0}
    
    # Process recommendations to count issues
    if "recommendations" in review_results:
        for rec in review_results["recommendations"]:
            if isinstance(rec, dict) and "severity" in rec:
                severity = rec["severity"].lower()
                if severity in issues_count:
                    issues_count[severity] += 1
                issues_count["total"] += 1
    
    # Calculate an overall score (just for demonstration)
    overall_score = 100 - (issues_count["high"] * 10 + issues_count["medium"] * 3 + issues_count["low"])
    overall_score = max(0, min(100, overall_score))  # Ensure between 0-100
    
    # Display overall score with a gauge chart
    with col1:
        st.markdown("### Overall Score")
        # Create a simple gauge visual
        score_color = "green" if overall_score >= 80 else "orange" if overall_score >= 60 else "red"
        st.markdown(f"""
        <div style="text-align:center">
            <div style="font-size:2.5rem; color:{score_color}; font-weight:bold;">
                {overall_score}/100
            </div>
            <div style="background: #e0e0e0; height:10px; border-radius:5px; margin-top:10px">
                <div style="background:{score_color}; width:{overall_score}%; height:10px; border-radius:5px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display issue counts
    with col2:
        st.markdown("### Issues Found")
        st.markdown(f"""
        <div style="text-align:center; padding:10px;">
            <div style="font-size:1.8rem; font-weight:bold;">{issues_count['total']}</div>
            <div>Total Issues</div>
            <div style="margin-top:10px; display:flex; justify-content:space-between;">
                <div style="color:red;">🔴 {issues_count['high']} High</div>
                <div style="color:orange;">🟠 {issues_count['medium']} Medium</div>
                <div style="color:#B5B50B;">🟡 {issues_count['low']} Low</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # File info
    with col3:
        if "file" in review_results:
            file_name = review_results["file"].split("/")[-1]
            file_ext = file_name.split(".")[-1] if "." in file_name else "unknown"
            
            st.markdown("### File Info")
            st.markdown(f"""
            <div style="text-align:center; padding:10px;">
                <div style="font-size:1.2rem; font-weight:bold; overflow-wrap: break-word;">{file_name}</div>
                <div>Type: {file_ext.upper()}</div>
                <div style="margin-top:5px;">
                    {datetime.now().strftime("%Y-%m-%d %H:%M")}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Add a divider
    st.markdown("---")
    
    # Create tabs for different review sections
    review_tabs = st.tabs(["📝 Recommendations", "🔍 Issues by Category", "💬 Ask Follow-up Questions"])
    
    with review_tabs[0]:  # Recommendations tab
        if "recommendations" in review_results and review_results["recommendations"]:
            # Group recommendations by type
            rec_by_type = {}
            for rec in review_results["recommendations"]:
                if isinstance(rec, dict):
                    rec_type = rec.get('type', 'other')
                    if rec_type not in rec_by_type:
                        rec_by_type[rec_type] = []
                    rec_by_type[rec_type].append(rec)
            
            # Create expandable sections for each type
            for rec_type, recs in rec_by_type.items():
                with st.expander(f"{rec_type.capitalize()} ({len(recs)})", expanded=True):
                    for i, rec in enumerate(recs, 1):
                        severity_color = {
                            "high": "red",
                            "medium": "orange",
                            "low": "#B5B50B"
                        }.get(rec.get('severity', '').lower(), "gray")
                        
                        st.markdown(f"""
                        <div style="margin-bottom:15px; padding:10px; border-left:3px solid {severity_color}; background-color:rgba(0,0,0,0.03);">
                            <div style="color:{severity_color}; font-weight:bold;">
                                {i}. {rec.get('subtype', '').replace('_', ' ').capitalize()} ({rec.get('severity', '').upper()})
                            </div>
                            <div style="margin-top:5px;"><strong>Issue:</strong> {rec.get('message', '')}</div>
                            <div style="margin-top:5px;"><strong>Suggestion:</strong> {rec.get('suggestion', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("No recommendations found in the review results.")
    
    with review_tabs[1]:  # Issues by Category tab
        if "recommendations" in review_results and review_results["recommendations"]:
            # Create expandable sections for each severity level
            for severity in ["high", "medium", "low"]:
                severity_issues = [rec for rec in review_results["recommendations"] 
                                if isinstance(rec, dict) and rec.get('severity', '').lower() == severity]
                
                if severity_issues:
                    severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}[severity]
                    with st.expander(f"{severity_icon} {severity.upper()} Priority Issues ({len(severity_issues)})", 
                                    expanded=severity=="high"):  # Auto-expand high priority
                        for i, issue in enumerate(severity_issues, 1):
                            st.markdown(f"""
                            <div style="margin-bottom:15px; padding:10px; background-color:rgba(0,0,0,0.03);">
                                <div style="font-weight:bold;">
                                    {i}. {issue.get('type', '').capitalize()}: {issue.get('subtype', '').replace('_', ' ').capitalize()}
                                </div>
                                <div style="margin-top:5px;">{issue.get('message', '')}</div>
                                <div style="margin-top:5px; font-style:italic;">{issue.get('suggestion', '')}</div>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("No issues found in the review results.")
    
    with review_tabs[2]:  # Follow-up Questions tab
        st.markdown("""
        Have questions about the review results? Ask for clarification or additional information.
        """)
        
        # Initialize chat history in session state if not already present
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        # Display chat history
        for i, (q, a) in enumerate(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(q)
            with st.chat_message("assistant"):
                st.write(a)
        
        # Input for follow-up questions
        follow_up = st.text_input("Ask a question about the code review results:", key="follow_up_input")
        
        if st.button("Submit Question", key="follow_up_button"):
            if follow_up:
                with st.spinner("Thinking..."):
                    answer = process_follow_up_question(follow_up, review_results)
                st.session_state.chat_history.append((follow_up, answer))
                # Force a rerun to display the new Q&A
                st.rerun()
                
        # Add some example questions as buttons
        st.markdown("### Example questions:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Can you explain the high priority issues in more detail?"):
                follow_up = "Can you explain the high priority issues in more detail?"
                with st.spinner("Thinking..."):
                    answer = process_follow_up_question(follow_up, review_results)
                st.session_state.chat_history.append((follow_up, answer))
                st.rerun()
        with col2:
            if st.button("How can I fix the indentation issues?"):
                follow_up = "How can I fix the indentation issues?"
                with st.spinner("Thinking..."):
                    answer = process_follow_up_question(follow_up, review_results)
                st.session_state.chat_history.append((follow_up, answer))
                st.rerun()
                
def process_follow_up_question(question, review_results):
    """Process a follow-up question about the code review results."""
    # Get the Groq API key
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not groq_api_key:
        return "API key not available. Please set the GROQ_API_KEY environment variable."
    
    try:
        # Initialize the LLM        
        llm = ChatGroq(
            model_name="llama3-70b-8192",
            api_key=groq_api_key,
            temperature=0.7
        )
        
        # Convert review results to a string representation
        review_context = json.dumps(review_results, indent=2)
        
        # Create prompt template for answering follow-up questions
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an AI code review assistant. You will be provided with code review results and a 
            follow-up question from the user. Your job is to provide a helpful, educational answer based on the 
            review context. Keep your answers concise but thorough, focusing on helping the user understand the 
            code issues and how to address them."""),
            ("user", """
            Here are the code review results:
            
            {review_context}
            
            User's question: {question}
            
            Please provide a helpful, educational answer that directly addresses the question based on the review results.
            """)
        ])
        
        # Generate answer
        chain = LLMChain(llm=llm, prompt=prompt_template)
        answer = chain.run(review_context=review_context, question=question)
        
        return answer
    
    except Exception as e:
        return f"Error processing your question: {str(e)}"

def display_review_results(review_results):
    """Display the review results in a structured format."""
    st.subheader("Review Results")
    
    # Store review results in session state to access during follow-up questions
    if "review_data" not in st.session_state:
        st.session_state.review_data = review_results
    
    # Display summary
    if "summary" in review_results:
        st.markdown("### Summary")
        st.markdown(review_results["summary"])
    
    # Display scores if available
    if "scores" in review_results:
        st.markdown("### Scores")
        scores = review_results["scores"]
        
        # Convert scores to DataFrame for display
        score_data = []
        for category, value in scores.items():
            score_data.append({"Category": category, "Score": value, "Visual": "▓" * int(value * 10)})
        
        score_df = pd.DataFrame(score_data)
        
        # Display as a table
        st.dataframe(score_df.style.hide(axis="index"), use_container_width=True)
    
    # Display issues with improved formatting
    if "issues" in review_results:
        st.markdown("### Issues")
        
        for i, issue in enumerate(review_results["issues"], 1):
            severity_color = {
                "high": "🔴",
                "medium": "🟠",
                "low": "🟡"
            }.get(issue.get('severity', '').lower(), "⚪️")
            
            issue_title = issue.get('title', issue.get('subtype', 'Issue'))
            expander_title = f"{severity_color} {i}. {issue_title}"
            
            with st.expander(expander_title):
                st.markdown(f"**Description:** {issue.get('description', '')}")
                if "code_snippet" in issue:
                    st.code(issue["code_snippet"])
                if "suggestion" in issue:
                    st.markdown(f"**Suggestion:** {issue['suggestion']}")
    
    # Display recommendations with improved formatting
    if "recommendations" in review_results:
        st.markdown("### Recommendations")
        for i, rec in enumerate(review_results["recommendations"], 1):
            if isinstance(rec, dict):
                severity_color = {
                    "high": "🔴",
                    "medium": "🟠",
                    "low": "🟡"
                }.get(rec.get('severity', '').lower(), "⚪️")
                
                # Create a better title from the type and subtype
                rec_type = rec.get('type', '').capitalize()
                rec_subtype = rec.get('subtype', '').replace('_', ' ').capitalize()
                rec_title = f"{rec_type}: {rec_subtype}" if rec_subtype else rec_type
                
                with st.expander(f"{severity_color} {i}. {rec_title}"):
                    st.markdown(f"**Issue:** {rec.get('message', '')}")
                    
                    # Display explanation if available (from enhanced LLM output)
                    if "explanation" in rec:
                        st.markdown(f"**Why this matters:** {rec['explanation']}")
                    
                    st.markdown(f"**Suggestion:** {rec.get('suggestion', '')}")
                    st.markdown(f"**Severity:** {rec.get('severity', '').capitalize()}")
            else:
                st.markdown(f"{i}. {rec}")
    
    # Additional insights
    if "insights" in review_results:
        with st.expander("Additional Insights"):
            st.markdown(review_results["insights"])
    
    # Follow-up questions section
    st.markdown("### 💬 Ask Follow-up Questions")
    
    # Initialize chat history in session state if not already present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for q, a in st.session_state.chat_history:
        st.markdown(f"**Question:** {q}")
        st.markdown(f"**Answer:** {a}")
    
    # Input for follow-up questions
    follow_up = st.text_input("Ask a question about the code review results:")
    
    if st.button("Submit Question", key="follow_up_button"):
        if follow_up:
            answer = process_follow_up_question(follow_up, review_results)
            st.session_state.chat_history.append((follow_up, answer))
            # Force a rerun to display the new Q&A
            st.rerun()

if __name__ == "__main__":
    main()