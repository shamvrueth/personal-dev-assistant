import os
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import hashlib
import numpy as np
from sklearn.manifold import TSNE

load_dotenv()
WORKSPACE_ROOT = Path(os.getenv("MCP_WORKSPACE")).resolve()

EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".cache",
    "dist", "build", "target", "out", "coverage", ".idea", ".vscode",
    "site-packages", "Lib", "Scripts", "bin", "Include", ".next",
    ".nuxt", ".output", ".webpack", ".turbo", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".tox", "htmlcov"
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".scala", ".m", ".mm", ".dart", ".lua"
}

class CodeEmbedder:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model loaded successfully")
    
        db_path = Path.home() / ".dev-assistant" / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(db_path))
        # create collection name based on workspace hash
        workspace_hash = hashlib.md5(str(workspace_root).encode()).hexdigest()[:8]
        name = f"code_{workspace_hash}"

        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Using collection: {name}")
    
    def chunk_file(self, filepath: Path, size: int = 50):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            chunks = []
            step = size // 2  # 50% overlap
            for i in range(0, len(lines), step):
                chunk_lines = lines[i: i + size]
                chunk_text = ''.join(chunk_lines).strip()
                if not chunk_text:
                    continue

                chunks.append({
                    "text": chunk_text,
                    "file": str(filepath.relative_to(self.workspace_root)),
                    "start_line": i + 1,
                    "end_line": min(i+size, len(lines))
                })
            
            return chunks
        
        except Exception as e:
            print(f"Error chunking {filepath}: {e}")
            return []
    
    def index_workspace(self): # index all code files in workspace
        print(f"Indexing workspace: {self.workspace_root}")

        ids = []
        documents = []
        metadatas = []

        fc = 0
        cc = 0

        for filepath in self.workspace_root.rglob("*"):
            if any(excluded in filepath.parts for excluded in EXCLUDED_DIRS):
                continue
            
            if not filepath.is_file():
                continue
            
            if filepath.suffix not in ALLOWED_EXTENSIONS:
                continue
            
            try:
                if filepath.stat().st_size > 1_000_000:
                    print(f"Skipping large file: {filepath.name}")
                    continue
            except:
                continue

            chunks = self.chunk_file(filepath)
            if not chunks:
                continue

            fc += 1
            for chunk in chunks:
                chunk_id = f"{chunk['file']}:{chunk['start_line']}-{chunk['end_line']}" # unique chunk id
                ids.append(chunk_id)

                documents.append(chunk["text"])
                metadatas.append({
                    "file": chunk["file"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "extension": filepath.suffix
                })

                cc += 1
                if cc % 100 == 0:
                    print(f"Indexed {cc} chunks from {fc} files...")
            
        if not documents:
            print("No code files found to index")
            return
            
        print(f"Generating embeddings for {len(documents)} chunks...")

        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]

            self.collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta
            )
            
        print(f"Indexing complete")
    
    def search_relevant_code(self, query: str, n_results:int = 10):
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )

            if not results["documents"][0]:
                return []
            
            relevant_chunks = []
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i]
                similarity = max(0, 1-distance)
                relevant_chunks.append({
                    "text": results["documents"][0][i],
                    "file": results["metadatas"][0][i]["file"],
                    "start_line": results["metadatas"][0][i]["start_line"],
                    "end_line": results["metadatas"][0][i]["end_line"],
                    "similarity": round(similarity, 3)
                })
            return relevant_chunks
        
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def get_stats(self):
        try:
            count = self.collection.count()
            return {
                "indexed_chunks": count,
                "workspace": str(self.workspace_root)
            }
        except:
            return {"indexed_chunks": 0}
        
    def clear_index(self):
        try:
            name = self.collection.name
            self.client.delete_collection(name)
            
            # recreate empty collection
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Index cleared: {name}")

        except Exception as e:
            print(f"Error clearing index: {e}")

    def visualize_vector_space(self, max_points: int = 500):
        try:
            # get all embeddings from ChromaDB
            results = self.collection.get(
                include=['embeddings', 'metadatas', 'documents'],
                limit=max_points  # limit for performance
            )
            
            if len(results['embeddings']) == 0:
                return {
                    "error": "No embeddings found. Build index first.",
                    "points": []
                }
            
            embeddings = np.array(results['embeddings'])
            metadatas = results['metadatas']
            documents = results['documents']
            
            print(f"Visualizing {len(embeddings)} embeddings...")
            
            tsne = TSNE(
                n_components=2,
                random_state=42,
                perplexity=min(30, len(embeddings) - 1),
                # n_iter=1000,
                verbose=0
            )
            
            coords_2d = tsne.fit_transform(embeddings)
            
            # normalize coordinates to 0-1 range for easier plotting
            normalized = (coords_2d - coords_2d.min(axis=0)) / (coords_2d.max(axis=0) - coords_2d.min(axis=0))
            
            unique_files = list(set(m['file'] for m in metadatas))
            file_colors = {}
            
            # generate distinct colors using HSV color space
            import colorsys
            for i, file in enumerate(unique_files):
                hue = i / len(unique_files)
                rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
                file_colors[file] = {
                    "rgb": [int(c * 255) for c in rgb],
                    "hex": "#{:02x}{:02x}{:02x}".format(
                        int(rgb[0] * 255),
                        int(rgb[1] * 255),
                        int(rgb[2] * 255)
                    )
                }
            
            # build visualization data
            points = []
            for i, (x, y) in enumerate(normalized):
                file = metadatas[i]['file']
                
                points.append({
                    "x": float(x),
                    "y": float(y),
                    "file": file,
                    "color": file_colors[file]["hex"],
                    "start_line": metadatas[i]['start_line'],
                    "end_line": metadatas[i]['end_line'],
                    "preview": documents[i][:100] + "..." if len(documents[i]) > 100 else documents[i]
                })
            
            return {
                "points": points,
                "file_colors": file_colors,
                "total_points": len(points),
                "total_files": len(unique_files),
                "dimensions_original": embeddings.shape[1],
                "dimensions_reduced": 2
            }
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "points": []
            }

_embedders: dict = {}

def get_embedder(workspace=None):
    global _embedders
    target = Path(workspace).resolve() if workspace else WORKSPACE_ROOT
    if target not in _embedders:
        _embedders[target] = CodeEmbedder(target)
    return _embedders[target]
