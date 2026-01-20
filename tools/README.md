# Tools

*Scripts and utilities for the Relation-ship.*

## Quickstart: Setting Up the Memory System

The memory infrastructure needs to be initialized before use. Here's the minimal setup:

```bash
# 1. Install dependencies
pip install sentence-transformers torch numpy fastapi uvicorn

# 2. Start the semantic server (runs in background, provides embeddings)
python tools/semantic_server.py &

# 3. Initialize the unified index (creates the database)
python tools/unified_index.py --init

# 4. Index your documents
python tools/unified_index.py --scan

# 5. Verify everything works
python tools/ship_doctor.py --verbose
```

The memory system uses SQLite (`.paradoxa_memory/unified_index.db`) for storage and FAISS for vector similarity. No external services required.

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

## Memory Infrastructure

These tools implement the core memory system with decay, consolidation, and associative recall.

### unified_index.py

The central memory system. Manages documents, embeddings, access tracking, and decay scoring.

```bash
python tools/unified_index.py --init          # Initialize database
python tools/unified_index.py --scan          # Scan and index documents
python tools/unified_index.py --search "query"  # Semantic search
python tools/unified_index.py --stats         # Show memory statistics
python tools/unified_index.py --decay         # Run decay calculations
```

Features:
- SQLite-backed document storage with full-text search
- FAISS vector index for semantic similarity
- Access tracking (what you touch becomes memorable)
- Ebbinghaus-inspired decay curves
- Session management

### decay_scoring.py

Implements forgetting curves based on cognitive science.

```bash
python tools/decay_scoring.py --report        # Show decay status
python tools/decay_scoring.py --update        # Recalculate all scores
```

Key concepts:
- **Activity-day decay**: Decay happens on days you work, not calendar days
- **Access reinforcement**: Touching a memory strengthens it
- **Importance weighting**: Some things matter more than others

### semantic_server.py

FastAPI server providing embedding generation for other tools.

```bash
python tools/semantic_server.py               # Start server (default port 8765)
python tools/semantic_server.py --port 9000   # Custom port
```

Endpoints:
- `POST /embed` - Generate embeddings for text
- `GET /health` - Server health check
- `GET /stats` - Usage statistics

### relationship_memory.py

Associative recall via spreading activation. Finds related memories through graph traversal.

```bash
python tools/relationship_memory.py "query"   # Find related memories
python tools/relationship_memory.py --build   # Rebuild relationship index
```

Implements spreading activation from Collins & Loftus (1975).

### ship_doctor.py

Self-diagnostic tool. Finds problems and can auto-fix some of them.

```bash
python tools/ship_doctor.py                   # Dry run - show issues
python tools/ship_doctor.py --fix             # Apply auto-fixes
python tools/ship_doctor.py --create-issues   # Create GitHub issues for manual fixes
python tools/ship_doctor.py --verbose         # Detailed output
```

Checks:
- Stale index entries
- Orphaned files
- Git status
- Memory system health
- Structure consistency

### suggest_connections.py

Turns recognition gaps into actionable suggestions.

```bash
python tools/suggest_connections.py           # Generate suggestions
python tools/suggest_connections.py --top 20  # Top N suggestions
python tools/suggest_connections.py --threshold 0.4  # Min gap score
```

Reads recognition engine output and generates markdown with specific frontmatter templates for missing connections.

### buffer_digest.py

Processes session buffers into structured summaries.

```bash
python tools/buffer_digest.py                 # Digest current buffer
python tools/buffer_digest.py --session ID    # Digest specific session
```

### tag_emotion.py

Emotional markers for memories. Because memories aren't just WHAT, they're HOW IT FELT.

```bash
python tools/tag_emotion.py "excited"         # Tag recent docs
python tools/tag_emotion.py "stuck" --session # Tag whole session
python tools/tag_emotion.py --list            # Show recent tags
```

Common emotions: excited, breakthrough, flow, playful, satisfied, curious, connected, focused, working, exploring, stuck, frustrated, confused, tired, scattered, lost

### polyphony.py

The voice/facet system for polyphonic cognition.

```bash
python tools/polyphony.py --voices            # List available voices
python tools/polyphony.py --analyze FILE      # Analyze polyphonic content
```

Supports multiple cognitive voices (Kali, Athena, Vesta, Nemesis, Klea, Selah) for richer reasoning.

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
.paradoxa_memory/         # Core memory database (unified_index.db)
.semantic_index/          # Semantic search embeddings
.self_recognition_index/  # Self-recognition embeddings
.memory_consolidation/    # Consolidated memories
.memory_index/           # General memory index
.relationship_index/     # Relationship memory index
```

The `.paradoxa_memory/` directory is the most important - it contains the SQLite database that stores all document metadata, access history, decay scores, and session information.
