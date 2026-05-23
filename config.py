#cinfig.py
import json
import hashlib
from pathlib import Path

# CACHE_DIR = Path.home() / ".dev-assistant" / "cache"
GIT_CONFIG_FILE = Path.home() / ".dev-assistant" / "git_config.json"

# def get_workspace_id():
#     import os
#     workspace = os.getenv("MCP_WORKSPACE")
#     if not workspace:
#         return None
#     return hashlib.md5(workspace.encode()).hexdigest()

# def get_cached_signals():
#     workspace_id = get_workspace_id()
#     if not workspace_id:
#         return None
    
#     cache_file = CACHE_DIR / f"{workspace_id}_signals.json"
    
#     if not cache_file.exists():
#         return None
    
#     try:
#         with open(cache_file, 'r') as f:
#             return json.load(f)
#     except Exception as e:
#         print(f"Error loading cache: {e}")
#         return None

# def save_cached_signals(signals):
#     workspace_id = get_workspace_id()
#     if not workspace_id:
#         return False
    
#     CACHE_DIR.mkdir(parents=True, exist_ok=True)
#     cache_file = CACHE_DIR / f"{workspace_id}_signals.json"
    
#     try:
#         with open(cache_file, 'w') as f:
#             json.dump(signals, f, indent=2)
#         return True
#     except Exception as e:
#         print(f"Error saving cache: {e}")
#         return False

# def clear_signals_cache():
#     workspace_id = get_workspace_id()
#     if not workspace_id:
#         return False
    
#     cache_file = CACHE_DIR / f"{workspace_id}_signals.json"
    
#     if cache_file.exists():
#         try:
#             cache_file.unlink() 
#             print(f"Cleared cache: {cache_file}")
#             return True
#         except Exception as e:
#             print(f"Error clearing cache: {e}")
#             return False
#     return False

# def clear_all_cache():
#     if not CACHE_DIR.exists():
#         return False
    
#     try:
#         count = 0
#         for cache_file in CACHE_DIR.glob("*_signals.json"):
#             cache_file.unlink()
#             count += 1
        
#         print(f"Cleared {count} cache files")
#         return True
#     except Exception as e:
#         print(f"Error clearing all cache: {e}")
#         return False

def load_config():
    if not GIT_CONFIG_FILE.exists():
        return {}
    
    try:
        with open(GIT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def save_config(config):
    GIT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(GIT_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
    
def get_git_context():
    config = load_config()
    
    workspace = str(Path.cwd())
    
    if workspace in config:
        return config[workspace].get("git_context")
    
    print("\n=== Git Repository Configuration ===")
    ans = input("Is this project a Git repository? (y/n): ").strip().lower()
    
    if ans != "y":
        git_ctx = None
    else:
        local = input("Is the repository available locally? (y/n): ").strip().lower()
        git_ctx = "LOCAL_GIT" if local == "y" else "REMOTE_ONLY"
    
    if workspace not in config:
        config[workspace] = {}
    config[workspace]["git_context"] = git_ctx
    save_config(config)
    
    return git_ctx