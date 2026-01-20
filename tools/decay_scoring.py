#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Importance Scoring
=========================

# Kali ❤️‍🔥 [Visionary]: Not everything should persist forever with equal weight.
#     Important memories stay vivid. Unused ones fade. This is how memory works.
#
# Athena 🦉 [Reviewer]: Based on cognitive science research, not arbitrary formulas.
#     See ACKNOWLEDGMENTS.md for full citations.
#
# Vesta 🔥 [Architect]: Activity-day decay, not calendar-day. If you don't
#     use the repo for a week, memories don't rot during that time.
#
# Nemesis 💀 [Security]: Pure computation, no side effects beyond scoring.
#
# Klea 👁️ [Product]: ...fading is not forgetting. it's prioritizing.

Cognitive Science Foundations:
    - Ebbinghaus (1885): Forgetting follows exponential decay
    - Anderson & Schooler (1991): Memory reflects environmental statistics
    - Bjork (1994): Retrieval strengthens memory (testing effect)
    - Collins & Loftus (1975): Spreading activation in semantic networks

Inspiration:
    Memory architecture inspired by MIRA-OSS (Taylor Satula).
    Implementation is clean-room based on cognitive science principles.
    See ACKNOWLEDGMENTS.md for full attribution.

Our Formula:
    importance = (access_value + centrality_value) * recency_factor * stability_bonus

    Where:
    - access_value: log(1 + access_count) - diminishing returns on repeated access
    - centrality_value: sqrt(incoming_links) * 0.2 - hub documents matter more
    - recency_factor: 2^(-activity_days / half_life) - exponential forgetting curve
    - stability_bonus: 1 + (retrieval_strength * 0.1) - retrieval strengthens memory

Usage:
    from decay_scoring import MemoryScorer

    scorer = MemoryScorer()
    score = scorer.calculate_importance(doc_id)
    active_docs = scorer.get_active_memories(threshold=0.3)

"""

import sys
import math
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Kali ❤️‍🔥 [Visionary]: Handle imports whether run as module or script
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    PARADOXA_MEMORY_DIR,
    print_section,
    print_ok,
    print_warning,
)

from unified_index import UnifiedIndex, DB_FILE


# =============================================================================
# CONFIGURATION
# =============================================================================
# Athena 🦉 [Reviewer]: Parameters derived from cognitive science literature

# Ebbinghaus forgetting curve: R = 2^(-t/S) where S is stability
# Half-life of 14 activity days means memory drops to 50% importance after 2 weeks of no access
HALF_LIFE_ACTIVITY_DAYS = 14

# New documents get a grace period before decay kicks in
# Anderson & Schooler: Recent items have recency advantage
NEWNESS_GRACE_PERIOD_DAYS = 7

# Retrieval strengthens memory (Bjork's desirable difficulties)
# Each successful retrieval adds stability
RETRIEVAL_STRENGTHENING_RATE = 0.1

# Maximum stability bonus from retrievals (diminishing returns)
MAX_STABILITY_BONUS = 2.0


@dataclass
class MemoryScore:
    """Score components for a document."""
    doc_id: int
    path: str
    access_value: float      # From access frequency
    centrality_value: float  # From graph position
    recency_factor: float    # Time decay
    stability_bonus: float   # Retrieval strengthening
    total_score: float       # Final importance
    last_accessed: Optional[datetime]
    access_count: int


class MemoryScorer:
    """
    Calculate memory importance scores based on cognitive science principles.

    # Kali ❤️‍🔥 [Visionary]: Memory that works like memory!
    # Athena 🦉 [Documentation]: Combines access patterns, graph structure, and time decay.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_FILE
        self._activity_days = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def _get_activity_days(self, conn: sqlite3.Connection) -> int:
        """
        Count distinct days with activity (not calendar days).

        # Vesta 🔥 [Architect]: If the repo sits idle, time doesn't pass for memory decay.
        """
        if self._activity_days is not None:
            return self._activity_days

        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(accessed_at))
            FROM access_log
        """)
        result = cursor.fetchone()
        self._activity_days = result[0] if result else 0
        return self._activity_days

    def _days_since_access(self, last_accessed: Optional[str], conn: sqlite3.Connection) -> float:
        """
        Calculate activity days since last access.

        # Athena 🦉 [Reviewer]: Activity days, not calendar days.
        """
        if not last_accessed:
            return float('inf')

        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(accessed_at))
            FROM access_log
            WHERE DATE(accessed_at) > DATE(?)
        """, (last_accessed,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def calculate_importance(self, doc_id: int) -> Optional[MemoryScore]:
        """
        Calculate importance score for a document.

        # Kali ❤️‍🔥 [Visionary]: The heart of memory prioritization!
        # Athena 🦉 [Documentation]:
        #     importance = (access_value + centrality_value) * recency_factor * stability_bonus
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get document info
        cursor.execute("""
            SELECT path, access_count, last_accessed, incoming_links
            FROM documents
            WHERE id = ?
        """, (doc_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        path, access_count, last_accessed, incoming_links = row
        access_count = access_count or 0
        incoming_links = incoming_links or 0

        # 1. Access value: log(1 + count) - diminishing returns
        # Kali ❤️‍🔥 [Visionary]: First access matters most, repeated access has diminishing returns
        access_value = math.log(1 + access_count)

        # 2. Centrality value: sqrt(links) * 0.2
        # Athena 🦉 [Reviewer]: Hub documents (many incoming links) are more important
        # Square root to prevent runaway importance from highly-linked docs
        centrality_value = math.sqrt(incoming_links) * 0.2

        # 3. Recency factor: 2^(-days / half_life)
        # Ebbinghaus forgetting curve
        days_since = self._days_since_access(last_accessed, conn)

        if days_since == float('inf'):
            recency_factor = 0.1  # Never accessed = low but not zero
        elif days_since <= NEWNESS_GRACE_PERIOD_DAYS:
            recency_factor = 1.0  # Grace period = no decay
        else:
            effective_days = days_since - NEWNESS_GRACE_PERIOD_DAYS
            recency_factor = math.pow(2, -effective_days / HALF_LIFE_ACTIVITY_DAYS)

        # 4. Stability bonus from retrieval practice
        # Bjork: Each successful retrieval strengthens the memory trace
        retrieval_strength = min(access_count * RETRIEVAL_STRENGTHENING_RATE, MAX_STABILITY_BONUS - 1)
        stability_bonus = 1.0 + retrieval_strength

        # Final score
        base_value = access_value + centrality_value
        total_score = base_value * recency_factor * stability_bonus

        conn.close()

        return MemoryScore(
            doc_id=doc_id,
            path=path,
            access_value=round(access_value, 3),
            centrality_value=round(centrality_value, 3),
            recency_factor=round(recency_factor, 3),
            stability_bonus=round(stability_bonus, 3),
            total_score=round(total_score, 3),
            last_accessed=datetime.fromisoformat(last_accessed) if last_accessed else None,
            access_count=access_count
        )

    def get_active_memories(self, threshold: float = 0.3, limit: int = 100) -> List[MemoryScore]:
        """
        Get memories above importance threshold.

        # Kali ❤️‍🔥 [Visionary]: What's worth remembering right now?
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM documents")
        doc_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        scores = []
        for doc_id in doc_ids:
            score = self.calculate_importance(doc_id)
            if score and score.total_score >= threshold:
                scores.append(score)

        # Sort by importance
        scores.sort(key=lambda x: x.total_score, reverse=True)
        return scores[:limit]

    def get_fading_memories(self, threshold: float = 0.1, limit: int = 50) -> List[MemoryScore]:
        """
        Get memories that are fading but not yet gone.

        # Klea 👁️ [Product]: Candidates for consolidation or archival.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM documents")
        doc_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        scores = []
        for doc_id in doc_ids:
            score = self.calculate_importance(doc_id)
            if score and score.total_score < threshold and score.total_score > 0.01:
                scores.append(score)

        scores.sort(key=lambda x: x.total_score)
        return scores[:limit]


def print_memory_status():
    """Print current memory importance distribution."""
    scorer = MemoryScorer()

    print_section("Memory Importance Status")

    active = scorer.get_active_memories(threshold=0.5, limit=10)
    if active:
        print(f"\n{Colors.GREEN}Active Memories (score >= 0.5):{Colors.END}")
        for m in active:
            print(f"  {m.total_score:.2f} | {m.path}")
            print(f"       access={m.access_value:.2f} central={m.centrality_value:.2f} "
                  f"recency={m.recency_factor:.2f} stability={m.stability_bonus:.2f}")

    fading = scorer.get_fading_memories(threshold=0.2, limit=5)
    if fading:
        print(f"\n{Colors.YELLOW}Fading Memories (score < 0.2):{Colors.END}")
        for m in fading:
            print(f"  {m.total_score:.2f} | {m.path}")

    print_ok("Memory status computed")


if __name__ == "__main__":
    print_memory_status()
