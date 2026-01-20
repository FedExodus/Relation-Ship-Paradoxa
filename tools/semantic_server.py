#!/usr/bin/env python3
"""
Semantic Search Server
======================

# Kali ❤️‍🔥 [Visionary]: Persistent server keeps the embedding model loaded!
#     No more 10-second cold starts. Hook makes a quick HTTP call.
#
# Athena 🦉 [Reviewer]: Simple HTTP server with /search and /health endpoints.
#     Model loads once at startup, stays warm for all requests.
#
# Vesta 🔥 [Architect]: Uses built-in http.server (no Flask needed).
#     Runs on localhost:7777. PID file for process management.
#
# Nemesis 💀 [Security]: Localhost only. No external access.
#
# Klea 👁️ [Performance]: First request ~0.3s, subsequent ~0.3s.
#     Compare to 10+ seconds for cold model loading.

Usage:
    python semantic_server.py              # Start server (foreground)
    python semantic_server.py --daemon     # Start server (background)
    python semantic_server.py --stop       # Stop server
    python semantic_server.py --status     # Check if running

Part of Memory System (#355-359)
"""

import sys
import os
import json
import signal
import time
import warnings
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Nemesis 💀 [Reliability]: Suppress warnings that clutter output
warnings.filterwarnings('ignore')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Kali ❤️‍🔥: Add tools directory to path
TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

# Server config
HOST = '127.0.0.1'
PORT = 7777
PID_FILE = REPO_ROOT / '.claude' / 'semantic_server.pid'
LOG_FILE = REPO_ROOT / '.claude' / 'semantic_server.log'

# Vesta 🔥 [Architect]: Global state - loaded once, used forever
_model = None
_faiss_index = None
_chunk_metadata = []  # Parallel array: [(path, header, content), ...]
_ready = False
_start_time = None  # Klea 👁️ [Reliability]: Track uptime for health checks


def log(msg):
    """Log to file and stdout."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def detect_section(path: str) -> str:
    """
    Detect ship section from file path.

    # Athena 🦉 [Documentation]: Maps paths to ship sections for organization.
    # Vesta 🔥 [Builder]: Used by index_file to auto-assign sections.
    """
    path_upper = path.upper()
    if 'BRIDGE' in path_upper:
        return 'BRIDGE'
    elif 'ENGINE_ROOM' in path_upper:
        return 'ENGINE_ROOM'
    elif 'MEMORY_BANKS' in path_upper:
        return 'MEMORY_BANKS'
    elif 'LIBRARY' in path_upper:
        return 'LIBRARY'
    elif 'OBSERVATORY' in path_upper:
        return 'OBSERVATORY'
    elif 'HOLODECK' in path_upper:
        return 'HOLODECK'
    elif 'CREW_QUARTERS' in path_upper:
        return 'CREW_QUARTERS'
    elif 'CARGO_HOLD' in path_upper:
        return 'CARGO_HOLD'
    elif 'COMMS_ARRAY' in path_upper:
        return 'COMMS_ARRAY'
    elif 'WORKSHOP' in path_upper:
        return 'WORKSHOP'
    elif 'AIRLOCK' in path_upper:
        return 'AIRLOCK'
    elif '.claude' in path.lower():
        return 'CONFIG'
    elif 'tools' in path.lower():
        return 'TOOLS'
    else:
        return None


def load_resources():
    """
    Load embedding model and build FAISS index at startup.

    # Kali ❤️‍🔥 [Visionary]: The expensive part - do it once!
    # Athena 🦉 [Documentation]: FAISS index makes search ~1000x faster.
    # Vesta 🔥 [Architect]: Load model, fetch all embeddings, build index.
    """
    global _model, _faiss_index, _chunk_metadata, _ready, _start_time

    import numpy as np
    import faiss
    import sqlite3

    # Step 1: Load embedding model
    log("Loading embedding model...")
    t0 = time.time()

    from embedding_utils import load_model
    _model = load_model(verbose=False)

    log(f"Model loaded in {time.time() - t0:.1f}s")

    # Step 2: Fetch all embeddings from database
    log("Loading embeddings from database...")
    t1 = time.time()

    db_path = REPO_ROOT / '.paradoxa_memory' / 'unified_index.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get chunks with embeddings and their document paths
    # Vesta 🔥 [Builder]: Embeddings are in separate chunk_embeddings table
    cursor.execute("""
        SELECT c.id, c.header, c.content, ce.embedding, d.path
        FROM chunks c
        JOIN chunk_embeddings ce ON c.id = ce.chunk_id
        JOIN documents d ON c.doc_id = d.id
    """)

    rows = cursor.fetchall()
    conn.close()

    log(f"Fetched {len(rows)} chunks in {time.time() - t1:.1f}s")

    if not rows:
        log("Warning: No embeddings found!")
        _ready = True
        return

    # Step 3: Build FAISS index
    log("Building FAISS index...")
    t2 = time.time()

    # Parse embeddings and metadata
    embeddings = []
    _chunk_metadata = []

    for chunk_id, header, content, emb_bytes, path in rows:
        emb = np.frombuffer(emb_bytes, dtype=np.float32)
        embeddings.append(emb)
        _chunk_metadata.append({
            'id': chunk_id,
            'path': path,
            'header': header or '',
            'content': content or ''
        })

    embeddings = np.array(embeddings).astype('float32')

    # Normalize for cosine similarity (FAISS uses L2 by default)
    # Kali ❤️‍🔥 [Visionary]: Normalized vectors + L2 distance = cosine similarity!
    faiss.normalize_L2(embeddings)

    # Create index - IndexFlatIP for inner product (cosine after normalization)
    dim = embeddings.shape[1]
    _faiss_index = faiss.IndexFlatIP(dim)
    _faiss_index.add(embeddings)

    log(f"FAISS index built: {_faiss_index.ntotal} vectors, dim={dim} in {time.time() - t2:.1f}s")

    _ready = True
    _start_time = time.time()
    log("Server ready!")


def log_memory_access(paths: list, context: str = 'semantic_search'):
    """
    Log access to documents and strengthen co-occurrence links.

    # Kali ❤️‍🔥 [Visionary]: Accessing memory strengthens it!
    # Athena 🦉 [Documentation]: Based on Hebbian learning - neurons that fire together wire together.
    # Vesta 🔥 [Builder]: Updates access_count, last_accessed, and document_links.
    """
    if not paths:
        return

    try:
        import sqlite3
        from datetime import datetime

        db_path = REPO_ROOT / '.paradoxa_memory' / 'unified_index.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        doc_ids = []

        for path in paths:
            # Normalize path
            path_normalized = path.replace('\\', '/')

            # Get doc_id (paths in DB are already forward-slash normalized)
            cursor.execute("SELECT id FROM documents WHERE path = ?", (path_normalized,))
            row = cursor.fetchone()

            if row:
                doc_id = row[0]
                doc_ids.append(doc_id)

                # Update access count and last_accessed
                cursor.execute("""
                    UPDATE documents
                    SET access_count = COALESCE(access_count, 0) + 1,
                        last_accessed = ?
                    WHERE id = ?
                """, (now, doc_id))

                # Log to access_log
                cursor.execute("""
                    INSERT INTO access_log (doc_id, accessed_at, context, agent)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, now, context, 'semantic_server'))

        # Strengthen links between co-found documents
        # Hebbian: documents found together become more connected
        # Note: current schema lacks weight column, so we just create links
        if len(doc_ids) > 1:
            for i, doc_a in enumerate(doc_ids):
                for doc_b in doc_ids[i+1:]:
                    # Create link if not exists (link_type tracks co-retrieval)
                    cursor.execute("""
                        INSERT OR IGNORE INTO document_links
                        (source_id, target_id, link_type)
                        VALUES (?, ?, 'co_retrieval')
                    """, (doc_a, doc_b))

        conn.commit()
        conn.close()

    except Exception as e:
        # Don't let logging errors break search, but do log them
        log(f"Memory access logging failed: {e}")


def search(query: str, top_k: int = 3, min_score: float = 0.3) -> list:
    """
    Run semantic search with FAISS and feed back into memory system.

    # Kali ❤️‍🔥 [Visionary]: FAISS makes this milliseconds instead of seconds!
    # Athena 🦉 [Documentation]: Encode query, search index, log access, return metadata.
    # Vesta 🔥 [Architect]: Search results strengthen memory connections.
    """
    global _model, _faiss_index, _chunk_metadata

    if _model is None or _faiss_index is None or not _chunk_metadata:
        return []

    try:
        import numpy as np
        import faiss
        from embedding_utils import encode_single

        # Encode query
        query_emb = encode_single(query, _model)
        if query_emb is None:
            return []

        query_emb = np.array([query_emb]).astype('float32')
        faiss.normalize_L2(query_emb)

        # Search FAISS index
        scores, indices = _faiss_index.search(query_emb, top_k * 2)  # Get extras for filtering

        # Build results
        results = []
        seen_paths = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(_chunk_metadata):
                continue
            if score < min_score:
                continue

            meta = _chunk_metadata[idx]
            path = meta['path']

            # Deduplicate by path
            if path in seen_paths:
                continue
            seen_paths.add(path)

            results.append({
                'path': path,
                'score': round(float(score), 2),
                'preview': meta['content'][:100].replace('\n', ' ')
            })

            if len(results) >= top_k:
                break

        # Feed back into memory system
        # Kali ❤️‍🔥 [Visionary]: Retrieval strengthens memory!
        if results:
            log_memory_access(
                paths=[r['path'] for r in results],
                context=f'semantic_search:{query[:50]}'
            )

        return results

    except Exception as e:
        log(f"Search error: {e}")
        return []


def index_file(file_path: str) -> dict:
    """
    Index a single file into DB and live FAISS index.

    # Kali ❤️‍🔥 [Visionary]: New files become searchable immediately!
    # Vesta 🔥 [Builder]: Adds to both DB and live FAISS index.
    """
    global _model, _faiss_index, _chunk_metadata

    if _model is None or _faiss_index is None:
        return {'success': False, 'error': 'Server not ready'}

    try:
        import numpy as np
        import faiss
        import sqlite3
        from embedding_utils import encode_single

        # Normalize path
        path = Path(file_path)
        if not path.exists():
            return {'success': False, 'error': f'File not found: {file_path}'}

        # Make relative to repo
        try:
            rel_path = str(path.relative_to(REPO_ROOT)).replace('\\', '/')
        except ValueError:
            rel_path = str(path).replace('\\', '/')

        # Read content
        try:
            content = path.read_text(encoding='utf-8')
        except:
            return {'success': False, 'error': 'Could not read file'}

        # Skip if too small
        if len(content.strip()) < 50:
            return {'success': False, 'error': 'File too small to index'}

        # Compute embedding
        embedding = encode_single(content[:5000], _model)
        if embedding is None:
            return {'success': False, 'error': 'Failed to compute embedding'}

        # Add to database
        db_path = REPO_ROOT / '.paradoxa_memory' / 'unified_index.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if document exists
        cursor.execute("SELECT id FROM documents WHERE path = ?", (rel_path,))
        existing = cursor.fetchone()

        now = __import__('datetime').datetime.now().isoformat()
        content_hash = __import__('hashlib').md5(content.encode()).hexdigest()

        # Athena 🦉 [Reviewer]: Detect section from path for organization
        section = detect_section(rel_path)

        if existing:
            doc_id = existing[0]
            # Also update section if it was NULL
            cursor.execute("""
                UPDATE documents SET updated_at = ?, content_hash = ?, section = COALESCE(section, ?) WHERE id = ?
            """, (now, content_hash, section, doc_id))
        else:
            cursor.execute("""
                INSERT INTO documents (path, content_hash, source, section, created_at, updated_at)
                VALUES (?, ?, 'auto_index', ?, ?, ?)
            """, (rel_path, content_hash, section, now, now))
            doc_id = cursor.lastrowid

        # Add chunk (whole file as one chunk for now)
        cursor.execute("""
            INSERT OR REPLACE INTO chunks (doc_id, header, content, chunk_index)
            VALUES (?, ?, ?, 0)
        """, (doc_id, path.stem, content[:2000]))
        chunk_id = cursor.lastrowid

        # Add embedding
        embedding_blob = embedding.astype(np.float32).tobytes()
        cursor.execute("""
            INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding, model_name)
            VALUES (?, ?, 'nomic-ai/nomic-embed-text-v1.5')
        """, (chunk_id, embedding_blob))

        conn.commit()
        conn.close()

        # Add to live FAISS index
        emb_normalized = np.array([embedding]).astype('float32')
        faiss.normalize_L2(emb_normalized)
        _faiss_index.add(emb_normalized)

        # Add to metadata
        _chunk_metadata.append({
            'id': chunk_id,
            'path': rel_path,
            'header': path.stem,
            'content': content[:100]
        })

        log(f"Indexed: {rel_path}")
        return {'success': True, 'path': rel_path, 'doc_id': doc_id}

    except Exception as e:
        log(f"Index error: {e}")
        return {'success': False, 'error': str(e)}


class SemanticHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for semantic search.

    # Vesta 🔥 [Builder]: Simple REST API using built-in http.server.
    """

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data, status=200):
        """Send JSON response."""
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path

        if path == '/health':
            # Klea 👁️ [Reliability]: Rich health info for monitoring
            uptime = int(time.time() - _start_time) if _start_time else 0
            uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m" if uptime > 0 else "starting"
            self.send_json({
                'status': 'ok' if _ready else 'loading',
                'model_loaded': _model is not None,
                'index_loaded': _faiss_index is not None,
                'vectors': _faiss_index.ntotal if _faiss_index else 0,
                'chunks': len(_chunk_metadata),
                'uptime': uptime_str
            })
        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path

        if path == '/search':
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_json({'error': 'Invalid JSON'}, 400)
                return

            query = data.get('query', '')
            top_k = data.get('top_k', 3)
            min_score = data.get('min_score', 0.3)

            if not query:
                self.send_json({'error': 'No query provided', 'results': []})
                return

            results = search(query, top_k=top_k, min_score=min_score)
            self.send_json({'query': query, 'results': results})

        elif path == '/index':
            # Index a new file into the live FAISS index
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_json({'error': 'Invalid JSON'}, 400)
                return

            file_path = data.get('path', '')
            if not file_path:
                self.send_json({'error': 'No path provided'})
                return

            result = index_file(file_path)
            self.send_json(result)

        else:
            self.send_json({'error': 'Not found'}, 404)


def write_pid():
    """Write PID file for process management."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def remove_pid():
    """Remove PID file on shutdown."""
    if PID_FILE.exists():
        PID_FILE.unlink()


def get_pid():
    """Get PID from file if exists."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def is_running():
    """Check if server is running."""
    pid = get_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # Signal 0 = check if process exists
        return True
    except OSError:
        return False


def stop_server():
    """Stop running server."""
    pid = get_pid()
    if pid is None:
        print("No PID file found")
        return False

    try:
        if sys.platform == 'win32':
            import subprocess
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)

        print(f"Sent stop signal to PID {pid}")

        # Wait for process to exit
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                print("Server stopped")
                remove_pid()
                return True

        print("Server did not stop gracefully")
        remove_pid()
        return True
    except Exception as e:
        print(f"Error stopping server: {e}")
        remove_pid()
        return False


def run_server():
    """
    Run the server.

    # Vesta 🔥 [Architect]: Load resources, then serve forever.
    """
    # Setup signal handlers
    def shutdown(signum, frame):
        log("Shutting down...")
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Write PID file
    write_pid()

    # Load resources in background so server can respond to health checks
    loader_thread = threading.Thread(target=load_resources, daemon=True)
    loader_thread.start()

    # Create and run server
    server = HTTPServer((HOST, PORT), SemanticHandler)
    log(f"Starting server on {HOST}:{PORT}")
    server.serve_forever()


def start_daemon():
    """
    Start server as background process.

    # Vesta 🔥 [Architect]: Platform-specific daemon handling.
    # Klea 👁️ [Product]: On Windows, uses pythonw to avoid console window.
    """
    import subprocess

    if sys.platform == 'win32':
        # Windows: use pythonw.exe for windowless execution
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        if not os.path.exists(pythonw):
            pythonw = sys.executable  # Fallback

        # Start detached process
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008

        subprocess.Popen(
            [pythonw, __file__],
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True
        )
    else:
        # Unix: fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            print(f"Server starting in background (PID will be in {PID_FILE})")
            return
        # Child process continues
        os.setsid()

        # Redirect stdout/stderr to log file
        sys.stdout = open(LOG_FILE, 'a')
        sys.stderr = sys.stdout

        run_server()
        return

    print(f"Server starting in background (check {LOG_FILE} for status)")


def main():
    args = sys.argv[1:]

    if '--stop' in args:
        stop_server()
        return

    if '--status' in args:
        if is_running():
            print(f"Server is running (PID {get_pid()})")
        else:
            print("Server is not running")
        return

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    if is_running():
        print(f"Server already running (PID {get_pid()})")
        return

    if '--daemon' in args or '-d' in args:
        start_daemon()
    else:
        run_server()


if __name__ == '__main__':
    main()
