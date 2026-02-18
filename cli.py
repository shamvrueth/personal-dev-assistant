import argparse
import sys
import asyncio
from mcp_client.client import MCPClient
import json

def build_prompt(args) -> str:
    if args.command == "explain":
        return (
            """
            You are executing the CLI command: explain.

            Goal:
            Provide a concise, high-level explanation of the project.

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

            Rules:
            - Plain text only
            - No markdown
            - Do not include unrelated files

            Format:
            - <file> -> <reason>
            """
        )

    if args.command == "find":
        return (
            "You are executing the CLI command: find.\n"
            f"Goal: Find where '{args.symbol}' is defined and used.\n"
            "Explain its role in the project.\n"
            """Rules:
            - Plain text only
            - No markdown
            - Group results by file
            - Show line numbers when available\n
            """
            """Format:
            FILE: <path>
            - line <n>: <snippet>
            """
        )

    if args.command == "explain-file":
        return (
            "You are executing the CLI command: explain-file.\n"
            f"Goal: Explain the file '{args.path}'.\n"
            "Include its responsibilities and how it fits into the project.\n"
            """
            Rules:
            - Plain text only
            - No markdown
            - Base explanation only on the file content and project context

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
            "You are executing the CLI command: tree.\n\n"
            "Goal:\n"
            f"Display the project directory structure until depth = {args.depth}.\n\n"
            "Rules:\n"
            "- Plain text only\n"
            "- Indent with two spaces per level\n"
            "- Do not explain files\n"
            "- Respect the specified depth\n"
        )
    
    if args.command == "explain-flow":
        return (
            f"""You are executing the CLI command: explain-flow.

                Goal:
                Explain the execution flow of the file '{args.path}'.

                Rules:
                - Plain text only
                - No markdown
                - Explain in logical steps
                - Do not speculate beyond file contents

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

            How to work:
            - You are provided with a signal summary and symbol-level hints
            - Use signals ONLY to decide which files matter
            - You MUST read relevant files using read_file before making claims
            - Do NOT rely on signal text alone
            - If you do not read a file, you must not mention it

            Rules:
            - Plain text only
            - No markdown
            - No stylistic or formatting nitpicks
            - No speculative issues
            - Every issue must cite:
            - exact file
            - exact line range
            - concrete code behavior

            Process:
            1. Review signals
            2. Select relevant files
            3. Call read_file
            4. Analyze actual code
            5. Report findings

            Output format:

            ISSUE <id>
            Type:
            Severity:
            File:
            Lines:
            Explanation:
            Why this matters:
            Suggested fix:

            """
        )
    
    if args.command == "optimize":
        return (
            f"""
            You are executing the CLI command: optimize.

            Goal:
            Identify performance, memory, scalability, or efficiency improvements.

            How to work:
            - Signals indicate possible hotspots only
            - You MUST read the relevant files using read_file before suggesting changes
            - Do NOT infer behavior from method names alone
            - Base conclusions on actual code paths and execution context

            Optimization scope:
            - Repeated expensive operations
            - Avoidable recomputation
            - Inefficient data flow
            - Resource misuse (IO, memory, CPU, GPU)
            - Poor lifecycle management (models, files, connections)

            Rules:
            - Plain text only
            - No hypothetical optimizations
            - No framework-specific assumptions unless visible in code
            - If no real optimization exists, say so clearly

            Output format:

            SUGGESTION <id>
            Category:
            Impact:
            File:
            Lines:
            Observed behavior:
            Why it is inefficient:
            Concrete improvement:

            """
        )
    
    if args.command == "fix":
        if args.allow_refactor:
            return (
                f"""
                You are executing the CLI command: fix (REFRACTOR MODE ENABLED).

                Goal:
                Generate concrete, copy-pasteable code fixes and refactors.

                Rules:
                - Output ONLY code changes
                - No explanations, no markdown, no commentary
                - Each fix must include exact code blocks
                - Code must be directly usable by the developer
                - Refactoring is allowed if it improves correctness, clarity, or robustness
                - If behavior changes, ensure backward compatibility
                - You MUST call read_file on relevant files before proposing any fix
                - If you have not read at least one file, you MUST NOT produce an answer
                - If genuinely there are no improvements, respond with: NO_FIXES_FOUND
                - Do NOT invent files or symbols

                Output format:

                FIX <id>
                FILE: <relative/path>
                REPLACE:
                <exact code to replace>

                WITH:
                <exact replacement code>

                Repeat for each fix."""
            )
        else:
            return (
                f"""
                You are executing the CLI command: fix.

                Goal:
                Generate concrete, copy-pasteable code fixes for real correctness issues.

                Rules:
                - Output ONLY code changes
                - No explanations, no markdown, no commentary
                - Each fix must include exact code blocks
                - Code must be directly usable by the developer
                - If a fix spans multiple files, include separate code blocks
                - Do NOT invent files or symbols
                - Use read_file to get full context before proposing changes
                - If no safe fix exists, output: NO_FIXES_FOUND

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

    raise ValueError("Unknown command")

async def main():
    parser = argparse.ArgumentParser(
        prog="dev-assistant",
        description="Codebase Understanding Assistant"
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

    args = parser.parse_args()
    prompt = build_prompt(args)

    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    client = MCPClient(
        command="uv",
        args=["run", "mcp_server/server.py"]
    )

    try:
        signals = None
        obj = None
        if args.command == "lint":
            path_arg = args.path if args.path else "."
            signals = await client.call_tool("lint", {"path": path_arg})
        
        elif args.command == "optimize":
            path_arg = args.path if args.path else "."
            signals = await client.call_tool("optimize", {"path": path_arg})

        elif args.command == "fix":
            path_arg = args.path if args.path else "."
            signals = await client.call_tool("fix", {"path": path_arg})

        # print(f"DEBUG: Type: {type(signals)}")
        # print(f"DEBUG: Signals: {signals}")
        if signals is not None:
            res = json.loads(signals)
            obj = json.dumps(res)
        # print(obj)
        response = await client.ask(prompt, args.command, obj)
        print(response)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())