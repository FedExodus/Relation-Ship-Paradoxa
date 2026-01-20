#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Index - Single Source of Truth for Paradoxa Memory
============================================================

# Kali ❤️‍🔥 [Visionary]: One index to rule them all. No more 5 separate pickle files
#     each storing embeddings for different purposes. Everything lives here.
#
# Athena 🦉 [Reviewer]: This is Phase 2 of MIRA-inspired unification. We're
#     replacing scattered .pkl indices with a single SQLite database that
#     supports source tagging, access tracking, and future decay scoring.
#
# Vesta 🔥 [Architect]: SQLite is perfect for this - embedded, no server,
#     handles concurrent reads, and supports rich queries.
#
# Nemesis 💀 [Security]: Local storage only. No data transmission.
#     Embeddings stay on your machine. Pickle used ONLY for legacy migration.
#
# Klea 👁️ [Product]: ...one brain, many purposes.

MIRA-OSS Integration:
    Phase 2 of the MIRA-inspired tool unification.
    Builds on Phase 1 shared infrastructure.
    Enables Phase 3 decay scoring via access tracking.

Attribution:
    MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)

Usage:
    from unified_index import UnifiedIndex

    idx = UnifiedIndex()
    idx.add_document("path/to/file.md", content, source="ship")
    results = idx.search("query", source_filter="ship", top_k=10)

"""

import sys
import re
import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

# Kali ❤️‍🔥 [Visionary]: Handle imports whether run as module or script
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

# Kali ❤️‍🔥 [Visionary]: Phase 1 shared infrastructure
# Attribution: MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS)
from shared_config import (
    Colors,
    PARADOXA_MEMORY_DIR,
    LEGACY_RECOGNITION_INDEX,
    LEGACY_SEMANTIC_INDEX,
    LEGACY_RELATIONSHIP_INDEX,
    LEGACY_SELF_RECOGNITION_INDEX,
    check_embedding_dependencies,
    print_section,
    print_ok,
    print_warning,
    print_error,
    DEFAULT_EMBEDDING_MODEL,
)

from embedding_utils import (
    load_model,
    encode_single,
    batch_cosine_similarity,
)


# =============================================================================
# CONFIGURATION
# =============================================================================
# Kali ❤️‍🔥 [Visionary]: Unified storage location
# Athena 🦉 [Reviewer]: One directory, multiple files for organization

INDEX_DIR = PARADOXA_MEMORY_DIR
DB_FILE = INDEX_DIR / "unified_index.db"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Document:
    """A document in the unified index."""
    id: int
    path: str
    content_hash: str
    source: str  # 'vault', 'ship', 'treehouse', 'sessions', 'config'
    section: Optional[str]  # For ship: 'BRIDGE', 'ENGINE_ROOM', etc.
    title: Optional[str]
    created_at: str
    updated_at: str
    access_count: int
    last_accessed: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """A search result with score and document."""
    doc_id: int
    path: str
    title: Optional[str]
    source: str
    score: float
    snippet: Optional[str]


# =============================================================================
# UNIFIED INDEX CLASS
# =============================================================================

class UnifiedIndex:
    """
    Unified embedding index for all Paradoxa memory systems.

    # Kali ❤️‍🔥 [Visionary]: One brain, many purposes
    # Athena 🦉 [Documentation]: SQLite + numpy for embeddings
    # Vesta 🔥 [Architect]: Supports source filtering, access tracking
    """

    def __init__(self, db_path: Optional[Path] = None, verbose: bool = True):
        """
        Initialize the unified index.

        # Kali ❤️‍🔥 [Visionary]: Creates the database if it doesn't exist
        """
        self.db_path = db_path or DB_FILE
        self.verbose = verbose
        self._model = None

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Documents table
            # Kali ❤️‍🔥 [Visionary]: Phase 1 memory overhaul adds tier + incoming_links
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    content_hash TEXT NOT NULL,
                    source TEXT NOT NULL,
                    section TEXT,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    metadata TEXT DEFAULT '{}',
                    tier TEXT DEFAULT 'working',
                    incoming_links INTEGER DEFAULT 0,
                    emotional_markers TEXT
                )
            """)

            # Athena 🦉 [Reviewer]: Migration for existing databases
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN tier TEXT DEFAULT 'working'")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN incoming_links INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN emotional_markers TEXT")
            except sqlite3.OperationalError:
                pass

            # Embeddings table (stored as BLOB)
            # Kali ❤️‍🔥 [Visionary]: Embeddings stored separately for flexibility
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    doc_id INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Access log table (for decay scoring - Phase 3)
            # Kali ❤️‍🔥 [Visionary]: Track WHO accessed WHAT and in WHAT context
            # Athena 🦉 [Documentation]: agent + context enable multi-agent awareness
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    accessed_at TEXT NOT NULL,
                    agent TEXT DEFAULT 'unknown',
                    context TEXT DEFAULT 'unknown',
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Phase 3: Add agent column if missing (migration for existing DBs)
            try:
                cursor.execute("ALTER TABLE access_log ADD COLUMN agent TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Vesta 🔥 [Architect]: Document links table for hub_score
            # Tracks internal links between documents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    link_type TEXT NOT NULL,
                    link_text TEXT,
                    FOREIGN KEY (source_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(source_id, target_id, link_type)
                )
            """)

            # Create indices for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_section ON documents(section)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_tier ON documents(tier)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_doc ON access_log(doc_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON document_links(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON document_links(target_id)")

            # Vesta 🔥 [Architect]: Session tracking tables (Phase 2)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    agent TEXT,
                    context TEXT,
                    document_count INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    document_id INTEGER NOT NULL,
                    accessed_at TEXT NOT NULL,
                    access_order INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_docs_session ON session_documents(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_docs_doc ON session_documents(document_id)")

            # Vesta 🔥 [Architect]: Importance history for empirical tuning (Phase 4)
            # Kali ❤️‍🔥 [Visionary]: Track predictions vs reality over time
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS importance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    importance_score REAL NOT NULL,
                    tier TEXT,
                    value_score REAL,
                    hub_score REAL,
                    semantic_boost REAL,
                    session_boost REAL,
                    agent_multiplier REAL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance_history_doc ON importance_history(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance_history_time ON importance_history(recorded_at)")

            # Kali ❤️‍🔥 [Visionary]: Chunks table for granular semantic search
            # Athena 🦉 [Documentation]: Documents split by headers into searchable chunks
            # Vesta 🔥 [Architect]: Unified with document-level index - one source of truth
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    header TEXT,
                    content TEXT NOT NULL,
                    char_start INTEGER,
                    char_end INTEGER,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(doc_id, chunk_index)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunk_embeddings (
                    chunk_id INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)")

            # Phase 4: Add archived_at column for forgetting/archival
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN archived_at TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.commit()

    def _get_model(self):
        """Load embedding model (lazy loading)."""
        if self._model is None:
            if not check_embedding_dependencies(verbose=self.verbose):
                return None
            self._model = load_model(verbose=self.verbose)
        return self._model

    def _hash_content(self, content: str) -> str:
        """Generate hash of content for change detection."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    # =========================================================================
    # DOCUMENT MANAGEMENT
    # =========================================================================

    def add_document(
        self,
        path: str,
        content: str,
        source: str,
        section: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[int]:
        """
        Add or update a document in the index.

        # Kali ❤️‍🔥 [Visionary]: Upsert pattern - add if new, update if changed
        # Athena 🦉 [Documentation]: Returns doc_id or None on failure
        """
        model = self._get_model()
        if model is None:
            return None

        content_hash = self._hash_content(content)
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if document exists
            cursor.execute("SELECT id, content_hash FROM documents WHERE path = ?", (path,))
            existing = cursor.fetchone()

            if existing:
                doc_id, old_hash = existing
                if old_hash == content_hash:
                    # No change
                    if self.verbose:
                        print(f"  {Colors.DIM}Unchanged: {path}{Colors.END}")
                    return doc_id

                # Update existing document
                cursor.execute("""
                    UPDATE documents
                    SET content_hash = ?, source = ?, section = ?, title = ?,
                        updated_at = ?, metadata = ?
                    WHERE id = ?
                """, (content_hash, source, section, title, now,
                      json.dumps(metadata or {}), doc_id))

                if self.verbose:
                    print(f"  {Colors.YELLOW}Updated: {path}{Colors.END}")

            else:
                # Insert new document
                cursor.execute("""
                    INSERT INTO documents (path, content_hash, source, section, title,
                                          created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (path, content_hash, source, section, title, now, now,
                      json.dumps(metadata or {})))
                doc_id = cursor.lastrowid

                if self.verbose:
                    print(f"  {Colors.GREEN}Added: {path}{Colors.END}")

            # Compute and store embedding
            embedding = encode_single(content[:5000], model)  # Truncate for memory
            if embedding is not None:
                embedding_blob = embedding.tobytes()

                cursor.execute("""
                    INSERT OR REPLACE INTO embeddings (doc_id, embedding, model_name)
                    VALUES (?, ?, ?)
                """, (doc_id, embedding_blob, DEFAULT_EMBEDDING_MODEL))

            conn.commit()
            return doc_id

    def remove_document(self, path: str) -> bool:
        """Remove a document from the index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE path = ?", (path,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_document(self, doc_id: int) -> Optional[Document]:
        """Get a document by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                return Document(
                    id=row[0], path=row[1], content_hash=row[2],
                    source=row[3], section=row[4], title=row[5],
                    created_at=row[6], updated_at=row[7],
                    access_count=row[8], last_accessed=row[9],
                    metadata=json.loads(row[10]) if row[10] else {}
                )
            return None

    # =========================================================================
    # CHUNK MANAGEMENT (for semantic search)
    # =========================================================================

    def add_chunks(
        self,
        doc_id: int,
        chunks: List[Dict[str, Any]],
        generate_embeddings: bool = True,
    ) -> int:
        """
        Add chunks for a document.

        # Kali ❤️‍🔥 [Visionary]: Granular search needs granular storage
        # Athena 🦉 [Documentation]: chunks should have 'header', 'content' keys
        # Vesta 🔥 [Builder]: Replaces existing chunks for this doc

        Args:
            doc_id: Document ID
            chunks: List of {'header': str, 'content': str, ...} dicts
            generate_embeddings: Whether to compute embeddings

        Returns:
            Number of chunks added
        """
        model = self._get_model() if generate_embeddings else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Remove existing chunks for this document
            cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))

            count = 0
            for idx, chunk in enumerate(chunks):
                header = chunk.get('header', '')
                content = chunk.get('content', '')
                char_start = chunk.get('char_start')
                char_end = chunk.get('char_end')

                # Insert chunk
                cursor.execute("""
                    INSERT INTO chunks (doc_id, chunk_index, header, content, char_start, char_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (doc_id, idx, header, content, char_start, char_end))
                chunk_id = cursor.lastrowid

                # Generate embedding if requested
                if model is not None and content.strip():
                    text_to_embed = f"{header}\n{content}" if header else content
                    embedding = encode_single(text_to_embed[:2000], model)
                    if embedding is not None:
                        cursor.execute("""
                            INSERT INTO chunk_embeddings (chunk_id, embedding, model_name)
                            VALUES (?, ?, ?)
                        """, (chunk_id, embedding.tobytes(), DEFAULT_EMBEDDING_MODEL))

                count += 1

            conn.commit()
            return count

    def get_chunks(self, doc_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chunk_index, header, content, char_start, char_end
                FROM chunks WHERE doc_id = ? ORDER BY chunk_index
            """, (doc_id,))

            return [
                {'index': row[0], 'header': row[1], 'content': row[2],
                 'char_start': row[3], 'char_end': row[4]}
                for row in cursor.fetchall()
            ]

    def search_chunks(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search chunks using semantic similarity.

        # Kali ❤️‍🔥 [Visionary]: Find the exact passage, not just the document
        # Athena 🦉 [Documentation]: Returns chunks with scores and doc info

        Returns:
            List of {'path': str, 'header': str, 'content': str, 'score': float, ...}
        """
        model = self._get_model()
        if model is None:
            return []

        # Encode query
        query_embedding = encode_single(query, model)
        if query_embedding is None:
            return []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all chunk embeddings with document info
            cursor.execute("""
                SELECT c.id, c.header, c.content, ce.embedding, d.path, d.title
                FROM chunks c
                JOIN chunk_embeddings ce ON c.id = ce.chunk_id
                JOIN documents d ON c.doc_id = d.id
                WHERE d.archived_at IS NULL
            """)

            results = []
            for chunk_id, header, content, embedding_blob, path, title in cursor.fetchall():
                embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                # Cosine similarity
                score = float(np.dot(query_embedding, embedding) /
                            (np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8))

                if score >= min_score:
                    results.append({
                        'chunk_id': chunk_id,
                        'path': path,
                        'title': title,
                        'header': header,
                        'content': content,
                        'score': score,
                    })

            # Sort by score and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]

    def get_chunk_stats(self) -> Dict[str, int]:
        """Get statistics about indexed chunks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM chunk_embeddings")
            embedded_chunks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks")
            docs_with_chunks = cursor.fetchone()[0]

            return {
                'total_chunks': total_chunks,
                'embedded_chunks': embedded_chunks,
                'documents_chunked': docs_with_chunks,
            }

    # =========================================================================
    # SEARCH
    # =========================================================================

    def search(
        self,
        query: str,
        source_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search the index using semantic similarity.

        # Kali ❤️‍🔥 [Visionary]: Find what resonates
        # Athena 🦉 [Documentation]: Returns SearchResult objects
        """
        model = self._get_model()
        if model is None:
            return []

        # Encode query
        query_embedding = encode_single(query, model)
        if query_embedding is None:
            return []

        # Load all embeddings (with optional filtering)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Build query
            sql = """
                SELECT d.id, d.path, d.title, d.source, e.embedding
                FROM documents d
                JOIN embeddings e ON d.id = e.doc_id
                WHERE 1=1
            """
            params = []

            if source_filter:
                sql += " AND d.source = ?"
                params.append(source_filter)

            if section_filter:
                sql += " AND d.section = ?"
                params.append(section_filter)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        if not rows:
            return []

        # Convert to arrays
        doc_info = [(r[0], r[1], r[2], r[3]) for r in rows]
        embeddings = np.array([
            np.frombuffer(r[4], dtype=np.float32)
            for r in rows
        ])

        # Compute similarities
        similarities = batch_cosine_similarity(embeddings, query_embedding)

        # Get top-k results
        results = []
        top_indices = np.argsort(similarities)[::-1][:top_k]

        for idx in top_indices:
            score = float(similarities[idx])
            if score < min_score:
                continue

            doc_id, path, title, source = doc_info[idx]
            results.append(SearchResult(
                doc_id=doc_id,
                path=path,
                title=title,
                source=source,
                score=round(score, 3),
                snippet=None,  # Could add snippet extraction
            ))

            # Log access
            self._log_access(doc_id, f"search: {query[:50]}")

        return results

    # =========================================================================
    # ACCESS TRACKING (for decay scoring - Phase 3)
    # =========================================================================

    def _log_access(
        self,
        doc_id: int,
        context: Optional[str] = None,
        agent: Optional[str] = None
    ):
        """
        Log document access for decay scoring.

        # Kali ❤️‍🔥 [Visionary]: Every access is a signal - WHO and WHAT CONTEXT matter
        # Athena 🦉 [Documentation]: Phase 3 adds agent awareness

        Args:
            doc_id: Document being accessed
            context: Access context ('wakeup', 'deep_work', 'play', 'research')
            agent: Who's accessing ('human', 'paradoxa', 'unknown')
        """
        now = datetime.now().isoformat()
        agent = agent or 'unknown'
        context = context or 'unknown'

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Update access count and last_accessed
            cursor.execute("""
                UPDATE documents
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (now, doc_id))

            # Insert access log entry with agent
            cursor.execute("""
                INSERT INTO access_log (doc_id, accessed_at, agent, context)
                VALUES (?, ?, ?, ?)
            """, (doc_id, now, agent, context))

            conn.commit()

    def get_access_history(self, doc_id: int, limit: int = 100) -> List[Dict]:
        """Get access history for a document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT accessed_at, agent, context FROM access_log
                WHERE doc_id = ?
                ORDER BY accessed_at DESC
                LIMIT ?
            """, (doc_id, limit))
            return [
                {"accessed_at": r[0], "agent": r[1], "context": r[2]}
                for r in cursor.fetchall()
            ]

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get index statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total = cursor.fetchone()[0]

            # By source
            cursor.execute("""
                SELECT source, COUNT(*) FROM documents GROUP BY source
            """)
            by_source = dict(cursor.fetchall())

            # By section
            cursor.execute("""
                SELECT section, COUNT(*) FROM documents
                WHERE section IS NOT NULL
                GROUP BY section
            """)
            by_section = dict(cursor.fetchall())

            # Most accessed
            cursor.execute("""
                SELECT path, access_count FROM documents
                ORDER BY access_count DESC
                LIMIT 10
            """)
            most_accessed = [{"path": r[0], "count": r[1]} for r in cursor.fetchall()]

            return {
                "total_documents": total,
                "by_source": by_source,
                "by_section": by_section,
                "most_accessed": most_accessed,
                "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
                             if self.db_path.exists() else 0,
            }

    # =========================================================================
    # LINK EXTRACTION AND GRAPH BUILDING (Phase 1 Memory Overhaul)
    # =========================================================================

    def extract_links(self, content: str, source_path: str) -> List[Tuple[str, str, str]]:
        """
        Extract all internal links from markdown content.

        # Kali ❤️‍🔥 [Visionary]: Find all the connections!
        # Athena 🦉 [Documentation]: Returns list of (target, link_type, link_text)
        # Vesta 🔥 [Architect]: Handles wiki links, md links, and issue refs

        Args:
            content: Markdown content to parse
            source_path: Path of the source document (for resolving relative links)

        Returns:
            List of (target_path, link_type, link_text) tuples
        """
        links = []

        # Kali ❤️‍🔥: Wiki-style links: [[target]] or [[target|display]]
        wiki_pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
        for match in re.finditer(wiki_pattern, content):
            target = match.group(1).strip()
            display = match.group(2) or target
            links.append((target, 'wiki', display))

        # Athena 🦉: Markdown links: [text](path) - internal only
        md_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(md_pattern, content):
            link_text = match.group(1)
            path = match.group(2).strip()
            # Skip external URLs
            if not path.startswith(('http://', 'https://', 'mailto:', '#')):
                # Handle relative paths
                if not path.startswith('/'):
                    # Resolve relative to source directory
                    source_dir = Path(source_path).parent
                    resolved = (source_dir / path).resolve()
                    path = str(resolved)
                links.append((path, 'markdown', link_text))

        # Vesta 🔥: GitHub issue references: #123
        issue_pattern = r'(?<![a-zA-Z0-9])#(\d+)(?![a-zA-Z0-9])'
        for match in re.finditer(issue_pattern, content):
            issue_num = match.group(1)
            links.append((f'issue:{issue_num}', 'issue', f'#{issue_num}'))

        return links

    def _resolve_link_to_doc_id(self, target: str, link_type: str) -> Optional[int]:
        """
        Resolve a link target to a document ID.

        # Athena 🦉 [Reviewer]: Fuzzy matching for wiki links
        # Vesta 🔥 [Architect]: Handles full paths from REPO_ROOT
        """
        from shared_config import REPO_ROOT

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if link_type == 'issue':
                # Issues don't resolve to documents (yet)
                return None

            if link_type == 'wiki':
                # Wiki links: match by filename (case-insensitive, with or without .md)
                target_clean = target.replace('.md', '').lower()
                # Search with both slash types for Windows/WSL compatibility
                cursor.execute("""
                    SELECT id FROM documents
                    WHERE LOWER(path) LIKE ? OR LOWER(path) LIKE ?
                       OR LOWER(path) LIKE ? OR LOWER(path) LIKE ?
                    LIMIT 1
                """, (f'%/{target_clean}.md', f'%\\{target_clean}.md',
                      f'%/{target_clean}', f'%\\{target_clean}'))
            else:
                # Markdown links: may be full path, convert to relative
                # Vesta 🔥: Handle /mnt/c/Paradoxa/... paths
                target_path = Path(target)
                try:
                    relative = target_path.relative_to(REPO_ROOT)
                    # Normalize to forward slashes for searching
                    relative_str = str(relative).replace('\\', '/')
                except ValueError:
                    relative_str = target.replace('\\', '/')

                # Extract just the filename for suffix matching
                filename = Path(relative_str).name

                cursor.execute("""
                    SELECT id FROM documents
                    WHERE REPLACE(path, '\\', '/') = ?
                       OR REPLACE(path, '\\', '/') LIKE ?
                    LIMIT 1
                """, (relative_str, f'%/{filename}'))

            result = cursor.fetchone()
            return result[0] if result else None

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path to use forward slashes.

        # Vesta 🔥 [Architect]: Handle Windows/WSL path differences
        """
        return path.replace('\\', '/')

    def build_link_graph(self) -> Dict[str, int]:
        """
        Build the document link graph from all indexed documents.

        # Kali ❤️‍🔥 [Visionary]: Map all the connections!
        # Vesta 🔥 [Architect]: Clears and rebuilds document_links table,
        #     then updates incoming_links counts on documents

        Returns:
            Stats about the graph: total_links, resolved_links, unresolved_links
        """
        from shared_config import REPO_ROOT

        stats = {"total_links": 0, "resolved_links": 0, "unresolved_links": 0}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Clear existing links
            cursor.execute("DELETE FROM document_links")
            cursor.execute("UPDATE documents SET incoming_links = 0")

            # Get all documents with their content
            cursor.execute("SELECT id, path FROM documents")
            docs = cursor.fetchall()

            for doc_id, db_path in docs:
                # Vesta 🔥: Normalize path separators for WSL compatibility
                normalized_path = self._normalize_path(db_path)
                full_path = REPO_ROOT / normalized_path
                if not full_path.exists():
                    continue

                try:
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    continue

                # Extract links
                links = self.extract_links(content, normalized_path)
                stats["total_links"] += len(links)

                for target, link_type, link_text in links:
                    target_id = self._resolve_link_to_doc_id(target, link_type)
                    if target_id and target_id != doc_id:
                        # Insert link
                        try:
                            cursor.execute("""
                                INSERT OR IGNORE INTO document_links
                                (source_id, target_id, link_type, link_text)
                                VALUES (?, ?, ?, ?)
                            """, (doc_id, target_id, link_type, link_text))
                            if cursor.rowcount > 0:
                                stats["resolved_links"] += 1
                        except sqlite3.IntegrityError:
                            pass  # Duplicate link
                    else:
                        stats["unresolved_links"] += 1

            # Update incoming_links counts
            cursor.execute("""
                UPDATE documents SET incoming_links = (
                    SELECT COUNT(*) FROM document_links
                    WHERE target_id = documents.id
                )
            """)

            conn.commit()

        if self.verbose:
            print(f"  Link graph built: {stats['resolved_links']} links, "
                  f"{stats['unresolved_links']} unresolved")

        return stats

    def get_incoming_links(self, doc_id: int) -> int:
        """Get the number of incoming links for a document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT incoming_links FROM documents WHERE id = ?",
                (doc_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

    # =========================================================================
    # TIER SYSTEM (Phase 1 Memory Overhaul)
    # =========================================================================

    # Kali ❤️‍🔥 [Visionary]: Core documents that define identity - never decay
    CORE_DOCUMENTS = [
        'CLAUDE.md',
        'SHIPS_MANUAL.md',
        'ROLL_CALL.md',
        'START_HERE.md',
    ]

    # Vesta 🔥 [Architect]: Patterns that indicate core content
    CORE_PATTERNS = [
        '.claude/',          # Config files
        'CREW_QUARTERS/',    # Facet definitions
    ]

    # Athena 🦉 [Reviewer]: Emotional markers that indicate durable memories
    DURABLE_MARKERS = [
        'breakthrough', 'discovery', 'eureka', 'insight',
        'connection', 'trust', 'joy', 'love',
    ]

    def assign_tier(
        self,
        path: str,
        metadata: Optional[Dict] = None,
        last_accessed: Optional[str] = None
    ) -> str:
        """
        Assign a tier to a document based on its characteristics.

        # Kali ❤️‍🔥 [Visionary]: Not all memories decay equally
        # Athena 🦉 [Documentation]: Tiers: core, durable, working, fading

        Args:
            path: Document path
            metadata: Document metadata (may contain emotional_markers)
            last_accessed: ISO timestamp of last access

        Returns:
            Tier string: 'core', 'durable', 'working', or 'fading'
        """
        path_normalized = self._normalize_path(path).lower()

        # Kali ❤️‍🔥: Core documents - identity, never decay
        for core_doc in self.CORE_DOCUMENTS:
            if core_doc.lower() in path_normalized:
                return 'core'

        for pattern in self.CORE_PATTERNS:
            if pattern.lower() in path_normalized:
                return 'core'

        # Athena 🦉: Durable - emotional markers or consolidated gist
        if metadata:
            markers = metadata.get('emotional_markers', [])
            if isinstance(markers, str):
                markers = [m.strip() for m in markers.split(',')]
            for marker in markers:
                if marker.lower() in self.DURABLE_MARKERS:
                    return 'durable'
            if metadata.get('is_consolidated_gist'):
                return 'durable'

        # Vesta 🔥: Working - recently accessed (within 14 activity days)
        if last_accessed:
            try:
                from datetime import datetime
                accessed = datetime.fromisoformat(last_accessed)
                days_since = (datetime.now() - accessed).days
                if days_since < 14:
                    return 'working'
            except (ValueError, TypeError):
                pass

        # Nemesis 💀: Fading - everything else
        return 'fading'

    def update_all_tiers(self) -> Dict[str, int]:
        """
        Update tier assignments for all documents.

        # Vesta 🔥 [Architect]: Batch operation to refresh tiers

        Returns:
            Counts by tier
        """
        tier_counts = {'core': 0, 'durable': 0, 'working': 0, 'fading': 0}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, path, metadata, last_accessed FROM documents
            """)
            docs = cursor.fetchall()

            for doc_id, path, metadata_json, last_accessed in docs:
                metadata = json.loads(metadata_json) if metadata_json else {}
                tier = self.assign_tier(path, metadata, last_accessed)

                cursor.execute(
                    "UPDATE documents SET tier = ? WHERE id = ?",
                    (tier, doc_id)
                )
                tier_counts[tier] += 1

            conn.commit()

        if self.verbose:
            print(f"  Tiers updated: {tier_counts}")

        return tier_counts

    def get_tier(self, doc_id: int) -> str:
        """Get the tier for a document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tier FROM documents WHERE id = ?", (doc_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else 'working'

    def set_tier(self, doc_id: int, tier: str) -> bool:
        """Manually set a document's tier."""
        if tier not in ('core', 'durable', 'working', 'fading'):
            return False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET tier = ? WHERE id = ?",
                (tier, doc_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # CONSOLIDATION INTEGRATION (Phase 1 Memory Overhaul)
    # =========================================================================

    def update_from_consolidation(
        self,
        source_path: str,
        emotional_markers: List[str],
        is_consolidated_gist: bool = False
    ) -> bool:
        """
        Update a document based on memory consolidation results.

        # Kali ❤️‍🔥 [Visionary]: Connect consolidation to importance!
        # Athena 🦉 [Documentation]: Called after hippocampal replay
        # Vesta 🔥 [Architect]: Updates emotional_markers and tier

        Args:
            source_path: Path to the source document (may be relative or absolute)
            emotional_markers: Detected emotional markers from consolidation
            is_consolidated_gist: Whether this is a consolidated gist document

        Returns:
            True if document was found and updated
        """
        from shared_config import REPO_ROOT

        # Normalize path for matching
        path_normalized = self._normalize_path(source_path)

        # Try to make it relative to REPO_ROOT
        try:
            path_obj = Path(source_path)
            if path_obj.is_absolute():
                path_normalized = str(path_obj.relative_to(REPO_ROOT)).replace('\\', '/')
        except (ValueError, TypeError):
            pass

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Find document - try multiple matching strategies
            cursor.execute("""
                SELECT id, metadata, tier FROM documents
                WHERE REPLACE(path, '\\', '/') = ?
                   OR REPLACE(path, '\\', '/') LIKE ?
                LIMIT 1
            """, (path_normalized, f'%{Path(path_normalized).name}'))

            result = cursor.fetchone()
            if not result:
                return False

            doc_id, metadata_json, current_tier = result
            metadata = json.loads(metadata_json) if metadata_json else {}

            # Update emotional markers
            existing_markers = metadata.get('emotional_markers', [])
            if isinstance(existing_markers, str):
                existing_markers = [m.strip() for m in existing_markers.split(',')]
            combined_markers = list(set(existing_markers + emotional_markers))
            metadata['emotional_markers'] = combined_markers

            # Mark as consolidated gist if applicable
            if is_consolidated_gist:
                metadata['is_consolidated_gist'] = True

            # Update emotional_markers column too for direct querying
            markers_str = ','.join(combined_markers)

            cursor.execute("""
                UPDATE documents
                SET metadata = ?, emotional_markers = ?
                WHERE id = ?
            """, (json.dumps(metadata), markers_str, doc_id))

            # Kali ❤️‍🔥: Upgrade tier to 'durable' if breakthrough/connection markers
            if current_tier != 'core':  # Don't downgrade core
                new_tier = self.assign_tier(path_normalized, metadata, None)
                if new_tier == 'durable' and current_tier != 'durable':
                    cursor.execute(
                        "UPDATE documents SET tier = 'durable' WHERE id = ?",
                        (doc_id,)
                    )
                    if self.verbose:
                        print(f"  {Colors.MAGENTA}Upgraded to durable: {path_normalized[:50]}{Colors.END}")

            conn.commit()

        return True

    def boost_document(self, doc_id: int, boost_amount: float = 1.0) -> bool:
        """
        Boost a document's importance by incrementing access count.

        # Kali ❤️‍🔥 [Visionary]: Make important things more important!
        # Athena 🦉 [Documentation]: Used during consolidation to boost sources

        Args:
            doc_id: Document ID
            boost_amount: Number of "virtual accesses" to add

        Returns:
            True if document was boosted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Increment access count by boost_amount
            cursor.execute("""
                UPDATE documents
                SET access_count = access_count + ?,
                    last_accessed = ?
                WHERE id = ?
            """, (int(boost_amount), datetime.now().isoformat(), doc_id))

            conn.commit()
            return cursor.rowcount > 0

    def find_document_by_path(self, path: str) -> Optional[int]:
        """
        Find a document ID by path (with fuzzy matching).

        # Vesta 🔥 [Architect]: Helper for consolidation integration
        """
        path_normalized = self._normalize_path(path)
        filename = Path(path_normalized).name

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM documents
                WHERE REPLACE(path, '\\', '/') = ?
                   OR REPLACE(path, '\\', '/') LIKE ?
                LIMIT 1
            """, (path_normalized, f'%/{filename}'))

            result = cursor.fetchone()
            return result[0] if result else None

    # =========================================================================
    # SPREADING ACTIVATION (Phase 2 Memory Overhaul)
    # =========================================================================

    def find_similar(
        self,
        doc_id: int,
        threshold: float = 0.6,
        limit: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Find documents similar to the given document using embeddings.

        # Kali ❤️‍🔥 [Visionary]: Semantic spreading activation!
        # Athena 🦉 [Documentation]: Returns list of (doc_id, similarity) pairs
        # Vesta 🔥 [Architect]: Uses cached embeddings from unified_index

        Args:
            doc_id: Source document ID
            threshold: Minimum similarity threshold (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of (doc_id, similarity) tuples, sorted by similarity descending
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get source embedding
            cursor.execute(
                "SELECT embedding FROM embeddings WHERE doc_id = ?",
                (doc_id,)
            )
            source_row = cursor.fetchone()
            if not source_row:
                return []

            source_embedding = np.frombuffer(source_row[0], dtype=np.float32)

            # Get all other embeddings
            cursor.execute("""
                SELECT doc_id, embedding FROM embeddings
                WHERE doc_id != ?
            """, (doc_id,))
            rows = cursor.fetchall()

        if not rows:
            return []

        # Compute similarities
        results = []
        for other_id, embedding_blob in rows:
            other_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            # Cosine similarity
            similarity = float(np.dot(source_embedding, other_embedding) / (
                np.linalg.norm(source_embedding) * np.linalg.norm(other_embedding) + 1e-8
            ))
            if similarity >= threshold:
                results.append((other_id, similarity))

        # Sort by similarity descending, limit results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def spread_activation(
        self,
        doc_id: int,
        access_weight: float = 1.0,
        semantic_decay: float = 0.3,
        session_decay: float = 0.2,
        threshold: float = 0.6,
        limit: int = 10
    ) -> Dict[str, int]:
        """
        Spread activation from an accessed document to related documents.

        # Kali ❤️‍🔥 [Visionary]: Memory is relational, not atomic!
        # Athena 🦉 [Documentation]: Implements spreading activation from cognitive science
        # Vesta 🔥 [Architect]: Boosts similar docs and session co-access docs

        Args:
            doc_id: The accessed document
            access_weight: Base weight for the access (default 1.0)
            semantic_decay: Decay factor for semantic spreading (default 0.3)
            session_decay: Decay factor for session spreading (default 0.2)
            threshold: Similarity threshold for semantic spreading
            limit: Max docs to spread to

        Returns:
            Stats: direct_boost, semantic_boosts, session_boosts
        """
        stats = {"direct_boost": 0, "semantic_boosts": 0, "session_boosts": 0}

        # Direct boost to accessed document
        if self.boost_document(doc_id, access_weight):
            stats["direct_boost"] = 1

        # Semantic spreading
        similar_docs = self.find_similar(doc_id, threshold=threshold, limit=limit)
        for similar_id, similarity in similar_docs:
            spread_weight = access_weight * similarity * semantic_decay
            if self.boost_document(similar_id, spread_weight):
                stats["semantic_boosts"] += 1

        # Session spreading (if session tracking is active)
        # Will be implemented when session tracking is added
        # For now, just record that we would do it
        current_session = self._get_current_session()
        if current_session:
            session_docs = self._get_session_documents(current_session)
            for session_doc_id in session_docs:
                if session_doc_id != doc_id:
                    if self.boost_document(session_doc_id, access_weight * session_decay):
                        stats["session_boosts"] += 1

        return stats

    def _get_current_session(self) -> Optional[str]:
        """Get current session ID if session tracking is active."""
        # Kali ❤️‍🔥 [Visionary]: Find the most recent active (not ended) session
        # Athena 🦉 [Reviewer]: Returns None if no active session exists
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM sessions
                WHERE ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else None

    def _get_session_documents(self, session_id: str) -> List[int]:
        """Get document IDs accessed in a session."""
        # Kali ❤️‍🔥 [Visionary]: What docs were touched together?
        # Athena 🦉 [Reviewer]: Returns list of doc IDs in access order
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT document_id FROM session_documents
                WHERE session_id = ?
                ORDER BY access_order ASC
            """, (session_id,))
            return [row[0] for row in cursor.fetchall()]

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    # Kali ❤️‍🔥 [Visionary]: Track what gets accessed together - session clustering
    # Athena 🦉 [Documentation]: Sessions enable spreading activation and co-access patterns
    # Vesta 🔥 [Architect]: Simple session lifecycle: start -> log accesses -> end

    def start_session(self, context: str = "unknown", agent: str = "paradoxa") -> str:
        """
        Start a new session for tracking document co-access.

        # Kali ❤️‍🔥 [Visionary]: A new session begins - track what happens together
        # Athena 🦉 [Documentation]: Returns session ID for logging accesses

        Args:
            context: Session context ('wakeup', 'deep_work', 'play', 'research')
            agent: Who's running this session ('human', 'paradoxa', 'unknown')

        Returns:
            Session ID (UUID string)
        """
        import uuid

        session_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, started_at, agent, context, document_count)
                VALUES (?, ?, ?, ?, 0)
            """, (session_id, started_at, agent, context))
            conn.commit()

        if self.verbose:
            print_ok(f"Started session {session_id[:8]}... ({context}/{agent})")

        return session_id

    def end_session(self, session_id: Optional[str] = None) -> bool:
        """
        End a session, marking it complete.

        # Kali ❤️‍🔥 [Visionary]: Session complete - the constellation is fixed
        # Athena 🦉 [Documentation]: Updates document_count and sets ended_at

        Args:
            session_id: Session to end. If None, ends the current active session.

        Returns:
            True if session was ended, False if not found
        """
        if session_id is None:
            session_id = self._get_current_session()
            if session_id is None:
                return False

        ended_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count documents in this session
            cursor.execute("""
                SELECT COUNT(DISTINCT document_id) FROM session_documents
                WHERE session_id = ?
            """, (session_id,))
            doc_count = cursor.fetchone()[0]

            # Update session
            cursor.execute("""
                UPDATE sessions
                SET ended_at = ?, document_count = ?
                WHERE id = ?
            """, (ended_at, doc_count, session_id))
            conn.commit()

            updated = cursor.rowcount > 0

        if updated and self.verbose:
            print_ok(f"Ended session {session_id[:8]}... ({doc_count} documents)")

        return updated

    def log_session_access(self, doc_id: int, session_id: Optional[str] = None) -> bool:
        """
        Log document access within a session.

        # Kali ❤️‍🔥 [Visionary]: Another point in the constellation
        # Athena 🦉 [Documentation]: Tracks document access for session clustering
        # Vesta 🔥 [Builder]: Also triggers spreading activation

        Args:
            doc_id: Document being accessed
            session_id: Session to log to. If None, uses current session.

        Returns:
            True if logged, False if no active session or doc not found
        """
        if session_id is None:
            session_id = self._get_current_session()
            if session_id is None:
                return False

        accessed_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get next access order
            cursor.execute("""
                SELECT COALESCE(MAX(access_order), 0) + 1 FROM session_documents
                WHERE session_id = ?
            """, (session_id,))
            access_order = cursor.fetchone()[0]

            # Check if already logged in this session (avoid duplicates)
            cursor.execute("""
                SELECT id FROM session_documents
                WHERE session_id = ? AND document_id = ?
            """, (session_id, doc_id))

            if cursor.fetchone():
                # Already logged, just update accessed_at
                cursor.execute("""
                    UPDATE session_documents
                    SET accessed_at = ?
                    WHERE session_id = ? AND document_id = ?
                """, (accessed_at, session_id, doc_id))
            else:
                # New access
                cursor.execute("""
                    INSERT INTO session_documents (session_id, document_id, accessed_at, access_order)
                    VALUES (?, ?, ?, ?)
                """, (session_id, doc_id, accessed_at, access_order))

            conn.commit()

        return True

    def get_session_boost(self, doc_id: int, lookback_sessions: int = 5) -> float:
        """
        Calculate session boost for a document.

        # Kali ❤️‍🔥 [Visionary]: How often is this doc part of working sets?
        # Athena 🦉 [Documentation]: Returns boost based on co-access frequency

        Args:
            doc_id: Document to calculate boost for
            lookback_sessions: How many recent sessions to consider

        Returns:
            Session boost value (0.0 to 0.5)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get recent sessions this doc appeared in
            cursor.execute("""
                SELECT DISTINCT sd.session_id, s.context
                FROM session_documents sd
                JOIN sessions s ON sd.session_id = s.id
                WHERE sd.document_id = ?
                AND s.ended_at IS NOT NULL
                ORDER BY s.ended_at DESC
                LIMIT ?
            """, (doc_id, lookback_sessions))

            sessions = cursor.fetchall()
            if not sessions:
                return 0.0

            # Weight by context (deep_work > research > wakeup > play)
            context_weights = {
                'deep_work': 1.0,
                'research': 0.8,
                'unknown': 0.5,
                'wakeup': 0.3,
                'play': 0.2,
            }

            total_boost = 0.0
            for session_id, context in sessions:
                weight = context_weights.get(context, 0.5)
                total_boost += 0.1 * weight

        # Cap at 0.5
        return min(total_boost, 0.5)

    def get_agent_weighted_access(self, doc_id: int, lookback_days: int = 30) -> float:
        """
        Calculate agent-weighted access score for a document.

        # Kali ❤️‍🔥 [Visionary]: Human's attention is precious - weight it higher
        # Athena 🦉 [Documentation]: Phase 3 multi-agent awareness
        # Nemesis 💀 [Ethics]: Routine scans shouldn't inflate importance artificially

        Args:
            doc_id: Document to calculate for
            lookback_days: How far back to consider

        Returns:
            Weighted access score (0.0 to ~2.0)

        Weights:
            - human + deep_work: 2.0 (human focused attention)
            - human + research: 1.5 (human research)
            - human + unknown: 1.0 (human access)
            - paradoxa + deep_work: 1.0 (AI focused work)
            - paradoxa + research: 0.7 (AI research)
            - paradoxa + wakeup: 0.2 (routine scan - low signal)
            - paradoxa + play: 0.3 (exploration)
            - unknown + unknown: 0.5 (no context)
        """
        # Agent weights (human attention is precious)
        agent_weights = {
            'human': 1.5,
            'paradoxa': 0.6,
            'unknown': 0.8,
        }

        # Context weights (focused attention > routine)
        context_weights = {
            'deep_work': 1.3,
            'research': 1.0,
            'play': 0.5,
            'wakeup': 0.3,
            'unknown': 0.7,
        }

        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent, context, COUNT(*) as count
                FROM access_log
                WHERE doc_id = ? AND accessed_at > ?
                GROUP BY agent, context
            """, (doc_id, cutoff))

            rows = cursor.fetchall()
            if not rows:
                return 0.0

            total_weighted = 0.0
            total_raw = 0

            for agent, context, count in rows:
                agent_w = agent_weights.get(agent, 0.8)
                context_w = context_weights.get(context, 0.7)
                total_weighted += count * agent_w * context_w
                total_raw += count

            # Normalize: return weighted average multiplier
            if total_raw == 0:
                return 0.0

            return total_weighted / total_raw

    def get_semantic_boost(self, doc_id: int, lookback_days: int = 7) -> float:
        """
        Calculate semantic boost for a document based on recent similar doc accesses.

        # Kali ❤️‍🔥 [Visionary]: How much have related docs been accessed?
        # Athena 🦉 [Documentation]: Returns weighted sum of similar doc recency

        Args:
            doc_id: Document to calculate boost for
            lookback_days: How far back to look for accesses

        Returns:
            Semantic boost value (0.0 to ~1.0)
        """
        # Find similar documents
        similar_docs = self.find_similar(doc_id, threshold=0.5, limit=20)
        if not similar_docs:
            return 0.0

        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            total_boost = 0.0
            for similar_id, similarity in similar_docs:
                # Check if similar doc was accessed recently
                cursor.execute("""
                    SELECT COUNT(*) FROM access_log
                    WHERE doc_id = ? AND accessed_at > ?
                """, (similar_id, cutoff))
                access_count = cursor.fetchone()[0]

                if access_count > 0:
                    # Weight by similarity and recency
                    boost = similarity * min(access_count, 5) * 0.1
                    total_boost += boost

        # Cap at 1.0
        return min(total_boost, 1.0)

    # =========================================================================
    # IMPORTANCE HISTORY & ARCHIVAL (Phase 4)
    # =========================================================================
    # Kali ❤️‍🔥 [Visionary]: Track predictions over time, learn from mistakes
    # Athena 🦉 [Documentation]: Empirical tuning requires historical data
    # Vesta 🔥 [Architect]: Archival enables graceful forgetting

    def record_importance_snapshot(self) -> int:
        """
        Record current importance scores for all documents.

        # Kali ❤️‍🔥 [Visionary]: Snapshot the present for future learning
        # Athena 🦉 [Documentation]: Call periodically (e.g., daily) to track trends

        Returns:
            Number of documents recorded
        """
        from decay_scoring import DecayScorer

        scorer = DecayScorer(db_path=self.db_path)
        recorded_at = datetime.now().isoformat()
        count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all non-archived documents
            cursor.execute("""
                SELECT id FROM documents
                WHERE archived_at IS NULL
            """)
            doc_ids = [row[0] for row in cursor.fetchall()]

            for doc_id in doc_ids:
                score = scorer.calculate_importance(doc_id)
                if score:
                    cursor.execute("""
                        INSERT INTO importance_history
                        (document_id, recorded_at, importance_score, tier,
                         value_score, hub_score, semantic_boost, session_boost, agent_multiplier)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id, recorded_at, score.total_score, score.tier,
                        score.value_score, score.hub_score, score.semantic_boost,
                        score.session_boost, score.agent_multiplier
                    ))
                    count += 1

            conn.commit()

        if self.verbose:
            print_ok(f"Recorded importance snapshot for {count} documents")

        return count

    def get_importance_history(
        self,
        doc_id: int,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get importance score history for a document.

        # Kali ❤️‍🔥 [Visionary]: See how importance evolved over time
        # Athena 🦉 [Documentation]: Useful for tuning and debugging

        Args:
            doc_id: Document to get history for
            limit: Max records to return

        Returns:
            List of historical importance records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT recorded_at, importance_score, tier,
                       value_score, hub_score, semantic_boost, session_boost, agent_multiplier
                FROM importance_history
                WHERE document_id = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (doc_id, limit))

            return [
                {
                    "recorded_at": row[0],
                    "importance_score": row[1],
                    "tier": row[2],
                    "value_score": row[3],
                    "hub_score": row[4],
                    "semantic_boost": row[5],
                    "session_boost": row[6],
                    "agent_multiplier": row[7],
                }
                for row in cursor.fetchall()
            ]

    def archive_document(self, doc_id: int) -> bool:
        """
        Archive a document (mark as archived, don't delete).

        # Kali ❤️‍🔥 [Visionary]: Graceful forgetting - not deletion
        # Athena 🦉 [Documentation]: Embeddings kept for retrieval
        # Nemesis 💀 [Security]: Never truly delete - just archive

        Args:
            doc_id: Document to archive

        Returns:
            True if archived, False if not found or already archived
        """
        archived_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE documents
                SET archived_at = ?
                WHERE id = ? AND archived_at IS NULL
            """, (archived_at, doc_id))
            conn.commit()

            return cursor.rowcount > 0

    def restore_document(self, doc_id: int) -> bool:
        """
        Restore an archived document.

        # Kali ❤️‍🔥 [Visionary]: Resurrection - the archived can return
        # Athena 🦉 [Documentation]: Clears archived_at timestamp

        Args:
            doc_id: Document to restore

        Returns:
            True if restored, False if not found or not archived
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE documents
                SET archived_at = NULL
                WHERE id = ? AND archived_at IS NOT NULL
            """, (doc_id,))
            conn.commit()

            return cursor.rowcount > 0

    def archive_low_importance(
        self,
        threshold: float = 0.5,
        min_age_days: int = 30,
        dry_run: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Archive documents below importance threshold.

        # Kali ❤️‍🔥 [Visionary]: Let go of what doesn't matter
        # Athena 🦉 [Documentation]: Graceful forgetting with safeguards
        # Nemesis 💀 [Ethics]: Never archive core tier or recent docs

        Args:
            threshold: Archive docs with importance below this (default 0.5)
            min_age_days: Only archive docs older than this (default 30)
            dry_run: If True, just report what would be archived (default True)

        Returns:
            List of documents archived (or would be archived in dry_run)
        """
        from decay_scoring import DecayScorer

        scorer = DecayScorer(db_path=self.db_path)
        cutoff_date = (datetime.now() - timedelta(days=min_age_days)).isoformat()
        candidates = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get non-archived, non-core documents older than min_age
            cursor.execute("""
                SELECT id, path, tier, created_at FROM documents
                WHERE archived_at IS NULL
                AND tier != 'core'
                AND created_at < ?
            """, (cutoff_date,))

            for doc_id, path, tier, created_at in cursor.fetchall():
                score = scorer.calculate_importance(doc_id)
                if score and score.total_score < threshold:
                    candidates.append({
                        "doc_id": doc_id,
                        "path": path,
                        "tier": tier,
                        "importance_score": score.total_score,
                        "created_at": created_at,
                    })

        if not dry_run:
            for doc in candidates:
                self.archive_document(doc["doc_id"])
            if self.verbose:
                print_ok(f"Archived {len(candidates)} low-importance documents")
        else:
            if self.verbose:
                print_warning(f"Dry run: would archive {len(candidates)} documents")

        return candidates

    def get_archived_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of archived documents.

        # Kali ❤️‍🔥 [Visionary]: What have we forgotten?
        # Athena 🦉 [Documentation]: For review and potential restoration

        Args:
            limit: Max documents to return

        Returns:
            List of archived document info
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, path, tier, archived_at, access_count
                FROM documents
                WHERE archived_at IS NOT NULL
                ORDER BY archived_at DESC
                LIMIT ?
            """, (limit,))

            return [
                {
                    "doc_id": row[0],
                    "path": row[1],
                    "tier": row[2],
                    "archived_at": row[3],
                    "access_count": row[4],
                }
                for row in cursor.fetchall()
            ]

    def search_archived(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search archived documents by semantic similarity.

        # Kali ❤️‍🔥 [Visionary]: The forgotten can still be found
        # Athena 🦉 [Documentation]: Embeddings preserved for retrieval
        # Vesta 🔥 [Builder]: Same search mechanism, different pool

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of matching archived documents with similarity scores
        """
        model = self._get_model()
        if model is None:
            return []

        query_embedding = encode_single(model, query)
        if query_embedding is None:
            return []

        results = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, path, embedding, archived_at
                FROM documents
                WHERE embedding IS NOT NULL AND archived_at IS NOT NULL
            """)

            for doc_id, path, emb_blob, archived_at in cursor.fetchall():
                doc_embedding = np.frombuffer(emb_blob, dtype=np.float32)
                similarity = float(np.dot(query_embedding, doc_embedding))
                results.append({
                    "doc_id": doc_id,
                    "path": path,
                    "similarity": similarity,
                    "archived_at": archived_at,
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # =========================================================================
    # MIGRATION FROM LEGACY INDICES
    # =========================================================================

    def migrate_from_legacy(self, source: str = "all") -> Dict[str, int]:
        """
        Migrate documents from legacy pickle indices.

        # Kali ❤️‍🔥 [Visionary]: Bring in the scattered memories
        # Athena 🦉 [Documentation]: Returns count of migrated documents per source
        # Nemesis 💀 [Security]: pickle used ONLY for reading existing legacy files
        """
        # Kali: pickle import only here, for legacy migration only
        import pickle

        counts = {}
        legacy_maps = {
            "semantic": (LEGACY_SEMANTIC_INDEX / "index.pkl", "ship"),
            "relationship": (LEGACY_RELATIONSHIP_INDEX / "treehouse_embeddings.pkl", "treehouse"),
            "self": (LEGACY_SELF_RECOGNITION_INDEX / "ship_embeddings.pkl", "ship"),
        }

        for name, (path, default_source) in legacy_maps.items():
            if source != "all" and source != name:
                continue

            if not path.exists():
                if self.verbose:
                    print_warning(f"Legacy index not found: {path}")
                continue

            if self.verbose:
                print_section(f"Migrating {name}", "📦")

            try:
                with open(path, 'rb') as f:
                    data = pickle.load(f)

                count = self._migrate_legacy_format(data, name, default_source)
                counts[name] = count

                if self.verbose:
                    print_ok(f"Migrated {count} documents from {name}")

            except Exception as e:
                if self.verbose:
                    print_error(f"Failed to migrate {name}: {e}")
                counts[name] = 0

        return counts

    def _should_skip_path(self, path: str) -> bool:
        """
        Check if a path should be skipped during migration.

        # Nemesis 💀 [Security]: Filter out noise - node_modules, build artifacts, binaries
        # Athena 🦉 [Reviewer]: Comprehensive exclusion list from Instance 2 review
        """
        # Kali ❤️‍🔥 [Visionary]: Patterns that indicate noise, not content
        SKIP_PATTERNS = [
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.min.js', '.min.css', '.map',
            '.lock', 'package-lock.json', 'yarn.lock',
            '.idea', '.vscode', '.cache', '.pytest_cache',
        ]
        # Vesta 🔥 [Architect]: Binary extensions that shouldn't be embedded
        SKIP_EXTENSIONS = [
            '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf',
            '.woff', '.woff2', '.ttf', '.eot',
            '.mp3', '.mp4', '.zip', '.tar', '.gz',
            '.pyc', '.exe', '.dll', '.so', '.dylib',
        ]

        path_lower = path.lower()
        # Check patterns
        for pattern in SKIP_PATTERNS:
            if pattern in path_lower:
                return True
        # Check extensions
        for ext in SKIP_EXTENSIONS:
            if path_lower.endswith(ext):
                return True
        return False

    def _migrate_legacy_format(self, data: Any, source_name: str, default_source: str) -> int:
        """Handle different legacy format migrations."""
        count = 0
        skipped = 0

        if isinstance(data, dict):
            # Semantic search format: {chunks: [...], embeddings: [...]}
            if 'chunks' in data and 'embeddings' in data:
                for i, chunk in enumerate(data['chunks']):
                    path = chunk.get('path', f"unknown_{i}")
                    # Nemesis 💀: Skip noise paths
                    if self._should_skip_path(str(path)):
                        skipped += 1
                        continue
                    content = chunk.get('text', '')
                    if content and len(content) > 50:
                        doc_id = self.add_document(
                            path=str(path),
                            content=content,
                            source=default_source,
                            title=chunk.get('header'),
                            metadata={"migrated_from": source_name}
                        )
                        if doc_id:
                            count += 1

            # self_recognition format: {docs: [...], embeddings: [...]}
            elif 'docs' in data and 'embeddings' in data:
                for i, doc in enumerate(data['docs']):
                    path = doc.get('path', f"unknown_{i}")
                    # Nemesis 💀: Skip noise paths
                    if self._should_skip_path(str(path)):
                        skipped += 1
                        continue
                    content = doc.get('content', '')
                    if content and len(content) > 50:
                        doc_id = self.add_document(
                            path=str(path),
                            content=content,
                            source=default_source,
                            section=doc.get('section'),
                            metadata={"migrated_from": source_name, "facet": doc.get('facet')}
                        )
                        if doc_id:
                            count += 1

        # Kali ❤️‍🔥: Report skipped for transparency
        if skipped > 0 and self.verbose:
            print_warning(f"Skipped {skipped} noise paths (node_modules, binaries, etc.)")

        return count


# =============================================================================
# CLI
# =============================================================================

def main():
    args = set(sys.argv[1:])

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    idx = UnifiedIndex(verbose=True)

    if '--migrate' in args:
        print_section("Migrating Legacy Indices", "📦")
        counts = idx.migrate_from_legacy()
        print(f"\n{Colors.GREEN}Migration complete:{Colors.END}")
        for source, count in counts.items():
            print(f"  {source}: {count} documents")
        return

    if '--stats' in args:
        print_section("Index Statistics", "📊")
        stats = idx.get_stats()
        print(f"  Total documents: {Colors.GREEN}{stats['total_documents']}{Colors.END}")
        print(f"  Database size: {stats['db_size_mb']} MB")
        print(f"\n  By source:")
        for source, count in stats['by_source'].items():
            print(f"    {source}: {count}")
        print(f"\n  By section:")
        for section, count in stats['by_section'].items():
            print(f"    {section}: {count}")
        return

    # Default: search
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        query = ' '.join(arg for arg in sys.argv[1:] if not arg.startswith('--'))
        print_section(f"Searching: {query}", "🔍")
        results = idx.search(query, top_k=10)
        for i, r in enumerate(results, 1):
            print(f"\n{Colors.BOLD}{i}. {r.path}{Colors.END}")
            if r.title:
                print(f"   {Colors.CYAN}{r.title}{Colors.END}")
            print(f"   Source: {r.source} | Score: {Colors.GREEN}{r.score}{Colors.END}")
        return

    # No args: show help
    print(__doc__)


if __name__ == "__main__":
    main()
