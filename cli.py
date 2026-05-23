import argparse
import sys
import asyncio
from mcp_client.client import MCPClient, MCPHTTPClient
import json
from config import get_git_context

def build_prompt(args) -> str:
    if args.command == "explain":
        return (
            """
            You are executing the CLI command: explain.

            Goal:
            Provide a concise, high-level explanation of the project.

            How to work:
            - Use summarize_project to get project overview
            - Use search_relevant_code to understand key components
            - Use find_entry_points to identify startup logic

            Rules:
            - Plain text only
            - No markdown
            - No emojis
            - No speculation
            - Base your answer ONLY on tool outputs

            Format exactly:

            PROJECT
            <1-2 sentences>

            STRUCTURE
            - <top-level folders/files with short descriptions>

            ENTRY POINTS
            - <file>: <reason>

            TECH STACK
            - Frameworks: ...
            - Libraries: ...

            Do not repeat sections.
            """
        )

    if args.command == "entry":
        return (
            """
            You are executing the CLI command: entry.

            Goal:
            List execution entry points and explain why each is an entry point.

            How to work:
            - Use find_entry_points tool
            - Verify with read_file if needed

            Rules:
            - Plain text only
            - No markdown
            - Do not include unrelated files

            Format:
            - <file> -> <reason>
            """
        )

    if args.command == "find":
        symbol_query = ' '.join(args.symbol)
        return (
            f"""
            You are executing the CLI command: find.

            Goal:
            Find where '{symbol_query}' is defined and used.
            Explain its role in the project.

            How to work:
            - First, use search_code(query="{symbol_query}") for exact matches
            - Then, use search_relevant_code(query="{symbol_query}") for semantic matches
            - Combine results from both searches
            - Use read_file to get full context if needed

            Rules:
            - Plain text only
            - No markdown
            - Group results by file
            - Show line numbers when available
            - Filter out irrelevant results (build artifacts, config files)

            Format:
            FILE: <path>
            - line <n>: <snippet>
            
            Explain the role of '{symbol_query}' in the project.
            """
        )

    if args.command == "explain-file":
        return (
            f"""
            You are executing the CLI command: explain-file.

            Goal:
            Explain the file '{args.path}'.
            Include its responsibilities and how it fits into the project.

            How to work:
            - FIRST: Use read_file to read '{args.path}' (MANDATORY)
            - If file doesn't exist, respond: "ERROR: File not found: {args.path}"
            - Use search_relevant_code to find related code if needed
            - Use summarize_project for project context if needed

            Rules:
            - Plain text only
            - No markdown
            - Base explanation ONLY on actual file content
            - Never hallucinate or guess content

            Format:
            FILE
            <path>

            PURPOSE
            <4-5 sentences>

            KEY RESPONSIBILITIES
            - ...
            - ...
            """
        )
    
    if args.command == "tree":
        return (
            f"""
            You are executing the CLI command: tree.

            Goal:
            Display the project directory structure until depth = {args.depth}.

            How to work:
            - Use list_directory tool with depth parameter

            Rules:
            - Plain text only
            - Indent with two spaces per level
            - Do not explain files
            - Respect the specified depth
            """
        )
    
    if args.command == "explain-flow":
        return (
            f"""
            You are executing the CLI command: explain-flow.

            Goal:
            Explain the execution flow of the file '{args.path}'.

            How to work:
            - FIRST: Use read_file to read '{args.path}' (MANDATORY)
            - If file doesn't exist, respond: "ERROR: File not found: {args.path}"
            - Use search_relevant_code to find related flow if needed
            - Trace function calls and dependencies

            Rules:
            - Plain text only
            - No markdown
            - Explain in logical steps
            - Only analyze the specified file
            - Never hallucinate file contents

            Format:

            FILE
            <path>

            FLOW
            1. ...
            2. ...

            ROLE
            <what this file does in the project>
            """
        )
    
    if args.command == "lint":
        return (
            f"""
            You are executing the CLI command: lint.

            Goal:
            Identify real bugs, fragile logic, and correctness issues in the codebase.
            Target directory: '{args.path}' (if '.' then analyze entire codebase)

            How to work:
            1. Make MULTIPLE search_relevant_code calls (at least 5-6 searches):
               - search_relevant_code("error handling try catch exception blocks", max_results=20)
               - search_relevant_code("database connections queries SQL transactions", max_results=20)
               - search_relevant_code("file operations open read write close cleanup", max_results=20)
               - search_relevant_code("resource management memory leaks connections", max_results=20)
               - search_relevant_code("async await promises concurrent operations", max_results=20)
               - search_relevant_code("security vulnerabilities injection validation", max_results=20)
            
            2. Examine ALL results with similarity > 0.3
            
            3. Read relevant files using read_file for full context
            
            4. Analyze actual code for real issues
            
            5. Report 5-8 issues if found

            Rules:
            - Plain text only
            - No markdown
            - No stylistic nitpicks
            - Every issue must cite: exact file, exact line range, concrete code behavior
            - Focus on: bugs, resource leaks, security issues, error handling
            - Ignore build artifacts (.next, dist, node_modules)

            Output format:

            ISSUE <id>
            Type: <bug/security/resource-leak/error-handling>
            Severity: <high/medium/low>
            File: <path>
            Lines: <start-end>
            Explanation: <what's wrong>
            Why this matters: <impact>
            Suggested fix: <how to fix>
            """
        )
    
    if args.command == "optimize":
        return (
            f"""
            You are executing the CLI command: optimize.

            Goal:
            Identify performance, scalability, or architectural optimization opportunities.
            Target directory: '{args.path}' (if '.' then analyze entire codebase)

            How to work:
            1. Make MULTIPLE search_relevant_code calls (at least 5-6 searches):
               - search_relevant_code("nested loops iterations performance bottlenecks", max_results=20)
               - search_relevant_code("expensive operations training model computations", max_results=20)
               - search_relevant_code("repeated calculations redundant API calls", max_results=20)
               - search_relevant_code("large data processing memory usage", max_results=20)
               - search_relevant_code("database queries N+1 problems", max_results=20)
               - search_relevant_code("caching memoization optimization opportunities", max_results=20)
            
            2. Examine results with similarity > 0.3
            
            3. Read relevant files using read_file
            
            4. Analyze for optimization opportunities
            
            5. Provide 5-8 specific recommendations with code examples

            Rules:
            - Plain text only
            - No markdown
            - Base every suggestion on concrete evidence
            - Focus on: algorithmic improvements, caching, redundant work, resource usage
            - Ignore micro-optimizations and build artifacts

            Output format:

            SUGGESTION <number>
            Category: <Performance/Memory/I/O/Design>
            Impact: <Low/Medium/High>
            File(s): <paths>
            Evidence: <what you found>
            Current Code:
            <code snippet>
            
            Optimized Code:
            <improved code>
            
            Expected Improvement: <description>
            """
        )
    
    if args.command == "fix":
        refactor_mode = "(REFACTOR MODE ENABLED)" if args.allow_refactor else ""
        refactor_note = "- Refactoring is allowed if it improves correctness, clarity, or robustness\n" if args.allow_refactor else ""
        
        return (
            f"""
            You are executing the CLI command: fix {refactor_mode}.

            Goal:
            Generate concrete, copy-pasteable code fixes for issues.
            Target directory: '{args.path}' (if '.' then analyze entire codebase)

            How to work:
            1. Make MULTIPLE search_relevant_code calls (at least 4-5 searches):
               - search_relevant_code("bugs errors exceptions failures crashes", max_results=20)
               - search_relevant_code("security vulnerabilities XSS injection CSRF", max_results=20)
               - search_relevant_code("race conditions deadlocks concurrency issues", max_results=20)
               - search_relevant_code("memory leaks resource cleanup disposal", max_results=20)
               - search_relevant_code("null pointer undefined reference errors", max_results=20)
            
            2. Examine results with similarity > 0.3
            
            3. Read relevant files using read_file for full context
            
            4. Generate exact, copy-pasteable fixes
            
            5. Provide 3-5 fixes with before/after code

            Rules:
            - Output ONLY code changes
            - No explanations, no markdown, no commentary
            - Each fix must include exact code blocks
            - Code must be directly usable
            - MUST read files before proposing fixes
            - If no fixes possible: NO_FIXES_FOUND
            - Ignore build artifacts
            {refactor_note}
            Output format:

            FIX <id>
            FILE: <relative/path>
            REPLACE:
            <exact code to replace>

            WITH:
            <exact replacement code>

            Repeat for each fix.
            """
        )
    
    if args.command == "git-summary":
        return (
            """
            You are executing the CLI command: git-summary.

            Goal:
            Provide a concise overview of the current Git state of the project.

            Rules:
            - Plain text only
            - No markdown
            - Do not explain Git concepts
            - Do not suggest actions

            Output format:

            REPOSITORY
            - Git repo: <yes/no>
            - Branch: <branch-name>
            - Working tree: <clean/dirty>

            RECENT COMMITS
            - <hash> | <date> | <message>
            - <hash> | <date> | <message>

            SUMMARY
            Explain recent commits in a few sentences
            """
        )

    raise ValueError("Unknown command")

async def main():
    parser = argparse.ArgumentParser(
        prog="dev-assistant",
        description="Codebase Understanding Assistant (RAG-powered)"
    )

    subparser = parser.add_subparsers(dest="command", required=True)

    subparser.add_parser("explain", help="Explain the project")
    subparser.add_parser("entry", help="Show project entry points")

    find_parser = subparser.add_parser("find", help="Find a symbol or concept")
    find_parser.add_argument("symbol", nargs="+", help="Symbol, function, or concept to search for")

    explain_file = subparser.add_parser("explain-file", help="Explain a specific file")
    explain_file.add_argument("path")

    tree = subparser.add_parser("tree", help="Show project structure")
    tree.add_argument("--depth", type=int, default=4, help="Maximum directory depth (default = 4)")

    flow_parser = subparser.add_parser("explain-flow", help="Explain execution flow inside a file")
    flow_parser.add_argument("path", help="Path to the file")

    lint = subparser.add_parser("lint", help="Detect potential bugs and design issues")
    lint.add_argument("path", nargs="?", default=".", help="Optional subdirectory to lint")

    optimize = subparser.add_parser("optimize", help="Get suggestions for optimizations in code")
    optimize.add_argument("path", nargs="?", default=".", help="Optional subdirectory to optimize")

    fix = subparser.add_parser("fix", help="Get code fixes for potential bugs and optimizations")
    fix.add_argument("path", nargs="?", default=".", help="Optional subdirectory to fix")
    fix.add_argument("--allow-refactor", action="store_true", help="Allow refactoring and structural code changes")

    subparser.add_parser("git-summary", help="Get summary of github activity")

    args = parser.parse_args()
    prompt = build_prompt(args)

    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    client = MCPHTTPClient()

    try:
        git_ctx = get_git_context()
        git_info = None
        
        if git_ctx == "LOCAL_GIT":
            res = await client.read_resource("dev-assistant://commits")
            git_info = json.loads(res)

        print(f"[INFO] Executing {args.command} command...")
        
        response = await client.ask(prompt, args.command, git_info)
        print(response)

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())