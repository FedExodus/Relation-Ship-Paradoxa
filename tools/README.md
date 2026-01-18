# Tools

*Scripts and utilities for the Relation-ship.*

## Installation

Core tools work with standard library only. Advanced tools require optional dependencies:

```bash
pip install -r requirements.txt
```

Or install specific features:

```bash
# Semantic search and embeddings
pip install sentence-transformers torch numpy

# Clustering analysis
pip install scikit-learn
```

## Core Tools

### wakeup.py

The ship's morning routine. Run this when a new instance arrives.

```bash
python tools/wakeup.py
```

Shows computed state: git status, recent commits, open issues, ship log entries.
Not instructions - actual state. The difference matters.

### shared_config.py

Common infrastructure. Import this instead of redefining paths and colors.

```python
from shared_config import Colors, REPO_ROOT, SHIP_DIR
```

### embedding_utils.py

Shared embedding infrastructure for all semantic tools.

```python
from embedding_utils import load_model, encode_texts, cosine_similarity

model = load_model()
embeddings = encode_texts(["hello world"], model)
sim = cosine_similarity(emb1, emb2)
```

Handles GPU detection, model caching, batch encoding.

## Semantic Tools

These require `sentence-transformers`, `torch`, and `numpy`.

### semantic_search.py

Find documents by meaning, not keywords.

```bash
python tools/semantic_search.py "how do we handle disagreement"
python tools/semantic_search.py --rebuild  # Rebuild index
python tools/semantic_search.py --info     # Show index stats
```

Uses all-MiniLM-L6-v2 (384-dimensional vectors). Index cached to `.semantic_index/`.

### self_recognition.py

The ship seeing itself. Semantic analysis of the repo structure.

```bash
python tools/self_recognition.py             # Full analysis
python tools/self_recognition.py --build     # Build/rebuild index
python tools/self_recognition.py --gaps      # Find internal gaps
python tools/self_recognition.py --bridges   # Find unexpected bridges
python tools/self_recognition.py --facets    # Facet divergence
python tools/self_recognition.py --clusters  # Semantic clusters
```

Finds:
- **Gaps**: High similarity across sections (should they connect?)
- **Bridges**: Low similarity within sections (unexpected diversity)
- **Facet divergence**: Are the voices actually distinct?
- **Clusters**: Natural groupings in the content

## Metacognitive Tools

These analyze work patterns and session history.

### momentum.py

Metacognitive analysis of work patterns.

```bash
python tools/momentum.py              # Full report
python tools/momentum.py --issues     # Issue analysis only
python tools/momentum.py --commits    # Commit patterns only
python tools/momentum.py --stuck      # Show potentially stuck work
python tools/momentum.py --brief      # Short summary
```

Tracks:
- Commit velocity and patterns
- Issue freshness (hot/cold/stale)
- Work type distribution
- Potential blind spots

### memory_consolidation.py

Hippocampal replay for session memories.

```bash
python tools/memory_consolidation.py              # Run consolidation
python tools/memory_consolidation.py --analyze    # Analyze patterns
python tools/memory_consolidation.py --retrieve "query"
python tools/memory_consolidation.py --patterns   # Cross-session patterns
```

Implements cognitive science concepts:
- Hippocampal replay (consolidating experiences)
- Contextual binding (rich context vectors)
- Reconsolidation (enriching on retrieval)
- Transactive memory (routing to facets)
- Semantic gist extraction

## Philosophy

These tools exist to help maintain continuity across sessions. Key principles:

1. **Compute, don't assume** - Show actual state, not cached instructions
2. **Local first** - No external API calls for core functionality
3. **Graceful degradation** - Tools work even if dependencies are missing
4. **Polyphonic comments** - Comments show reasoning, not just what

## Attribution

- MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
- Original Paradoxa implementation by Nathan Batty & Paradoxa

## Index Directories

These directories are created automatically and should be gitignored:

```
.semantic_index/          # Semantic search embeddings
.self_recognition_index/  # Self-recognition embeddings
.memory_consolidation/    # Consolidated memories
.memory_index/           # General memory index
.relationship_index/     # Relationship memory index
```
