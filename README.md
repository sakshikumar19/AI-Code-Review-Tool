# Repositories and Code to Test Your AI Code Review Tool

To thoroughly test your AI Code Review Tool, you should try it with different types of repositories and code files. Here are some recommendations:

## Repository Types to Test

1. **Python Projects**

   - Web frameworks (Django, Flask)
   - Data science libraries
   - CLI applications
   - Medium-sized open-source packages (1000-5000 lines)

2. **JavaScript/TypeScript Projects**

   - React applications
   - Node.js backends
   - Full-stack applications
   - NPM packages

3. **Mixed Language Repositories**
   - Full-stack applications with frontend and backend code
   - Projects with multiple programming languages

## Specific Repositories to Consider

- **Small to Medium Open Source Projects**:
  - `requests` (Python HTTP library)
  - `express` (Node.js web framework)
  - `pandas` (Python data analysis library)
  - Your own projects where you know the codebase well

## Code Files to Test Against

1. **Well-formed code files** that follow the project's conventions
2. **Code files with intentional style inconsistencies**:
   - Mixed indentation (spaces vs tabs)
   - Different naming conventions
   - Inconsistent formatting
3. **Code with architectural issues**:
   - Unusual import patterns
   - Circular dependencies
   - Violations of project structure
4. **Code with functional issues**:
   - Missing error handling
   - Inconsistent logging
   - Incomplete tests

## Testing Approach

1. **Baseline Test**: Run the tool on a file that already follows all conventions
2. **Style Test**: Create a PR with style issues (spacing, naming, etc.)
3. **Architecture Test**: Add code that imports unusual libraries or structures data differently
4. **Integration Test**: Test on real PRs if you have access to a development workflow

## Practical Example

You could:

1. Clone a well-maintained project like `requests`
2. Run your tool to learn the repository patterns
3. Create a copy of an existing file with intentional modifications:
   - Change indentation from 4 spaces to 2
   - Convert snake_case variables to camelCase
   - Remove error handling
   - Use print() instead of the project's logging system
4. Run your review tool on this modified file

This approach will help you validate that your tool correctly identifies various types of issues across different programming languages and project structures.
