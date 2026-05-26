from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from pathlib import Path
import json
import os
import subprocess
import atexit
import time
from mcp_client.client import MCPHTTPClient
from embedder import get_embedder
from config import load_config, save_config

CURRENT_WORKSPACE = None
MCP_SERVER_PROCESS = None
MCP_SERVER_URL = "http://127.0.0.1:3000/mcp"
_shared_client = None

async def get_mcp_client():
    global _shared_client
    
    if _shared_client is None:
        _shared_client = MCPHTTPClient()
        await _shared_client.connect()
    
    return _shared_client

def start_mcp_server():
    global MCP_SERVER_PROCESS
    
    if MCP_SERVER_PROCESS is None:
        print("Starting MCP server...")
        MCP_SERVER_PROCESS = subprocess.Popen(
            ["uv", "run", "mcp_server/server.py", "--http", "--port", "3000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)
        print("MCP server started")

def stop_mcp_server():
    global MCP_SERVER_PROCESS
    if MCP_SERVER_PROCESS:
        print("Stopping MCP server...")
        MCP_SERVER_PROCESS.terminate()
        MCP_SERVER_PROCESS.wait()
        print("MCP server stopped")

atexit.register(stop_mcp_server)

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_mcp_server()
    yield
    stop_mcp_server()

app = FastAPI(title="Dev Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WorkspaceRequest(BaseModel):
    workspace: str

class CommandRequest(BaseModel):
    command: str
    args: dict = {}

class GitConfigRequest(BaseModel):
    has_git: bool
    is_local: bool = False

def get_current_workspace():
    if CURRENT_WORKSPACE is None:
        raise HTTPException(
            status_code=400, 
            detail="Workspace not set. Please set workspace first using /workspace/set"
        )
    return CURRENT_WORKSPACE

def get_git_context_for_workspace(workspace: str):
    config = load_config()
    return config.get(workspace, {}).get("git_context")

def set_git_context_for_workspace(workspace: str, has_git: bool, is_local: bool):
    config = load_config()
    
    if workspace not in config:
        config[workspace] = {}
    
    if has_git:
        config[workspace]["git_context"] = "LOCAL_GIT" if is_local else "REMOTE_ONLY"
    else:
        config[workspace]["git_context"] = None
    
    save_config(config)

@app.post("/workspace/set")
async def set_workspace(request: WorkspaceRequest):
    global CURRENT_WORKSPACE

    workspace_path = Path(request.workspace).resolve()

    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path does not exist")

    if not workspace_path.is_dir():
        raise HTTPException(status_code=400, detail="Workspace must be a directory")

    CURRENT_WORKSPACE = str(workspace_path)

    # Propagate the new workspace to the MCP server process
    try:
        client = await get_mcp_client()
        await client.call_tool("set_workspace", {"path": CURRENT_WORKSPACE})
    except Exception as e:
        print(f"Warning: could not update MCP server workspace: {e}")

    git_ctx = get_git_context_for_workspace(CURRENT_WORKSPACE)

    return {
        "status": "success",
        "workspace": CURRENT_WORKSPACE,
        "git_configured": git_ctx is not None,
        "git_context": git_ctx
    }

@app.get("/workspace/current")
async def get_workspace():
    if CURRENT_WORKSPACE is None:
        return {
            "workspace": None,
            "set": False
        }
    
    git_ctx = get_git_context_for_workspace(CURRENT_WORKSPACE)
    
    return {
        "workspace": CURRENT_WORKSPACE,
        "set": True,
        "git_configured": git_ctx is not None,
        "git_context": git_ctx
    }


@app.post("/config/git")
async def configure_git(request: GitConfigRequest):
    set_git_context_for_workspace(CURRENT_WORKSPACE, request.has_git, request.is_local)
    return {"status": "success", "message": "Git configuration saved", "workspace": CURRENT_WORKSPACE}


@app.post("/index/build")
async def build_index(workspace: str = Depends(get_current_workspace)):
    try:
        original_cwd = Path.cwd()
        workspace_path = Path(workspace)
        os.chdir(workspace_path)

        embedder = get_embedder(workspace)
        embedder.index_workspace()
        stats = embedder.get_stats()
        return {
            "status": "success",
            "message": "Index built successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.chdir(original_cwd)

@app.get("/index/stats")
async def get_index_stats():
    try:
        embedder = get_embedder(CURRENT_WORKSPACE)
        stats = embedder.get_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/index/clear")
async def clear_index():
    try:
        embedder = get_embedder(CURRENT_WORKSPACE)
        embedder.clear_index()
        
        return {
            "status": "success",
            "message": "Index cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute")
async def execute_command(request: CommandRequest):
    if request.command == "explain-flow" or request.command == "explain-file":
        file_path = request.args.get("path", "")
        
        if not file_path or file_path == ".":
            raise HTTPException(
                status_code=400,
                detail="explain-flow requires a specific file path, not a directory"
            )
        
        workspace_path = Path(CURRENT_WORKSPACE)
        target_file = workspace_path / file_path
        
        if not target_file.exists() or target_file.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"File not found or is a directory: {file_path}"
            )

    try:
        original_cwd = Path.cwd()
        workspace_path = Path(CURRENT_WORKSPACE)
        
        os.chdir(workspace_path)

        client = await get_mcp_client()

        try:
            # signals = None
            git_info = None
            
            git_ctx = get_git_context_for_workspace(CURRENT_WORKSPACE)
            
            if git_ctx is None:
                return {
                    "status": "git_config_required",
                    "message": "Please configure git settings first",
                    "workspace": CURRENT_WORKSPACE
                }
            
            if git_ctx == "LOCAL_GIT":
                try:
                    res = await client.read_resource("dev-assistant://commits")
                    git_info = json.loads(res)
                except Exception as e:
                    print(f"Warning: Could not fetch git commits: {e}")
                    git_info = None
            
            # if request.command in ["lint", "optimize", "fix"]:
            #     signals = get_cached_signals()
                
            #     if not signals:
            #         resource_content = await client.read_resource("dev-assistant://signals")
            #         signals = json.loads(resource_content)
            #         save_cached_signals(signals)
            
            from cli import build_prompt
            
            class Args:
                def __init__(self, command, **kwargs):
                    self.command = command
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            
            args = Args(request.command, **request.args)
            prompt = build_prompt(args)
            
            response = await client.ask(prompt, request.command, git_info)
            
            return {
                "status": "success",
                "command": request.command,
                "workspace": CURRENT_WORKSPACE,
                "response": response,
                # "used_cache": signals is not None and get_cached_signals() is not None,
                "has_git_info": git_info is not None
            }
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"ERROR in execute endpoint:")
        print(error_details["traceback"])
        raise HTTPException(status_code=500, detail=error_details)

@app.get("/index/visualize")
async def visualize_index(
    max_points: int = 500,
    workspace: str = Depends(get_current_workspace)
):
    try:
        embedder = get_embedder(workspace)

        print(f"Generating visualization for {max_points} points...")
        viz_data = embedder.visualize_vector_space(max_points=max_points)
        
        return {
            "status": "success",
            "workspace": workspace,
            "visualization": viz_data
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/health")
async def health():
    return {"status": "ok"}