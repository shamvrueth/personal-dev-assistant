import argparse
import sys
import asyncio
from mcp_client.client import MCPClient

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
        response = await client.ask(prompt)
        print(response)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())