import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
import re
import sys
from mcp.server.fastmcp.prompts import base
from system_prompt import SYSTEM_PROMPT
from openai import OpenAI
import json
import inspect
# from raw_signal import collect_signals
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedder import get_embedder
import subprocess

load_dotenv()
mcp = FastMCP("PersonalDevAssistant", log_level="ERROR")
openai = OpenAI()

_ws = os.getenv("MCP_WORKSPACE")
WORKSPACE_ROOT: Path | None = Path(_ws).resolve() if _ws else None

def _ws_root() -> Path:
    if WORKSPACE_ROOT is None:
        raise ValueError("Workspace not set. Use /workspace/set in the app first.")
    return WORKSPACE_ROOT


@mcp.tool(
    name="set_workspace",
    description="Update the workspace root used by all tools"
)
async def set_workspace_tool(
    path: str = Field(description="Absolute path to the new workspace directory"),
    ctx: Context = None
) -> str:
    global WORKSPACE_ROOT
    new_path = Path(path).resolve()
    if not new_path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not new_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    WORKSPACE_ROOT = new_path
    if ctx:
        await ctx.info(f"Workspace updated to: {WORKSPACE_ROOT}")
    return str(WORKSPACE_ROOT)


BINARY_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".zip", ".tar", ".gz", ".exe", ".dll",
    ".docx", ".pptx", ".xlsx", ".svg"
}

EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".cache",
    "dist", "build", "target", "out", "coverage", ".idea", ".vscode",
    "site-packages", "Lib", "Scripts", "bin", "Include"
}

VENV_MARKERS = {"site-packages", "Lib", "Scripts", "bin", "Include"}

MAX_FILE_SIZE = 300_000  # 300 KB
MAX_FILES_SCANNED = 300
MAX_LINES_READ = 100

ENTRY_PATTERNS = {
    "python_main": "if __name__ == \"__main__\"",
    "python_main_alt": "if __name__ == '__main__'",
    "c_cpp": "int main(",
    "java": "public static void main(",
    "go": "func main()",
    "rust": "fn main()",
    "csharp": "static void Main(",
    "javascript_module": "require.main === module",
    "express": "app.listen(",
    "fastapi": "uvicorn.run(",
    "flask": "app.run(",
    "django": "execute_from_command_line(",
    "react": "ReactDOM.render(",
    "nextjs": "export default function",
}

ALLOWED_EXTENSIONS = {
    ".py", ".pyw", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", 
    ".java", ".kt", ".kts", ".scala", ".groovy", ".c", ".h", ".cpp",
    ".cc", ".cxx", ".hpp", ".hxx", ".cs", ".fs", ".fsx", ".vb", ".go", ".rs",
    ".rb", ".php", ".swift", ".m", ".mm", ".r", ".R", ".dart", ".lua", 
    ".ex", ".exs", ".erl", ".hs"
}

COMMON_ENTRY_NAMES = {
    "main", "index", "app", "server", "start",
    "__main__", "run", "cli", "manage",
    "entry", "bootstrap",
    "wsgi", "asgi",
}

COMMAND_TOOL_ALLOWLIST = {
    "explain-flow": {"read_file", "find_entry_points", "search_relevant_code"},
    "entry": {"find_entry_points", "read_file"},
    "explain": {"summarize_project", "read_file", "find_entry_points", "search_relevant_code"},
    "find": {"search_code", "search_relevant_code"},
    "lint": {"read_file", "search_relevant_code"},
    "optimize": {"read_file", "search_relevant_code"},
    "explain-file": {"read_file", "search_code", "search_relevant_code"},
    "tree": {"list_directory"},
    "fix": {"read_file", "search_relevant_code"}
}

# _SIGNAL_CACHE = None

@mcp.tool(
    name="read_file",
    description="Read the contents of a text file inside the configured workspace"
)
async def read_file(
    path: str = Field(description="Relative path to the file inside the workspace"),
    ctx: Context = None
) -> str:
    
    ws = _ws_root()
    file_path = (ws / path).resolve()
    await ctx.info(f"Reading file: {path}")

    if not str(file_path).startswith(str(ws)):
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
    
    ws = _ws_root()
    dir = (ws / path).resolve()
    await ctx.info(f"Listing directory: {dir}")

    if not str(dir).startswith(str(ws)):
        raise ValueError("Access Denied: Path outside workspace")

    if not dir.exists():
        raise ValueError(f"Directory not found: {path}")

    if not dir.is_dir():
        raise ValueError(f"Not a directory: {path}")

    res = []
    for entry in dir.iterdir():
        try:
            relative_path = entry.relative_to(ws)
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
    description="Search for exact text pattern across all files (case-insensitive)"
)
async def search_code(
    query: str = Field(description="Text to search for"),
    path: str = Field(default=".", description="Directory to search in"),
    max_results: int = 50,
    raw: bool = False,
    ctx: Context = None
) -> List[Dict]:
    
    query_lower = query.lower()
    
    if not query or len(query.strip()) == 0:
        return []
    
    if not re.search(r'[A-Za-z0-9_]', query):
        return []
    
    fs = 0
    ws = _ws_root()
    search_path = (ws / path).resolve()
    if not str(search_path).startswith(str(ws)):
        raise ValueError("Access Denied: Path outside workspace")
    
    if not search_path.exists():
        raise ValueError(f"Directory not found: {path}")
    
    res = []
    for fp in search_path.rglob("*"):
        if fs >= MAX_FILES_SCANNED:
            break

        normalized = str(fp).replace("\\", "/")
        
        # Skip excluded directories including .next
        if any(seg in normalized for seg in EXCLUDED_DIRS):
            continue

        if len(res) >= max_results:
            break

        if not fp.is_file():
            continue

        if fp.suffix.lower() in BINARY_EXTENSIONS:
            continue

        if fp.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        try:
            if fp.stat().st_size > MAX_FILE_SIZE:
                continue
        except Exception:
            continue
        
        fs += 1
        
        try:
            with fp.open("r", encoding="utf-8", errors="ignore") as f:
                for n, line in enumerate(f, start=1):
                    line_lower = line.lower()
                    
                    # Skip comments
                    if line.strip().startswith("#"):
                        continue
                    
                    # Case-insensitive matching
                    if query_lower in line_lower:
                        res.append({
                            "file": str(fp.relative_to(ws)),
                            "line": n,
                            "snippet": line.strip(),
                        })
                        if len(res) >= max_results:
                            break
        except Exception:
            continue
    
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
    
    return walk(_ws_root(), 1)



@mcp.tool(
    name="find_entry_points",
    description="Identify likely execution entry points in the project"
)
async def find_entry_points(ctx: Context) -> List[Dict]:

    await ctx.info("Scanning project for entry points")
    entry_points = []
    seen_files = set()
    fs = 0

    ws = _ws_root()

    # Check package.json first
    package_json = ws / "package.json"
    if package_json.exists():
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

                if "main" in data:
                    entry_points.append({
                        "file": data["main"],
                        "reason": f"package.json 'main' field",
                        "type": "package_main"
                    })

                if "scripts" in data:
                    for script_name, script_cmd in data["scripts"].items():
                        if script_name in ["start", "dev", "serve", "main"]:
                            entry_points.append({
                                "file": "package.json",
                                "reason": f"npm script '{script_name}': {script_cmd}",
                                "type": "npm_script"
                            })
        except Exception:
            pass

    # Scan files
    for path in ws.rglob("*"):
        if fs >= MAX_FILES_SCANNED:
            break

        # Skip excluded directories (including .next)
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        
        normalized = str(path).replace("\\", "/")
        if any(seg in normalized for seg in EXCLUDED_DIRS):
            continue

        if not path.is_file():
            continue

        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        fs += 1
        rel_path = str(path.relative_to(ws))
        
        if rel_path in seen_files:
            continue

        stem = path.stem.lower()

        # Check for common entry filenames
        if stem in COMMON_ENTRY_NAMES:
            entry_points.append({
                "file": rel_path,
                "reason": f"Common entry filename: '{stem}{path.suffix}'",
                "type": "common_name"
            })
            seen_files.add(rel_path)
            continue

        # Check file content for entry patterns
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                head = "".join([f.readline() for _ in range(50)])

            for lang, pattern in ENTRY_PATTERNS.items():
                if pattern in head:
                    entry_points.append({
                        "file": rel_path,
                        "reason": f"Contains {lang} entry pattern: '{pattern}'",
                        "type": "code_pattern"
                    })
                    seen_files.add(rel_path)
                    break

        except Exception:
            continue

        if len(entry_points) >= 15:
            break
    
    await ctx.info(f"Detected {len(entry_points)} possible entry points")
    return entry_points



@mcp.tool(
    name="summarize_project",
    description="Return high-level structured information about the project for explanation"
)
async def summarize_project(ctx: Context) -> Dict:

    await ctx.info("Collecting top-level structure")
    ws = _ws_root()
    project_name = ws.name
    items = []
    for path in ws.iterdir():
        if path.name.startswith("."):
            continue
        items.append(path.name + ("/" if path.is_dir() else ""))

    key_files = []
    for name in (
        "README.md", "README.txt", "pyproject.toml", "requirements.txt",
        "package.json", "pom.xml", "build.gradle", "Makefile",
    ):
        candidate = ws / name
        if candidate.exists():
            key_files.append(name)

    extensions = set()
    for path in ws.rglob("*"):
        if path.is_file() and path.suffix:
            extensions.add(path.suffix.lower())

        if len(extensions) >= 10:
            break
    
    # entry_points = await find_entry_points()

    return {
        "project_name": project_name,
        "top_level_structure": sorted(items),
        "key_files": key_files,
        "file_extensions": sorted(extensions),
        # "entry_points": entry_points,
    }


@mcp.tool(
    name="lint",
    description="Detect potential bugs and design issues in the codebase"
)
async def lint(
    path: str = Field(default="."),
):
    return {
        "message": "Lint analysis requested",
        "path": path
    }


@mcp.tool(
    name="optimize",
    description="Collect optimization related signals from codebase"
)
async def optimize(
    path: str = Field(default="."),
):
    return {
        "message": "Optimize analysis requested",
        "path": path
    }


@mcp.tool(
    name="fix",
    description="Collect correctness-related signals for bug fixing"
)
async def fix(
    path: str = Field(default="."),
):
    return {
        "message": "Fix analysis requested",
        "path": path
    }


@mcp.tool(
    name="query",
    description="Orchestrate codebase analysis tasks using internal reasoning and available tools"
)
async def query(
    question: str = Field(description="User's question about the project"),
    command: str = Field(description="The requested command"),
    # signals: dict | None = Field(
    #     default=None,
    #     description="Optional precomputed analysis signals (used by lint)"
    # ),
    git_info: dict | None = None, 
    ctx: Context = None
) -> str:
    await ctx.info("Starting agentic query...")

    tool_schemas = []
    tools_list = await mcp.list_tools()
    allowed = COMMAND_TOOL_ALLOWLIST.get(command, set())

    for tool in tools_list:
        if tool.name == "query":
            continue  # never expose itself
            
        if tool.name in allowed:
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
    ]
    
    # Add command-specific guidance
    if command in ["lint", "optimize", "fix"]:
        messages.append({
            "role": "system",
            "content": (
                f"You are performing a '{command}' analysis.\n\n"
                "Use search_relevant_code tool to find relevant code chunks.\n"
                "Make 3-5 targeted searches to comprehensively analyze the codebase.\n\n"
                f"Recommended search queries for {command}:\n" +
                get_recommended_searches(command)
            )
        })
    
    if git_info:
        messages.append({
            "role": "system",
            "content": (
                "Additional Git context is provided below. "
                "Use it only if relevant.\n\n"
                f"{json.dumps(git_info, indent=2)}"
            )
        })

    messages.append({"role": "user", "content": question})

    MAX_STEPS = 20

    for step in range(MAX_STEPS):
        await ctx.info(f"Agent reasoning step {step + 1}")

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0.2
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

def get_recommended_searches(command: str) -> str:
    recommendations = {
        "lint": """
        1. search_relevant_code("error handling try catch exception blocks")
        2. search_relevant_code("database connections queries SQL transactions")
        3. search_relevant_code("file operations open read write close cleanup")
        4. search_relevant_code("resource management memory leaks connections")
        5. search_relevant_code("async await promises concurrent threading")
        6. search_relevant_code("security vulnerabilities injection validation")
        """,
        "optimize": """
        1. search_relevant_code("nested loops iterations performance bottlenecks")
        2. search_relevant_code("expensive operations training model computations")
        3. search_relevant_code("repeated calculations redundant API calls")
        4. search_relevant_code("large data processing memory usage")
        5. search_relevant_code("database queries N+1 problems")
        6. search_relevant_code("caching memoization optimization opportunities")
        """,
        "fix": """
        1. search_relevant_code("bugs errors exceptions failures crashes")
        2. search_relevant_code("security vulnerabilities XSS injection CSRF")
        3. search_relevant_code("race conditions deadlocks concurrency issues")
        4. search_relevant_code("memory leaks resource cleanup disposal")
        5. search_relevant_code("null pointer undefined reference errors")
        6. search_relevant_code("type errors validation inconsistencies")
        """
    }
    return recommendations.get(command, "Use search_relevant_code to find relevant code.")

# @mcp.resource(
#     uri="dev-assistant://signals",
#     description="Cached high-level directory structure of the workspace"
# )
# async def analysis_signals() -> dict:
#     global _SIGNAL_CACHE
#     if _SIGNAL_CACHE is not None:
#         return _SIGNAL_CACHE
    
#     async def search_wrapper(query: str, path_override: str = "."):
#         return await search_code(
#             query=query,
#             path=path_override,
#         )
    
#     signals = await collect_signals(search_fn=search_wrapper, base_path=".")
#     _SIGNAL_CACHE = signals
#     return json.dumps(signals)

@mcp.tool(
    name="search_relevant_code",
    description="Find code chunks semantically relevant to a natural language query. Use this for lint, optimize, and fix commands instead of scanning entire codebase."
)
async def search_relevant_code(
    query: str = Field(description="Natural language description of code to find"),
    max_results: int = Field(default=15, description="Maximum results to return"),
    ctx: Context = None
):
    await ctx.info(f"Searching for: {query}")
    
    try:
        embedder = get_embedder(WORKSPACE_ROOT)
        results = embedder.search_relevant_code(query, n_results=max_results)

        # print(f"FOUND: {len(results)} chunks")  # debug
        # if results:
        #     print(f"   Top 3: {[r['file'] for r in results[:3]]}")

        # await ctx.info(f"Found {len(results)} relevant code chunks")
        return results
    
    except Exception as e:
        await ctx.info(f"Search failed: {e}")
        return []

@mcp.resource("dev-assistant://commits")
async def recent_commits():
    print("recent_commits: started")
    try:
        limit = 5
        # run all git commands from the configured workspace root to ensure
        # we query the correct repository (not the process cwd)
        cwd = str(_ws_root())

        # get current branch
        branch = subprocess.check_output([
            "git", "rev-parse", "--abbrev-ref", "HEAD"
        ], text=True, cwd=cwd).strip()

        # get commit hashes
        commit_hashes = subprocess.check_output(
            ["git", "log", f"-{limit}", "--pretty=%H"], text=True, cwd=cwd
        ).splitlines()

        commits = []

        for h in commit_hashes:
            meta = subprocess.check_output(
                ["git", "show", "-s", "--format=%an|%ad|%s", h], text=True, cwd=cwd
            ).strip()

            author, date, message = meta.split("|", 2)

            files = subprocess.check_output(
                ["git", "show", "--name-only", "--pretty=format:", h], text=True, cwd=cwd
            ).splitlines()

            commits.append({
                "hash": h[:7],
                "author": author,
                "date": date,
                "message": message,
                "files": [f for f in files if f]
            })

        return json.dumps({
            "branch": branch,
            "commits": commits
        })

    except Exception as e:
        return json.dumps({
            "error": "Not a git repository or git unavailable",
            "details": str(e)
        })

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
    import sys
    
    if "--http" in sys.argv:
        import uvicorn
        
        port = 3000
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        
        uvicorn.run(
            mcp.streamable_http_app(), 
            host="127.0.0.1",
            port=port,
            log_level="info"
        )
    else:
        mcp.run(transport="stdio")

# {"jsonrpc": "2.0", "method": "tools/call", "params": {"_meta": {"progressToken": "abc123"}, "name": "read_file", "arguments": {"path": "app/main.py"}}, "id": 3}