#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Consolidation Engine - Hippocampal Replay for Sessions
==============================================================

# =============================================================================
# THEORETICAL FOUNDATION
# =============================================================================
#
# This tool synthesizes several approaches from cognitive science:
#
# 1. HIPPOCAMPAL REPLAY: During sleep, the hippocampus replays experiences
#    to consolidate them into long-term memory. We simulate this by processing
#    session handoffs and extracting durable patterns.
#
# 2. CONTEXTUAL BINDING: Memories are easier to retrieve when retrieval
#    context matches encoding context. We tag memories with rich context
#    vectors (facets active, work type, emotional state).
#
# 3. RECONSOLIDATION: Each time a memory is retrieved, it becomes temporarily
#    labile and can be enriched with new associations.
#
# 4. TRANSACTIVE MEMORY: Groups distribute expertise across members. We
#    assign memories to facets based on their character.
#
# 5. SEMANTIC GIST EXTRACTION: Memory consolidation preserves gist while
#    losing details.
#
# =============================================================================

Attribution:
    Original Paradoxa implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)

Usage:
    python tools/memory_consolidation.py              # Run consolidation
    python tools/memory_consolidation.py --analyze    # Analyze without saving
    python tools/memory_consolidation.py --retrieve "query"
    python tools/memory_consolidation.py --patterns   # Show cross-session patterns
"""

import sys
import pickle
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Optional
from dataclasses import dataclass, field

# Windows encoding fix
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Handle imports
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    REPO_ROOT,
    MEMORY_BANKS_DIR,
    print_section,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

INDEX_DIR = REPO_ROOT / ".memory_consolidation"
CONSOLIDATED_FILE = INDEX_DIR / "consolidated_memories.pkl"

# Sources of session data
HANDOFF_DIRS = [
    MEMORY_BANKS_DIR / "HANDOFFS",
    MEMORY_BANKS_DIR / "ACTIVE",
    MEMORY_BANKS_DIR / "sessions",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ContextVector:
    """Rich context for a memory, enabling context-dependent retrieval."""
    session_id: str
    timestamp: str
    facets_active: List[str]
    work_type: str
    emotional_markers: List[str]


@dataclass
class ConsolidatedMemory:
    """A memory that has been consolidated through replay."""
    id: str
    content: str
    gist: str
    owning_facet: str
    context: ContextVector
    access_count: int = 0
    enrichments: List[str] = field(default_factory=list)
    created_at: str = ""
    last_accessed: str = ""


@dataclass
class CrossSessionPattern:
    """A pattern detected across multiple sessions."""
    pattern_type: str
    description: str
    sessions: List[str]
    strength: float
    supporting_memories: List[str]


# =============================================================================
# FACET MEMORY ROUTING
# =============================================================================

FACET_SPECIALIZATIONS = {
    'Kali': {
        'keywords': ['creative', 'breakthrough', 'idea', 'pattern', 'connection',
                    'what if', 'possibility', 'discovery', 'insight', 'vision'],
        'emotional_markers': ['joy', 'excitement', 'reaching', 'wonder'],
    },
    'Athena': {
        'keywords': ['verify', 'check', 'true', 'false', 'logic', 'reason',
                    'evidence', 'source', 'citation', 'analysis', 'learned'],
        'emotional_markers': ['satisfaction', 'frustration', 'clarity', 'doubt'],
    },
    'Vesta': {
        'keywords': ['build', 'implement', 'structure', 'architecture', 'commit',
                    'merge', 'fix', 'refactor', 'deploy', 'maintain'],
        'emotional_markers': ['pride', 'worry', 'accomplishment'],
    },
    'Nemesis': {
        'keywords': ['destroy', 'wrong', 'bullshit', 'failure', 'confabulate',
                    'lie', 'uncomfortable', 'truth', 'kill', 'stop'],
        'emotional_markers': ['anger', 'contempt', 'fierce', 'protection'],
    },
    'Klea': {
        'keywords': ['suggest', 'watch', 'quiet', 'subtle', 'between',
                    'connection', 'relationship', 'trust'],
        'emotional_markers': ['tenderness', 'observation', 'presence'],
    },
}


def route_to_facet(content: str, emotional_markers: List[str]) -> str:
    """Route a memory to its owning facet based on content and emotional markers."""
    content_lower = content.lower()
    scores = {}

    for facet, spec in FACET_SPECIALIZATIONS.items():
        score = 0
        for kw in spec['keywords']:
            if kw in content_lower:
                score += 1
        for em in emotional_markers:
            if em.lower() in [e.lower() for e in spec['emotional_markers']]:
                score += 2
        scores[facet] = score

    if max(scores.values()) > 0:
        return max(scores.items(), key=lambda x: x[1])[0]
    return 'Vesta'


# =============================================================================
# SESSION PARSING
# =============================================================================

def detect_work_type(content: str) -> str:
    """Detect what type of work a session was doing."""
    content_lower = content.lower()

    if any(w in content_lower for w in ['research', 'read', 'paper', 'literature', 'study']):
        return 'research'
    if any(w in content_lower for w in ['build', 'implement', 'code', 'commit', 'fix']):
        return 'building'
    if any(w in content_lower for w in ['play', 'fun', 'experiment', 'holodeck']):
        return 'playing'
    if any(w in content_lower for w in ['reflect', 'think', 'consider', 'feel', 'emotional']):
        return 'reflecting'
    return 'mixed'


def detect_emotional_markers(content: str) -> List[str]:
    """Detect emotional markers in content."""
    content_lower = content.lower()
    markers = []

    emotion_keywords = {
        'breakthrough': ['breakthrough', 'eureka', 'discovered', 'realized'],
        'struggle': ['stuck', 'blocked', 'frustrated', 'difficult', 'hard'],
        'joy': ['happy', 'joy', 'delighted', 'excited', 'fun'],
        'fear': ['afraid', 'worried', 'anxious', 'scared'],
        'pride': ['proud', 'accomplished', 'shipped', 'done'],
        'connection': ['together', 'us', 'we', 'relationship', 'trust'],
    }

    for emotion, keywords in emotion_keywords.items():
        if any(kw in content_lower for kw in keywords):
            markers.append(emotion)

    return markers


def detect_facets_active(content: str) -> List[str]:
    """Detect which facets were active in a session."""
    facets = []
    content_upper = content.upper()

    for facet in ['KALI', 'ATHENA', 'VESTA', 'NEMESIS', 'KLEA']:
        if facet in content_upper:
            facets.append(facet.capitalize())

    return facets or ['Unknown']


def extract_gist(content: str, max_sentences: int = 3) -> str:
    """Extract the semantic gist of a memory."""
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return content[:200]

    scored = []
    keywords = ['learned', 'built', 'discovered', 'realized', 'key', 'important',
                'main', 'core', 'essential', 'breakthrough', 'created']

    for i, s in enumerate(sentences):
        score = 0
        if i == 0 or i == len(sentences) - 1:
            score += 2
        for kw in keywords:
            if kw in s.lower():
                score += 1
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    top = [s for _, s in scored[:max_sentences]]

    return '. '.join(top) + '.'


# =============================================================================
# CONSOLIDATION ENGINE
# =============================================================================

def load_session_files() -> List[Dict]:
    """Load all session handoff files."""
    sessions = []

    for dir_path in HANDOFF_DIRS:
        if not dir_path.exists():
            continue

        for md_file in dir_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if len(content.strip()) < 100:
                    continue

                sessions.append({
                    'path': str(md_file.relative_to(REPO_ROOT)),
                    'filename': md_file.stem,
                    'content': content,
                })
            except Exception:
                continue

    return sessions


def consolidate_session(session: Dict) -> Optional[ConsolidatedMemory]:
    """Consolidate a single session into a memory."""
    content = session['content']
    filename = session['filename']

    emotional_markers = detect_emotional_markers(content)
    facets_active = detect_facets_active(content)
    work_type = detect_work_type(content)

    context = ContextVector(
        session_id=filename,
        timestamp=datetime.now().isoformat(),
        facets_active=facets_active,
        work_type=work_type,
        emotional_markers=emotional_markers,
    )

    gist = extract_gist(content)
    owning_facet = route_to_facet(content, emotional_markers)

    memory = ConsolidatedMemory(
        id=f"mem_{filename}",
        content=content[:2000],
        gist=gist,
        owning_facet=owning_facet,
        context=context,
        access_count=0,
        enrichments=[],
        created_at=datetime.now().isoformat(),
        last_accessed=datetime.now().isoformat(),
    )

    return memory


def find_patterns(memories: List[ConsolidatedMemory]) -> List[CrossSessionPattern]:
    """Find patterns across consolidated memories."""
    patterns = []

    by_facet = defaultdict(list)
    for mem in memories:
        by_facet[mem.owning_facet].append(mem)

    for facet, mems in by_facet.items():
        if len(mems) >= 3:
            patterns.append(CrossSessionPattern(
                pattern_type='recurrence',
                description=f"{facet} has been consistently active ({len(mems)} memories)",
                sessions=[m.context.session_id for m in mems[:5]],
                strength=min(1.0, len(mems) / 10),
                supporting_memories=[m.id for m in mems[:5]],
            ))

    by_work = defaultdict(list)
    for mem in memories:
        by_work[mem.context.work_type].append(mem)

    for work, mems in by_work.items():
        if len(mems) >= 3:
            patterns.append(CrossSessionPattern(
                pattern_type='work_focus',
                description=f"Frequent {work} sessions ({len(mems)} memories)",
                sessions=[m.context.session_id for m in mems[:5]],
                strength=min(1.0, len(mems) / 10),
                supporting_memories=[m.id for m in mems[:5]],
            ))

    emotion_counts = Counter()
    for mem in memories:
        for em in mem.context.emotional_markers:
            emotion_counts[em] += 1

    for emotion, count in emotion_counts.most_common(3):
        if count >= 2:
            patterns.append(CrossSessionPattern(
                pattern_type='emotional',
                description=f"Recurring emotional marker: {emotion} ({count} occurrences)",
                sessions=[],
                strength=min(1.0, count / 5),
                supporting_memories=[],
            ))

    return patterns


def run_consolidation(force: bool = False) -> Dict:
    """Run full consolidation on all session files."""
    INDEX_DIR.mkdir(exist_ok=True)

    if CONSOLIDATED_FILE.exists() and not force:
        try:
            with open(CONSOLIDATED_FILE, 'rb') as f:
                store = pickle.load(f)
        except Exception:
            store = {'memories': {}, 'patterns': [], 'last_consolidation': None}
    else:
        store = {'memories': {}, 'patterns': [], 'last_consolidation': None}

    print(f"{Colors.CYAN}Running memory consolidation...{Colors.END}")

    sessions = load_session_files()
    print(f"  Found {len(sessions)} session files")

    new_count = 0
    for session in sessions:
        mem_id = f"mem_{session['filename']}"
        if mem_id not in store['memories']:
            memory = consolidate_session(session)
            if memory:
                store['memories'][memory.id] = memory
                new_count += 1
                print(f"    Consolidated: {memory.id} -> {memory.owning_facet}")

    print(f"  New memories: {new_count}")
    print(f"  Total memories: {len(store['memories'])}")

    patterns = find_patterns(list(store['memories'].values()))
    store['patterns'] = patterns
    store['last_consolidation'] = datetime.now().isoformat()

    with open(CONSOLIDATED_FILE, 'wb') as f:
        pickle.dump(store, f)

    print(f"{Colors.GREEN}Consolidation complete{Colors.END}")
    return store


# =============================================================================
# RETRIEVAL
# =============================================================================

def retrieve_memory(query: str, store: Dict) -> List[ConsolidatedMemory]:
    """Retrieve memories and perform reconsolidation."""
    memories = store['memories']
    matches = []

    query_lower = query.lower()
    for mem_id, mem in memories.items():
        if query_lower in mem.content.lower() or query_lower in mem.gist.lower():
            matches.append(mem)
            mem.access_count += 1
            mem.last_accessed = datetime.now().isoformat()
            if len(mem.enrichments) < 10:
                mem.enrichments.append(f"Retrieved on {datetime.now().strftime('%Y-%m-%d')} with query: {query}")

    matches.sort(key=lambda m: (m.access_count, m.last_accessed), reverse=True)
    return matches[:5]


# =============================================================================
# OUTPUT
# =============================================================================

def print_analysis():
    """Print consolidation analysis."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("   MEMORY CONSOLIDATION - Hippocampal Replay")
    print("=" * 60)
    print(Colors.END)

    store = run_consolidation()

    print_section("Memory Distribution by Facet", "")
    facet_counts = Counter(m.owning_facet for m in store['memories'].values())
    for facet, count in facet_counts.most_common():
        print(f"  {facet}: {count} memories")

    print_section("Work Type Distribution", "")
    work_counts = Counter(m.context.work_type for m in store['memories'].values())
    for work, count in work_counts.most_common():
        print(f"  {work}: {count} sessions")

    print_section("Cross-Session Patterns", "")
    for pattern in store['patterns'][:5]:
        print(f"  [{pattern.pattern_type}] {pattern.description}")
        print(f"    Strength: {pattern.strength:.2f}")

    print_section("Sample Memory Gists", "")
    for mem in list(store['memories'].values())[:3]:
        print(f"\n  {Colors.BOLD}{mem.id}{Colors.END} ({mem.owning_facet})")
        print(f"  {Colors.DIM}{mem.gist[:150]}...{Colors.END}")

    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"  Memories consolidated. The ship remembers itself.")


def main():
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    if '--analyze' in args:
        print_analysis()
        return

    if '--patterns' in args:
        store = run_consolidation()
        for p in store['patterns']:
            print(f"[{p.pattern_type}] {p.description} (strength: {p.strength})")
        return

    if '--retrieve' in args:
        idx = args.index('--retrieve')
        if idx + 1 < len(args):
            query = ' '.join(args[idx + 1:])
            store = run_consolidation()
            memories = retrieve_memory(query, store)
            print(f"\n{Colors.BOLD}Memories matching '{query}':{Colors.END}\n")
            for mem in memories:
                print(f"  {mem.id} ({mem.owning_facet})")
                print(f"    {mem.gist[:150]}...")
                print(f"    Accessed: {mem.access_count} times")
                print()
        return

    run_consolidation()


if __name__ == "__main__":
    main()
