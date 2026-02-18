import asyncio
import re
from pathlib import Path
from dotenv import load_dotenv
import os 

load_dotenv()
WORKSPACE_ROOT = os.getenv("MCP_WORKSPACE")
WORKSPACE_ROOT = Path(WORKSPACE_ROOT).resolve()

async def is_third_party(path: str) -> bool:
    return any(part in path for part in [
        "site-packages",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build"
    ])

async def collect_definitions(search_fn, base_path):
    defs = {}

    for kw in ["def ", "class "]:
        results = await search_fn(query=kw, path_override=base_path)

        for r in results:
            if await is_third_party(r["file"]):
                continue
            line = r["snippet"]

            try:
                if kw == "def ":
                    parts = line.split("def ")
                    if len(parts) < 2:
                        continue
                    name = parts[1].split("(")[0].strip()
                else:
                    parts = line.split("class ")
                    if len(parts) < 2: 
                        continue
                    name = parts[1].split("(")[0].strip()

                if name: 
                    defs[name] = {
                        "file": r["file"],
                        "line": r["line"]
                    }
            except (IndexError, AttributeError):
                continue

    return defs

async def collect_usages(search_fn, definitions, base_path):
    usages = {name: [] for name in definitions}

    for name in definitions:
        results = await search_fn(query=f"{name}(", path_override = base_path)

        for r in results:
            if r["line"] != definitions[name]["line"]:
                usages[name].append(r["file"])

    unused = []

    for name, files in usages.items():
        if not files:
            unused.append({
                "symbol": name,
                "defined_in": definitions[name]
            })

    return usages, unused

EXTERNAL_PATTERNS = ["open(", "requests.", "subprocess.", "os.system("]

async def collect_external_calls(search_fn, base_path):
    calls = []

    for pattern in EXTERNAL_PATTERNS:
        results = await search_fn(query=pattern, path_override=base_path)

        for r in results:
            calls.append({
                "file": r["file"],
                "line": r["line"],
                "snippet": r["snippet"]
            })

    return calls

async def collect_try_blocks(search_fn, base_path):
    blocks = []

    results = await search_fn("try:", base_path)

    for r in results:
        blocks.append({
            "file": r["file"],
            "line": r["line"]
        })

    return blocks

EXPENSIVE_METHOD_HINTS = [
    "fit", "train", "compile", "optimize",
    "predict", "infer", "evaluate",
    "load", "save",
    "from_pretrained", "deserialize",
    "build", "initialize",
]

RESOURCE_HINTS = [
    "open(", "read(", "write(",
    "http", "requests", "fetch",
    "cuda", "gpu", "device",
    "thread", "process", "pool",
]

CALL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\(")

LOOP_HINTS = ["for ", "while "]
ASYNC_HINTS = ["async def", "await "]
ALLOWED_EXTENSIONS = {
    ".py", ".pyw", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", 
    ".java", ".kt", ".kts", ".scala", ".groovy", ".c", ".h", ".cpp",
    ".cc", ".cxx", ".hpp", ".hxx", ".cs", ".fs", ".fsx", ".vb", ".go", ".rs",
    ".rb", ".php", ".swift", ".m", ".mm", ".r", ".R", ".dart", ".lua", 
    ".ex", ".exs", ".erl", ".hs"
}

BINARY_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".zip", ".tar", ".gz", ".exe", ".dll",
    ".docx", ".pptx", ".xlsx"
}
EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".cache",
    "dist", "build", "target", "out", "coverage", ".idea", ".vscode",
    "site-packages", "Lib", "Scripts", "bin", "Include"
}

async def iter_source_lines(base_path):
    # root = Path(base_path).resolve()
    search_path = (WORKSPACE_ROOT / base_path).resolve()
    for fp in search_path.rglob("*"):
        normalized = str(fp).replace("\\", "/")
        if any(seg in normalized for seg in EXCLUDED_DIRS):
            continue

        if not fp.is_file():
            continue

        if not fp.is_file(): # skip non files
            continue

        if fp.suffix.lower() in BINARY_EXTENSIONS: # skip files which cannot be read normally
            continue

        if fp.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        try:
            with fp.open("r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, start=1):
                    yield {
                        "file": str(fp.relative_to(WORKSPACE_ROOT)),
                        "line": lineno,
                        "text": line.rstrip()
                    }
        except Exception:
            continue


async def collect_expensive_ops(base_path):
    ops = []

    async for row in iter_source_lines(base_path):
        line = row["text"]

        # match any function call (object.method OR function())
        m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
        if not m:
            continue

        method = m.group(1)

        if method not in EXPENSIVE_METHOD_HINTS:
            continue

        ops.append({
            "file": row["file"],
            "line": row["line"],
            "method": method,
            "signals": {
                "inside_loop": any(h in line for h in LOOP_HINTS),
                "async_context": any(h in line for h in ASYNC_HINTS),
            }
        })

    return ops

async def collect_signals(search_fn, base_path):
    defs = await collect_definitions(search_fn, base_path)
    uses, unused = await collect_usages(search_fn, defs, base_path)

    return {
        "definitions": defs,
        "usages": uses,
        "unused": unused,
        "external_calls": await collect_external_calls(search_fn, base_path),
        "try_blocks": await collect_try_blocks(search_fn, base_path),
        "expensive_ops": await collect_expensive_ops(base_path)
    }