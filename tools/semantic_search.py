#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Search - Find docs by meaning, not keywords
=====================================================

# Kali [Visionary]: Natural language search for the repo! Instead of grepping
#     for exact keywords, you ask "how do we handle disagreement" and it finds
#     relevant docs even if they use different words.
#
# Athena [Reviewer]: Uses sentence-transformers to embed both your query
#     and all documents into the same vector space. Similar meanings cluster.
#
# Vesta [Architect]: Chunks documents by headers and size limits.
#     Embeds all chunks using all-MiniLM-L6-v2 (384-dimensional vectors).
#     Caches embeddings to disk (rebuilding is expensive).
#
# Nemesis [Security]: ALL LOCAL. No API calls. Your GPU does the work if
#     available, CPU fallback otherwise.
#
# Klea [Product]: Should this exist? Yes. Knowledge scattered across
#     hundreds of markdown files. This is how you find what you're looking for.

Attribution:
    MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
    Original Paradoxa implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)

Usage:
    python tools/semantic_search.py "how do we handle disagreement"
    python tools/semantic_search.py "where do files go"
    python tools/semantic_search.py --rebuild  # Rebuild index
    python tools/semantic_search.py --info     # Show index stats
"""

import os
import sys
import pickle
from pathlib import Path
from typing import List, Tuple, Optional

# Handle imports whether run as module or script
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    REPO_ROOT,
    SHIP_DIR,
    CLAUDE_DIR,
    LEGACY_SEMANTIC_INDEX,
    check_embedding_dependencies,
)

# Optional numpy import
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

# =============================================================================
# CONFIGURATION
# =============================================================================

INDEX_DIR = LEGACY_SEMANTIC_INDEX
INDEX_FILE = INDEX_DIR / "index.pkl"
HASH_FILE = INDEX_DIR / "file_hashes.json"

# Directories to search
SEARCH_DIRS = [
    SHIP_DIR,
    CLAUDE_DIR,
    REPO_ROOT / "docs",
]


# =============================================================================
# DOCUMENT DISCOVERY
# =============================================================================

def get_all_docs(search_path: Path = None) -> List[Tuple[Path, str]]:
    """
    Get all markdown files with their content.

    # Kali [Visionary]: Knowledge scattered across markdown files.
    # Athena [Documentation]: Searches specified path or defaults to ship dirs.
    # Vesta [Builder]: Skips files under 100 chars (too short to be useful).
    """
    docs = []

    # If search_path provided, just search that directory
    if search_path:
        search_dirs = [search_path]
    else:
        search_dirs = [d for d in SEARCH_DIRS if d.exists()]

    for search_dir in search_dirs:
        if search_dir.exists():
            for md_file in search_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8', errors='replace')
                    # Skip very short files
                    if len(content) > 100:
                        docs.append((md_file, content))
                except Exception:
                    pass

    return docs


# =============================================================================
# DOCUMENT CHUNKING
# =============================================================================

def chunk_document(path: Path, content: str, chunk_size: int = 500) -> List[dict]:
    """
    Split document into chunks for embedding.

    # Kali [Visionary]: Headers are natural boundaries. Use them!
    # Athena [Documentation]:
    #     1. Split by markdown headers (#, ##, etc.)
    #     2. If section is small enough, keep as-is
    #     3. If section is too big, split further by word count
    """
    chunks = []

    # Split by headers first
    sections = []
    current_section = ""
    current_header = ""

    for line in content.split('\n'):
        if line.startswith('#'):
            if current_section.strip():
                sections.append((current_header, current_section))
            current_header = line
            current_section = ""
        else:
            current_section += line + "\n"

    if current_section.strip():
        sections.append((current_header, current_section))

    # Create chunks from sections
    try:
        rel_path = str(path.relative_to(REPO_ROOT))
    except ValueError:
        rel_path = str(path)

    for header, section in sections:
        # If section is small enough, use as-is
        if len(section) <= chunk_size:
            chunks.append({
                'path': rel_path,
                'header': header.strip(),
                'content': section.strip(),
                'text': f"{header}\n{section}".strip()
            })
        else:
            # Split into smaller chunks by words
            words = section.split()
            for i in range(0, len(words), chunk_size // 5):
                chunk_words = words[i:i + chunk_size // 5]
                chunk_text = ' '.join(chunk_words)
                if len(chunk_text) > 50:  # Skip tiny chunks
                    chunks.append({
                        'path': rel_path,
                        'header': header.strip(),
                        'content': chunk_text,
                        'text': f"{header}\n{chunk_text}".strip()
                    })

    return chunks


# =============================================================================
# INDEX BUILDING
# =============================================================================

def build_index(force: bool = False) -> Optional[dict]:
    """
    Build or update the semantic search index.

    # Kali [Visionary]: GPU power! Embed everything in parallel!
    # Athena [Documentation]: Creates embeddings for all chunks.
    # Nemesis [Privacy]: All local, no API calls.

    Args:
        force: If True, rebuild even if index exists

    Returns:
        Index data dict or None on failure
    """
    if not check_embedding_dependencies():
        return None

    from embedding_utils import load_model, encode_texts

    INDEX_DIR.mkdir(exist_ok=True)

    print(f"{Colors.CYAN}Building semantic search index...{Colors.END}")

    # Get all docs
    docs = get_all_docs()
    print(f"  Found {len(docs)} markdown files")

    # Chunk documents
    all_chunks = []
    for path, content in docs:
        chunks = chunk_document(path, content)
        all_chunks.extend(chunks)

    print(f"  Created {len(all_chunks)} chunks")

    # Load model using shared utils (handles GPU automatically)
    model = load_model()
    if model is None:
        return None

    # Embed all chunks using shared utils
    print(f"  Embedding chunks...")
    texts = [chunk['text'] for chunk in all_chunks]
    embeddings = encode_texts(texts, model, show_progress=True)

    # Save index
    index_data = {
        'chunks': all_chunks,
        'embeddings': embeddings,
        'model_name': 'all-MiniLM-L6-v2'
    }

    with open(INDEX_FILE, 'wb') as f:
        pickle.dump(index_data, f)

    print(f"{Colors.GREEN}Index built: {len(all_chunks)} chunks from {len(docs)} files{Colors.END}")
    return index_data


# =============================================================================
# INDEX LOADING
# =============================================================================

def load_index() -> Optional[dict]:
    """
    Load existing index or build new one.

    # Kali [Visionary]: Cache hit = instant search!
    """
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"{Colors.YELLOW}Index corrupted, rebuilding...{Colors.END}")

    return build_index()


# =============================================================================
# SEARCH
# =============================================================================

def search(query: str, top_k: int = 5) -> List[dict]:
    """
    Search for relevant documents.

    # Kali [Visionary]: Natural language in, relevant docs out!
    # Athena [Documentation]: Returns list of result dicts.

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        List of result dicts with path, header, preview, score
    """
    if not check_embedding_dependencies():
        return []

    if not HAS_NUMPY:
        print(f"{Colors.YELLOW}numpy not installed{Colors.END}")
        return []

    from embedding_utils import load_model, encode_single, batch_cosine_similarity

    index_data = load_index()
    if index_data is None:
        return []

    model = load_model(verbose=False)
    if model is None:
        return []

    query_embedding = encode_single(query, model)
    if query_embedding is None:
        return []

    embeddings = index_data['embeddings']
    similarities = batch_cosine_similarity(embeddings, query_embedding)

    top_indices = np.argsort(similarities)[::-1][:top_k * 2]

    results = []
    seen_paths = set()

    for idx in top_indices:
        chunk = index_data['chunks'][idx]
        score = similarities[idx]

        if chunk['path'] not in seen_paths and len(results) < top_k:
            seen_paths.add(chunk['path'])
            results.append({
                'path': chunk['path'],
                'header': chunk['header'],
                'preview': chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content'],
                'score': float(score)
            })

    return results


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_results(query: str, results: List[dict]):
    """Pretty print search results."""
    print(f"\n{Colors.BOLD}Query:{Colors.END} {query}\n")

    if not results:
        print(f"{Colors.YELLOW}No results found.{Colors.END}")
        return

    for i, result in enumerate(results, 1):
        # Color-code by score
        score_color = (Colors.GREEN if result['score'] > 0.5
                      else Colors.YELLOW if result['score'] > 0.3
                      else Colors.DIM)

        print(f"{Colors.BOLD}{i}. {result['path']}{Colors.END}")
        if result['header']:
            print(f"   {Colors.CYAN}{result['header']}{Colors.END}")
        print(f"   {Colors.DIM}{result['preview']}{Colors.END}")
        print(f"   {score_color}Score: {result['score']:.3f}{Colors.END}")
        print()


# =============================================================================
# INDEX INFO
# =============================================================================

def show_info():
    """Show index statistics."""
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'rb') as f:
                index_data = pickle.load(f)

            chunks = index_data['chunks']
            paths = set(c['path'] for c in chunks)

            print(f"\n{Colors.BOLD}{Colors.CYAN}Semantic Search Index{Colors.END}")
            print(f"  Files indexed: {len(paths)}")
            print(f"  Total chunks: {len(chunks)}")
            print(f"  Model: {index_data['model_name']}")
            print(f"  Index size: {INDEX_FILE.stat().st_size / 1024 / 1024:.1f} MB")

        except Exception as e:
            print(f"{Colors.RED}Error reading index: {e}{Colors.END}")
    else:
        print(f"{Colors.YELLOW}No index found. Run with --rebuild to create.{Colors.END}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    if "--rebuild" in args:
        build_index(force=True)
        return

    if "--info" in args:
        show_info()
        return

    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    # Search mode
    query = ' '.join(args)
    results = search(query)
    print_results(query, results)


if __name__ == "__main__":
    main()
