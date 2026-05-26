# # import asyncio
# # import re
# # from pathlib import Path
# # from dotenv import load_dotenv
# # import os 

# # load_dotenv()
# # WORKSPACE_ROOT = os.getenv("MCP_WORKSPACE")
# # WORKSPACE_ROOT = Path(WORKSPACE_ROOT).resolve()

# # async def is_third_party(path: str) -> bool:
# #     return any(part in path for part in [
# #         "site-packages",
# #         ".venv",
# #         "venv",
# #         "node_modules",
# #         "dist",
# #         "build"
# #     ])

# # async def collect_definitions(search_fn, base_path):
# #     defs = {}

# #     for kw in ["def ", "class "]:
# #         results = await search_fn(query=kw, path_override=base_path)

# #         for r in results:
# #             if await is_third_party(r["file"]):
# #                 continue
# #             line = r["snippet"]

# #             try:
# #                 if kw == "def ":
# #                     parts = line.split("def ")
# #                     if len(parts) < 2:
# #                         continue
# #                     name = parts[1].split("(")[0].strip()
# #                 else:
# #                     parts = line.split("class ")
# #                     if len(parts) < 2: 
# #                         continue
# #                     name = parts[1].split("(")[0].strip()

# #                 if name: 
# #                     defs[name] = {
# #                         "file": r["file"],
# #                         "line": r["line"]
# #                     }
# #             except (IndexError, AttributeError):
# #                 continue

# #     return defs

# # async def collect_usages(search_fn, definitions, base_path):
# #     usages = {name: [] for name in definitions}

# #     for name in definitions:
# #         results = await search_fn(query=f"{name}(", path_override = base_path)

# #         for r in results:
# #             if r["line"] != definitions[name]["line"]:
# #                 usages[name].append(r["file"])

# #     unused = []

# #     for name, files in usages.items():
# #         if not files:
# #             unused.append({
# #                 "symbol": name,
# #                 "defined_in": definitions[name]
# #             })

# #     return usages, unused

# # EXTERNAL_PATTERNS = ["open(", "requests.", "subprocess.", "os.system("]

# # async def collect_external_calls(search_fn, base_path):
# #     calls = []

# #     for pattern in EXTERNAL_PATTERNS:
# #         results = await search_fn(query=pattern, path_override=base_path)

# #         for r in results:
# #             calls.append({
# #                 "file": r["file"],
# #                 "line": r["line"],
# #                 "snippet": r["snippet"]
# #             })

# #     return calls

# # async def collect_try_blocks(search_fn, base_path):
# #     blocks = []

# #     results = await search_fn(query="try:", path_override=base_path)

# #     for r in results:
# #         blocks.append({
# #             "file": r["file"],
# #             "line": r["line"]
# #         })

# #     return blocks

# # EXPENSIVE_METHOD_HINTS = [
# #     "fit", "train", "compile", "optimize",
# #     "predict", "infer", "evaluate",
# #     "load", "save",
# #     "from_pretrained", "deserialize",
# #     "build", "initialize",
# # ]

# # RESOURCE_HINTS = [
# #     "open(", "read(", "write(",
# #     "http", "requests", "fetch",
# #     "cuda", "gpu", "device",
# #     "thread", "process", "pool",
# # ]

# # CALL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\(")

# # LOOP_HINTS = ["for ", "while "]
# # ASYNC_HINTS = ["async def", "await "]
# # ALLOWED_EXTENSIONS = {
# #     ".py", ".pyw", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", 
# #     ".java", ".kt", ".kts", ".scala", ".groovy", ".c", ".h", ".cpp",
# #     ".cc", ".cxx", ".hpp", ".hxx", ".cs", ".fs", ".fsx", ".vb", ".go", ".rs",
# #     ".rb", ".php", ".swift", ".m", ".mm", ".r", ".R", ".dart", ".lua", 
# #     ".ex", ".exs", ".erl", ".hs"
# # }

# # BINARY_EXTENSIONS = {
# #     ".pdf", ".png", ".jpg", ".jpeg", ".gif",
# #     ".zip", ".tar", ".gz", ".exe", ".dll",
# #     ".docx", ".pptx", ".xlsx"
# # }
# # EXCLUDED_DIRS = {
# #     "node_modules", ".venv", "venv", "__pycache__", ".git", ".cache",
# #     "dist", "build", "target", "out", "coverage", ".idea", ".vscode",
# #     "site-packages", "Lib", "Scripts", "bin", "Include", ".next",
# #     ".nuxt", ".output", "build",  ".webpack", ".turbo", 
# # }

# # async def iter_source_lines(base_path):
# #     # root = Path(base_path).resolve()
# #     search_path = (WORKSPACE_ROOT / base_path).resolve()
# #     for fp in search_path.rglob("*"):

# #         normalized = str(fp).replace("\\", "/")
# #         if any(seg in normalized for seg in EXCLUDED_DIRS):
# #             continue

# #         parts = fp.parts
# #         if any(part in EXCLUDED_DIRS for part in parts):
# #             continue

# #         if ".next" in str(fp):
# #             continue

# #         if not fp.is_file():
# #             continue

# #         if not fp.is_file(): # skip non files
# #             continue

# #         if fp.suffix.lower() in BINARY_EXTENSIONS: # skip files which cannot be read normally
# #             continue

# #         if fp.suffix.lower() not in ALLOWED_EXTENSIONS:
# #             continue

# #         try:
# #             with fp.open("r", encoding="utf-8", errors="ignore") as f:
# #                 for lineno, line in enumerate(f, start=1):
# #                     yield {
# #                         "file": str(fp.relative_to(WORKSPACE_ROOT)),
# #                         "line": lineno,
# #                         "text": line.rstrip()
# #                     }
# #         except Exception:
# #             continue


# # async def collect_expensive_ops(base_path):
# #     ops = []

# #     async for row in iter_source_lines(base_path):
# #         line = row["text"]

# #         # match any function call (object.method OR function())
# #         m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
# #         if not m:
# #             continue

# #         method = m.group(1)

# #         if method not in EXPENSIVE_METHOD_HINTS:
# #             continue

# #         ops.append({
# #             "file": row["file"],
# #             "line": row["line"],
# #             "method": method,
# #             "signals": {
# #                 "inside_loop": any(h in line for h in LOOP_HINTS),
# #                 "async_context": any(h in line for h in ASYNC_HINTS),
# #             }
# #         })

# #     return ops

# # async def collect_signals(search_fn, base_path):
# #     defs = await collect_definitions(search_fn, base_path)
# #     uses, unused = await collect_usages(search_fn, defs, base_path)

# #     return {
# #         "definitions": defs,
# #         "usages": uses,
# #         "unused": unused,
# #         "external_calls": await collect_external_calls(search_fn, base_path),
# #         "try_blocks": await collect_try_blocks(search_fn, base_path),
# #         "expensive_ops": await collect_expensive_ops(base_path)
# #     }

# @mcp.tool(
#     name="search_relevant_code",
#     description="Find code chunks semantically relevant to a natural language query. Use this for lint, optimize, and fix commands instead of scanning entire codebase."
# )
# async def search_relevant_code(
#     query: str = Field(description="Natural language description of code to find"),
#     max_results: int = Field(default=15, description="Maximum results to return"),
#     path_filter: str = Field(default=None, description="Optional path prefix to filter results (e.g., 'src/')"),
#     ctx: Context = None
# ):
#     await ctx.info(f"Searching for: {query}")
    
#     try:
#         embedder = get_embedder()
#         results = embedder.search_relevant_code(query, n_results=max_results, path_filter=path_filter)
        
#         await ctx.info(f"Found {len(results)} relevant code chunks")
#         return results
    
#     except Exception as e:
#         await ctx.info(f"Search failed: {e}")
#         return []
    

# COMMON_ENTRY_NAMES = {
#     "main", "index", "app", "server", "start",
#     "__main__", "run", "cli", "manage",
#     "entry", "bootstrap",
#     "wsgi", "asgi",
# }

# ENTRY_PATTERNS = {
#     "python_main": "if __name__ == \"__main__\"",
#     "python_main_alt": "if __name__ == '__main__'",
#     "c_cpp": "int main(",
#     "java": "public static void main(",
#     "go": "func main()",
#     "rust": "fn main()",
#     "csharp": "static void Main(",
#     "javascript_module": "require.main === module",
#     "express": "app.listen(",
#     "fastapi": "uvicorn.run(",
#     "flask": "app.run(",
#     "django": "execute_from_command_line(",
#     "react": "ReactDOM.render(",
#     "nextjs": "export default function",
# }

# @mcp.tool(
#     name="find_entry_points",
#     description="Identify likely execution entry points in the project"
# )
# async def find_entry_points(ctx: Context) -> List[Dict]:
#     await ctx.info("Scanning project for entry points")
#     entry_points = []
#     seen_files = set()
#     fs = 0

#     package_json = WORKSPACE_ROOT / "package.json"
#     if package_json.exists():
#         try:
#             with open(package_json, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
                
#                 if "main" in data:
#                     main_file = data["main"]
#                     entry_points.append({
#                         "file": main_file,
#                         "reason": f"package.json 'main' field points to this file",
#                         "type": "package_main"
#                     })
#                     seen_files.add(main_file)
                
#                 if "scripts" in data:
#                     for script_name, script_cmd in data["scripts"].items():
#                         if script_name in ["start", "dev", "serve", "main"]:
#                             entry_points.append({
#                                 "file": "package.json",
#                                 "reason": f"npm script '{script_name}': {script_cmd}",
#                                 "type": "npm_script"
#                             })
#         except Exception as e:
#             await ctx.info(f"Warning: Could not parse package.json: {e}")

#     for path in WORKSPACE_ROOT.rglob("*"):
#         if fs >= MAX_FILES_SCANNED:
#             break

#         if any(part in EXCLUDED_DIRS for part in path.parts):
#             continue
        
#         normalized = str(path).replace("\\", "/")
#         if any(seg in normalized for seg in EXCLUDED_DIRS):
#             continue

#         if not path.is_file():
#             continue

#         if path.suffix.lower() in BINARY_EXTENSIONS:
#             continue

#         if path.suffix.lower() not in ALLOWED_EXTENSIONS:
#             continue

#         fs += 1
#         rel_path = str(path.relative_to(WORKSPACE_ROOT))

#         if rel_path in seen_files:
#             continue

#         stem = path.stem.lower()

#         if stem in COMMON_ENTRY_NAMES:
#             entry_points.append({
#                 "file": rel_path,
#                 "reason": f"Common entry filename: '{stem}{path.suffix}'",
#                 "type": "common_name"
#             })
#             seen_files.add(rel_path)
#             continue

#         try:
#             with path.open("r", encoding="utf-8", errors="ignore") as f:
#                 head_lines = [f.readline() for _ in range(50)]
#                 head = "".join(head_lines)

#             for lang, pattern in ENTRY_PATTERNS.items():
#                 if pattern in head:
#                     entry_points.append({
#                         "file": rel_path,
#                         "reason": f"Contains {lang} entry point pattern: '{pattern}'",
#                         "type": "code_pattern"
#                     })
#                     seen_files.add(rel_path)
#                     break  # One entry point per file

#         except Exception:
#             continue

#         # Stop if we found enough entry points
#         if len(entry_points) >= 10:
#             break
    
#     await ctx.info(f"Detected {len(entry_points)} possible entry points")
#     return entry_points



# @mcp.tool(
#     name="search_code",
#     description="Search for a text pattern across all the files in the workspace"
# )
# async def search_code(
#     query: str = Field(description="Text to search for"),
#     path: str = Field(
#         default=".",
#         description="Relative directory to search in (default: workspace root)"
#     ),
#     max_results: int = 50,
#     raw: bool = False,
#     ctx: Context = None
# ) -> List[Dict]:
    
#     query_lower = query.lower()
    
#     # await ctx.info(f"Searching project for '{query}'")
#     if not query or len(query.strip()) == 0:
#         return []
    
#     if not re.search(r'[A-Za-z0-9_]', query):
#         return []
    
    
#     # normalize query to get meaningful tokens (to support multiline queries)
#     re.sub(r'\(.*\)', '', query) # in functions remove '()' funcname() -> func
#     tokens = set(
#         t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query)
#         if len(t) >= 1
#     )

#     tokens_lower = {t.lower() for t in tokens}

#     if not tokens_lower:
#         raise ValueError(f"Query does not contain searchable tokens: {query}")

    
#     fs = 0
#     search_path = (WORKSPACE_ROOT / path).resolve()
#     if not str(search_path).startswith(str(WORKSPACE_ROOT)):
#         raise ValueError("Access Denied: Path outside workspace")
    
#     if not search_path.exists():
#         raise ValueError(f"Directory not found: {path}")
    
#     res = []
#     for fp in search_path.rglob("*"):
#         if fs >= MAX_FILES_SCANNED:
#             break

#         normalized = str(fp).replace("\\", "/")
#         if any(seg in normalized for seg in EXCLUDED_DIRS):
#             continue

#         if len(res) >= max_results:
#             break

#         if not fp.is_file(): # skip non files
#             continue

#         if fp.suffix.lower() in BINARY_EXTENSIONS: # skip files which cannot be read normally
#             continue

#         if fp.suffix.lower() not in ALLOWED_EXTENSIONS:
#             continue

#         try:
#             if fp.stat().st_size > MAX_FILE_SIZE:
#                 continue
#         except Exception:
#             continue
        
#         fs += 1
#         # if (fs % 100 == 0):
#             # await ctx.info(f"Scanned {fs} files…")
#         try:
#             with fp.open("r", encoding="utf-8", errors="ignore") as f:
#                 for n, line in enumerate(f, start=1):
#                     line_lower = line.lower()
#                     if line.strip().startswith("#"): # to not scan commented lines
#                         continue
#                     if any(token in line_lower for token in tokens_lower):
#                         res.append({
#                             "file": str(fp.relative_to(WORKSPACE_ROOT)),
#                             "line": n,
#                             "snippet": line.strip(),
#                             "matched_tokens": [t for t in tokens_lower if t in line_lower]
#                         })
#                         if len(res) >= max_results:
#                             break
#         except Exception:
#             continue
    
#     # await ctx.info(f"Search complete. Found {len(res)} matches.")
#     return res
