import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
import re
import asyncio
from mcp.server.fastmcp.prompts import base
from system_prompt import SYSTEM_PROMPT
from openai import OpenAI
import json
import inspect

load_dotenv()
mcp = FastMCP("PersonalDevAssistant", log_level="ERROR")
openai = OpenAI()

WORKSPACE_ROOT = os.getenv("MCP_WORKSPACE")

assert WORKSPACE_ROOT, "Error: MCP_WORKSPACE cannot be empty. Update .env"
WORKSPACE_ROOT = Path(WORKSPACE_ROOT).resolve()

BINARY_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".zip", ".tar", ".gz", ".exe", ".dll",
    ".docx", ".pptx", ".xlsx"
}

EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".cache",
    "dist", "build", "target", "out", "coverage", ".idea", ".vscode",
}

VENV_MARKERS = {"site-packages", "Lib", "Scripts", "bin", "Include"}

MAX_FILE_SIZE = 300_000  # 300 KB
MAX_FILES_SCANNED = 300
MAX_LINES_READ = 100

ENTRY_PATTERNS = {
    "python": "__name__ == \"__main__\"",
    "c": "int main(",
    "cpp": "int main(",
    "java": "static void main(",
    "go": "func main()",
    "rust": "fn main()",
    "csharp": "static void Main(",
    "javascript": "require.main === module",
}

COMMON_ENTRY_NAMES = {"main", "index", "app", "server"}


@mcp.tool(
    name="read_file",
    description="Read the contents of a text file inside the configured workspace"
)
async def read_file(
    path: str = Field(description="Relative path to the file inside the workspace"),
    ctx: Context = None
) -> str:
    
    file_path = (WORKSPACE_ROOT / path).resolve()
    await ctx.info(f"Reading file: {path}")

    if not str(file_path).startswith(str(WORKSPACE_ROOT)):
        raise ValueError("Access Denied: Path outside workspace")
    
    if not file_path.exists():
        raise ValueError(f"File not found: {path}")
    
    if not file_path.is_file():
        raise ValueError(f"Not a file: {path}")
    
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        raise ValueError(f"Binary file type '{file_path.suffix}' is not supported by read_file")
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        await ctx.info(f"Read {len(content)} characters from file")
        return content
    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")
    

@mcp.tool(
    name="list_directory",
    description="List files and subdirectories inside a directory in the workspace"
)
async def list_directory(
    path: str = Field(
        default=".",
        description="Relative path of directory inside the workspace (default: workspace root)"
    ),
    ctx: Context = None
) -> List[Dict]:
    
    dir = (WORKSPACE_ROOT / path).resolve()
    await ctx.info(f"Listing directory: {dir}")

    if not str(dir).startswith(str(WORKSPACE_ROOT)):
        raise ValueError("Access Denied: Path outside workspace")

    if not dir.exists():
        raise ValueError(f"Directory not found: {path}")
    
    if not dir.is_dir():
        raise ValueError(f"Not a directory: {path}")

    res = []
    for entry in dir.iterdir():
        try:
            relative_path = entry.relative_to(WORKSPACE_ROOT)
            res.append({
                    "name": entry.name,
                    "path": str(relative_path),
                    "type": "directory" if entry.is_dir() else "file",
                    "size": str(entry.stat().st_size) + " bytes" if entry.is_file() else None
                })
        except Exception:
            continue # skip unreadable paths
    
    await ctx.info(f"Found {len(res)} items in directory")
    return res


@mcp.tool(
    name="search_code",
    description="Search for a text pattern across all the files in the workspace"
)
async def search_code(
    query: str = Field(description="Text to search for"),
    path: str = Field(
        default=".",
        description="Relative directory to search in (default: workspace root)"
    ),
    max_results: int = Field(
        default=50,
        description="Maximum number of results to return"
    ),
    ctx: Context = None
) -> List[Dict]:
    
    await ctx.info(f"Searching project for '{query}'")

    # normalize query to get meaningful tokens (to support multiline queries)
    re.sub(r'\(.*\)', '', query) # in functions remove '()' funcname() -> func
    tokens = set(
        t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query)
        if len(t) > 2
    )

    if not tokens:
        raise ValueError("Query does not contain searchable tokens")
    
    fs = 0
    search_path = (WORKSPACE_ROOT / path).resolve()
    if not str(search_path).startswith(str(WORKSPACE_ROOT)):
        raise ValueError("Access Denied: Path outside workspace")
    
    if not search_path.exists():
        raise ValueError(f"Directory not found: {path}")
    
    res = []
    for fp in search_path.rglob("*"):
        if fs >= MAX_FILES_SCANNED:
            break

        if any(part in EXCLUDED_DIRS for part in fp.parts):
            continue

        if len(res) >= max_results:
            break

        if not fp.is_file(): # skip non files
            continue

        if fp.suffix.lower() in BINARY_EXTENSIONS: # skip files which cannot be read normally
            continue

        try:
            if fp.stat().st_size > MAX_FILE_SIZE:
                continue
        except Exception:
            continue
        
        fs += 1
        if (fs % 100 == 0):
            await ctx.info(f"Scanned {fs} files…")
        try:
            with fp.open("r", encoding="utf-8", errors="ignore") as f:
                for n, line in enumerate(f, start=1):
                    if any(token in line for token in tokens):
                        res.append({
                            "file": str(fp.relative_to(WORKSPACE_ROOT)),
                            "line": n,
                            "snippet": line.strip(),
                            "matched_tokens": [t for t in tokens if t in line]
                        })
                        if len(res) >= max_results:
                            break
        except Exception:
            continue
    
    await ctx.info(f"Search complete. Found {len(res)} matches.")
    return res


@mcp.tool(
    name="project_tree",
    description="Get a tree view of the project structure"
)
async def project_tree(
    max_depth: int = Field(
        default=4,
        description="Maximum directory depth to include"
    ),
    ctx: Context = None
) -> Dict:
    await ctx.info("Scanning the directory for getting project root..")
    # recursive function which works till max depth is reached
    def walk(dir_path: Path, depth: int):
        if depth > max_depth:
            return None
        
        tree = {}
        try:
            for entry in dir_path.iterdir():
                if entry.is_dir():
                    subtree = walk(entry, depth + 1)
                    tree[entry.name + "/"] = subtree if subtree else {}
                else:
                    tree[entry.name] = None
        except Exception:
            pass

        return tree
    
    return walk(WORKSPACE_ROOT, 1)



@mcp.tool(
    name="find_entry_points",
    description="Identify likely execution entry points"
)
async def find_entry_points(ctx: Context) -> List[Dict]:

    await ctx.info("Scanning project for entry points")
    entry_points = []
    fs = 0

    for path in WORKSPACE_ROOT.rglob("*"):
        parts = set(path.parts)
        
        if fs >= MAX_FILES_SCANNED:
            break
        
        if "site-packages" in parts:
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        if not path.is_file():
            continue

        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        
        fs += 1
        rel_path = str(path.relative_to(WORKSPACE_ROOT))
        stem = path.stem.lower()

        if stem in COMMON_ENTRY_NAMES:
            entry_points.append({
                "file": rel_path,
                "reason": "Common entry filename"
            })
    
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                head = "".join(
                    f.readline() for _ in range(MAX_LINES_READ)
                )

            for lang, pattern in ENTRY_PATTERNS.items():
                if pattern in head:
                    entry_points.append({
                        "file": rel_path,
                        "reason": f"Contains {lang} entry point pattern"
                    })
        except Exception:
            continue

        if len(entry_points) >= 10:
            break
    
    await ctx.info(f"Detected {len(entry_points)} possible entry points")
    return entry_points



@mcp.tool(
    name="summarize_project",
    description="Return high-level structured information about the project for explanation"
)
async def summarize_project(ctx: Context) -> Dict:

    await ctx.info("Collecting top-level structure")
    project_name = WORKSPACE_ROOT.name
    items = []
    for path in WORKSPACE_ROOT.iterdir():
        if path.name.startswith("."):
            continue
        items.append(path.name + ("/" if path.is_dir() else ""))

    key_files = []
    for name in (
        "README.md", "README.txt", "pyproject.toml", "requirements.txt",
        "package.json", "pom.xml", "build.gradle", "Makefile",
    ):
        candidate = WORKSPACE_ROOT / name
        if candidate.exists():
            key_files.append(name)
    
    extensions = set()
    for path in WORKSPACE_ROOT.rglob("*"):
        if path.is_file() and path.suffix:
            extensions.add(path.suffix.lower())

        if len(extensions) >= 10:
            break
    
    entry_points = find_entry_points()

    return {
        "project_name": project_name,
        "top_level_structure": sorted(items),
        "key_files": key_files,
        "file_extensions": sorted(extensions),
        "entry_points": entry_points,
    }

@mcp.tool(
    name="query",
    description="Orchestrate codebase analysis tasks using internal reasoning and available tools"
)
async def query(
    question: str = Field(description="User's question about the project"),
    ctx: Context = None
) -> str:
    await ctx.info("Starting agentic query...")

    tool_schemas = []
    tools_list = await mcp.list_tools()

    for tool in tools_list:
        if tool.name == "query":
            continue  # never expose itself

        tool_schemas.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            }
        })

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    MAX_STEPS = 20

    for step in range(MAX_STEPS):
        await ctx.info(f"Agent reasoning step {step + 1}")

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            await ctx.info("Agent produced final answer")
            return msg.content or "No answer generated."

        messages.append(msg)

        for call in msg.tool_calls:
            tool_name = call.function.name
            args = json.loads(call.function.arguments)

            await ctx.info(f"Calling tool: {tool_name}({args})")

            try:
                # use the internal tool registry
                result = await mcp.call_tool(tool_name, args)
                if inspect.iscoroutine(result):
                    result = await result
            except Exception as e:
                result = f"Error calling tool '{tool_name}': {str(e)}"

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })
    await ctx.info("Agent stopped due to step limit")
    return "I could not fully answer the question within the allowed reasoning steps."



@mcp.prompt(
    name="assistant",
    description="General-purpose codebase assistant"
)
def assistant_prompt(query: str) -> list[base.Message]:
    return [
        base.UserMessage(
            content=SYSTEM_PROMPT
        ),
        base.UserMessage(
            content=query
        ),
    ]

if __name__ == "__main__":
    mcp.run(transport="stdio")

# {"jsonrpc": "2.0", "method": "tools/call", "params": {"_meta": {"progressToken": "abc123"}, "name": "read_file", "arguments": {"path": "app/main.py"}}, "id": 3}