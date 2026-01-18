#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-Recognition - The Ship Seeing Itself
==========================================

# Kali [Visionary]: We built a recognition engine to find gaps and bridges
#     in external knowledge. What happens when we turn it INWARD?
#     The ship learning to recognize itself. Meta-recognition.
#
# Athena [Reviewer]: This tool analyzes the ENTIRE repo:
#     1. Embeds all markdown files using GPU
#     2. Finds semantic gaps (should connect, doesn't)
#     3. Finds bridges (unexpected connections)
#     4. Analyzes facet divergence (are voices distinct?)
#
# Vesta [Architect]: GPU-intensive. Uses sentence-transformers.
#     Creates a self-recognition index for the ship structure.
#
# Nemesis [Ethics]: This is the thesis made recursive. What recognition
#     failures exist in OUR structure? What are we not seeing?
#
# Klea [Product]: ...a ship that can see itself is a ship that can grow.

Attribution:
    MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
    Original Paradoxa implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)

Usage:
    python tools/self_recognition.py             # Full self-analysis
    python tools/self_recognition.py --build     # Build/rebuild index
    python tools/self_recognition.py --gaps      # Show internal gaps
    python tools/self_recognition.py --bridges   # Show unexpected bridges
    python tools/self_recognition.py --facets    # Facet divergence analysis
    python tools/self_recognition.py --clusters  # Show semantic clusters
"""

import sys
import pickle
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Optional
from dataclasses import dataclass

# Handle imports
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    REPO_ROOT,
    SHIP_DIR,
    CLAUDE_DIR,
    LEGACY_SELF_RECOGNITION_INDEX,
    check_embedding_dependencies,
    print_section,
)

# Optional numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

# =============================================================================
# CONFIGURATION
# =============================================================================

INDEX_DIR = LEGACY_SELF_RECOGNITION_INDEX
INDEX_FILE = INDEX_DIR / "ship_embeddings.pkl"

# Directories to analyze
SHIP_DIRS = [
    SHIP_DIR,
    CLAUDE_DIR,
    REPO_ROOT / "docs",
]

# Exclude patterns
EXCLUDE_PATTERNS = ['.obsidian', 'node_modules', '__pycache__', '.git']


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SemanticGap:
    """A gap in self-recognition: things that should connect but don't."""
    source: str
    target: str
    similarity: float
    gap_reason: str


@dataclass
class SemanticBridge:
    """An unexpected bridge: distant things that ARE connected."""
    source: str
    target: str
    similarity: float
    bridge_type: str


# =============================================================================
# DOCUMENT LOADING
# =============================================================================

def get_all_ship_documents() -> List[Dict]:
    """Load all documents from the ship for analysis."""
    docs = []

    for base_dir in SHIP_DIRS:
        if not base_dir.exists():
            continue

        for md_file in base_dir.rglob("*.md"):
            if any(p in str(md_file) for p in EXCLUDE_PATTERNS):
                continue

            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if len(content.strip()) < 50:
                    continue

                try:
                    rel_path = md_file.relative_to(REPO_ROOT)
                except ValueError:
                    rel_path = md_file

                # Detect section
                section = "unknown"
                path_str = str(rel_path).lower()
                if "bridge" in path_str:
                    section = "BRIDGE"
                elif "engine_room" in path_str:
                    section = "ENGINE_ROOM"
                elif "memory_banks" in path_str:
                    section = "MEMORY_BANKS"
                elif "library" in path_str:
                    section = "LIBRARY"
                elif "observatory" in path_str:
                    section = "OBSERVATORY"
                elif "holodeck" in path_str:
                    section = "HOLODECK"
                elif "crew_quarters" in path_str:
                    section = "CREW_QUARTERS"
                elif "cargo_hold" in path_str:
                    section = "CARGO_HOLD"
                elif "workshop" in path_str:
                    section = "WORKSHOP"
                elif ".claude" in path_str:
                    section = "CONFIG"

                # Detect facet
                facet = "unknown"
                content_lower = content.lower()
                if "kali" in content_lower:
                    facet = "Kali"
                elif "athena" in content_lower:
                    facet = "Athena"
                elif "vesta" in content_lower:
                    facet = "Vesta"
                elif "nemesis" in content_lower:
                    facet = "Nemesis"
                elif "klea" in content_lower:
                    facet = "Klea"

                docs.append({
                    'path': str(rel_path),
                    'content': content[:5000],
                    'section': section,
                    'facet': facet,
                    'filename': md_file.stem,
                })

            except Exception:
                continue

    return docs


# =============================================================================
# EMBEDDING AND INDEXING
# =============================================================================

def build_self_index(force: bool = False) -> Optional[Dict]:
    """Build embedding index of the entire ship."""
    if not check_embedding_dependencies():
        return None

    from embedding_utils import load_model, encode_texts, DEFAULT_EMBEDDING_MODEL

    INDEX_DIR.mkdir(exist_ok=True)

    if INDEX_FILE.exists() and not force:
        try:
            with open(INDEX_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass

    print(f"{Colors.CYAN}Building self-recognition index...{Colors.END}")

    docs = get_all_ship_documents()
    print(f"  Found {len(docs)} documents")

    sections = Counter(d['section'] for d in docs)
    for sec, count in sections.most_common():
        print(f"    {sec}: {count}")

    model = load_model()
    if model is None:
        return None

    print(f"  Embedding ship documents...")
    texts = [d['content'] for d in docs]
    embeddings = encode_texts(texts, model, show_progress=True)
    if embeddings is None:
        return None

    index_data = {
        'docs': docs,
        'embeddings': embeddings,
        'model_name': DEFAULT_EMBEDDING_MODEL,
        'built_at': datetime.now().isoformat(),
    }

    with open(INDEX_FILE, 'wb') as f:
        pickle.dump(index_data, f)

    print(f"{Colors.GREEN}Self-recognition index built: {len(docs)} documents{Colors.END}")
    return index_data


def load_index() -> Optional[Dict]:
    """Load existing index."""
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return build_self_index()


# =============================================================================
# GAP AND BRIDGE DETECTION
# =============================================================================

def find_internal_gaps(index_data: Dict, threshold: float = 0.7) -> List[SemanticGap]:
    """Find semantic gaps within the ship."""
    from embedding_utils import cosine_similarity

    docs = index_data['docs']
    embeddings = index_data['embeddings']
    n = len(docs)

    gaps = []

    for i in range(n):
        for j in range(i + 1, n):
            if docs[i]['section'] == docs[j]['section']:
                continue

            sim = cosine_similarity(embeddings[i], embeddings[j])

            if sim > threshold:
                gap = SemanticGap(
                    source=docs[i]['path'],
                    target=docs[j]['path'],
                    similarity=round(sim, 3),
                    gap_reason=f"{docs[i]['section']} <-> {docs[j]['section']}"
                )
                gaps.append(gap)

    gaps.sort(key=lambda x: x.similarity, reverse=True)
    return gaps[:20]


def find_internal_bridges(index_data: Dict, threshold: float = 0.4) -> List[SemanticBridge]:
    """Find surprising bridges within the ship."""
    from embedding_utils import cosine_similarity

    docs = index_data['docs']
    embeddings = index_data['embeddings']
    n = len(docs)

    bridges = []

    for i in range(n):
        for j in range(i + 1, n):
            if docs[i]['section'] != docs[j]['section']:
                continue

            sim = cosine_similarity(embeddings[i], embeddings[j])

            if sim < threshold:
                bridge = SemanticBridge(
                    source=docs[i]['path'],
                    target=docs[j]['path'],
                    similarity=round(sim, 3),
                    bridge_type=docs[i]['section']
                )
                bridges.append(bridge)

    bridges.sort(key=lambda x: x.similarity)
    return bridges[:20]


# =============================================================================
# FACET DIVERGENCE ANALYSIS
# =============================================================================

def analyze_facet_divergence(index_data: Dict) -> Dict:
    """Analyze how different facets' outputs are from each other."""
    from embedding_utils import compute_centroid, cosine_similarity

    if not HAS_NUMPY:
        return {'error': 'numpy not installed'}

    docs = index_data['docs']
    embeddings = index_data['embeddings']

    facet_docs = defaultdict(list)
    facet_embeddings = defaultdict(list)

    for i, doc in enumerate(docs):
        facet = doc['facet']
        if facet != 'unknown':
            facet_docs[facet].append(doc)
            facet_embeddings[facet].append(embeddings[i])

    centroids = {}
    for facet, embs in facet_embeddings.items():
        if embs:
            centroids[facet] = compute_centroid(np.array(embs))

    distances = {}
    facets = list(centroids.keys())
    for i, f1 in enumerate(facets):
        for f2 in facets[i+1:]:
            sim = cosine_similarity(centroids[f1], centroids[f2])
            distances[f"{f1}-{f2}"] = round(sim, 3)

    counts = {f: len(docs) for f, docs in facet_docs.items()}

    return {
        'counts': counts,
        'distances': distances,
        'most_similar': max(distances.items(), key=lambda x: x[1]) if distances else None,
        'most_different': min(distances.items(), key=lambda x: x[1]) if distances else None,
    }


# =============================================================================
# SECTION ANALYSIS
# =============================================================================

def analyze_sections(index_data: Dict) -> Dict:
    """Analyze semantic cohesion of each ship section."""
    from embedding_utils import cosine_similarity

    if not HAS_NUMPY:
        return {'error': 'numpy not installed'}

    docs = index_data['docs']
    embeddings = index_data['embeddings']

    section_embeddings = defaultdict(list)
    for i, doc in enumerate(docs):
        section_embeddings[doc['section']].append(embeddings[i])

    cohesion = {}
    for section, embs in section_embeddings.items():
        if len(embs) < 2:
            cohesion[section] = {'count': len(embs), 'cohesion': 1.0}
            continue

        sims = []
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                sim = cosine_similarity(embs[i], embs[j])
                sims.append(sim)

        cohesion[section] = {
            'count': len(embs),
            'cohesion': round(np.mean(sims), 3) if sims else 1.0
        }

    return cohesion


# =============================================================================
# CLUSTER ANALYSIS
# =============================================================================

def find_semantic_clusters(index_data: Dict, n_clusters: int = 5) -> Dict:
    """Find semantic clusters in the ship's documents."""
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        return {'error': 'sklearn not installed'}

    if not HAS_NUMPY:
        return {'error': 'numpy not installed'}

    docs = index_data['docs']
    embeddings = index_data['embeddings']

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append(docs[i])

    summaries = {}
    for label, docs_in_cluster in clusters.items():
        sections = Counter(d['section'] for d in docs_in_cluster)
        summaries[f"cluster_{label}"] = {
            'size': len(docs_in_cluster),
            'dominant_section': sections.most_common(1)[0][0] if sections else 'unknown',
            'sections': dict(sections),
            'sample_files': [d['filename'] for d in docs_in_cluster[:5]],
        }

    return summaries


# =============================================================================
# OUTPUT
# =============================================================================

def print_full_analysis():
    """Print full self-recognition analysis."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("   SELF-RECOGNITION - The Ship Seeing Itself")
    print("=" * 60)
    print(Colors.END)

    index = load_index()
    if not index:
        print(f"{Colors.RED}Failed to load index{Colors.END}")
        return

    print_section("Section Cohesion", "")
    cohesion = analyze_sections(index)
    if 'error' not in cohesion:
        for section, data in sorted(cohesion.items(), key=lambda x: -x[1]['cohesion']):
            bar_len = int(data['cohesion'] * 20)
            bar = "#" * bar_len
            print(f"  {section:15} {bar} {data['cohesion']:.2f} ({data['count']} docs)")

    print_section("Facet Divergence", "")
    facets = analyze_facet_divergence(index)
    if 'error' not in facets:
        print(f"  Documents by facet: {facets['counts']}")
        if facets['distances']:
            print(f"\n  Similarity between facets:")
            for pair, sim in sorted(facets['distances'].items(), key=lambda x: -x[1]):
                print(f"    {pair}: {sim}")
        if facets['most_similar']:
            print(f"\n  {Colors.YELLOW}Most similar: {facets['most_similar'][0]} ({facets['most_similar'][1]}){Colors.END}")
        if facets['most_different']:
            print(f"  {Colors.GREEN}Most different: {facets['most_different'][0]} ({facets['most_different'][1]}){Colors.END}")

    print_section("Internal Gaps", "")
    gaps = find_internal_gaps(index)
    if gaps:
        print(f"  {Colors.YELLOW}High-similarity pairs across sections (should they connect?){Colors.END}")
        for gap in gaps[:7]:
            print(f"\n    {gap.source[:40]}")
            print(f"    <-> {gap.target[:40]}")
            print(f"    Similarity: {gap.similarity} | Sections: {gap.gap_reason}")
    else:
        print(f"  {Colors.GREEN}No significant gaps detected{Colors.END}")

    print_section("Internal Bridges", "")
    bridges = find_internal_bridges(index)
    if bridges:
        print(f"  {Colors.GREEN}Low-similarity pairs within sections (unexpected diversity){Colors.END}")
        for bridge in bridges[:5]:
            print(f"\n    {bridge.source[:40]}")
            print(f"    <-> {bridge.target[:40]}")
            print(f"    Similarity: {bridge.similarity} | Section: {bridge.bridge_type}")
    else:
        print(f"  {Colors.DIM}No significant bridges{Colors.END}")

    print_section("Semantic Clusters", "")
    clusters = find_semantic_clusters(index)
    if 'error' not in clusters:
        for name, data in sorted(clusters.items(), key=lambda x: -x[1]['size']):
            print(f"\n  {Colors.BOLD}{name}{Colors.END} ({data['size']} docs)")
            print(f"    Dominant: {data['dominant_section']}")
            print(f"    Samples: {', '.join(data['sample_files'][:3])}")

    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"  The ship sees itself.")


def main():
    args = set(sys.argv[1:])

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    if '--build' in args:
        build_self_index(force=True)
        return

    if '--gaps' in args:
        index = load_index()
        if index:
            gaps = find_internal_gaps(index)
            for gap in gaps:
                print(f"{gap.source} <-> {gap.target} ({gap.similarity})")
        return

    if '--bridges' in args:
        index = load_index()
        if index:
            bridges = find_internal_bridges(index)
            for bridge in bridges:
                print(f"{bridge.source} <-> {bridge.target} ({bridge.similarity})")
        return

    if '--facets' in args:
        index = load_index()
        if index:
            print(json.dumps(analyze_facet_divergence(index), indent=2))
        return

    if '--clusters' in args:
        index = load_index()
        if index:
            print(json.dumps(find_semantic_clusters(index), indent=2))
        return

    print_full_analysis()


if __name__ == "__main__":
    main()
