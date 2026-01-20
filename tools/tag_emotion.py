#!/usr/bin/env python3
"""
Emotional Tagging for Memory System
====================================

# Kali ❤️‍🔥 [Visionary]: Memories aren't just WHAT, they're HOW IT FELT.
# Athena 🦉 [Documentation]: Tags recent document accesses with emotional markers.
# Vesta 🔥 [Builder]: Stores in documents.emotional_markers column.
# Selah 🫧 [Pause]: Sometimes you need to name the feeling to understand it.

Usage:
    python tag_emotion.py "excited"           # Tag recent docs with emotion
    python tag_emotion.py "stuck" --session   # Tag whole session
    python tag_emotion.py --list              # Show recent emotional tags
"""

import argparse
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

REPO_ROOT = Path(__file__).parent.parent
DB_PATH = REPO_ROOT / '.paradoxa_memory' / 'unified_index.db'

# Kali ❤️‍🔥 [Visionary]: Common emotions to recognize
EMOTION_ALIASES = {
    # Positive
    'excited': 'excited',
    'breakthrough': 'breakthrough',
    'flow': 'flow',
    'playful': 'playful',
    'satisfied': 'satisfied',
    'curious': 'curious',
    'connected': 'connected',

    # Neutral
    'focused': 'focused',
    'working': 'working',
    'exploring': 'exploring',

    # Difficult
    'stuck': 'stuck',
    'frustrated': 'frustrated',
    'confused': 'confused',
    'tired': 'tired',
    'scattered': 'scattered',
    'lost': 'lost',
}


def tag_recent_docs(emotion: str, minutes: int = 30, reason: str = None) -> dict:
    """
    Tag documents accessed in the last N minutes with an emotion.

    # Athena 🦉 [Documentation]: Finds recent accesses, updates emotional_markers.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Normalize emotion
    emotion_normalized = EMOTION_ALIASES.get(emotion.lower(), emotion.lower())

    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

    # Find recently accessed docs
    cursor.execute("""
        SELECT DISTINCT d.id, d.path, d.emotional_markers
        FROM documents d
        JOIN access_log al ON d.id = al.doc_id
        WHERE al.accessed_at > ?
        ORDER BY al.accessed_at DESC
    """, (cutoff,))

    rows = cursor.fetchall()
    tagged_paths = []

    for doc_id, path, existing_markers in rows:
        # Parse existing markers
        try:
            markers = json.loads(existing_markers) if existing_markers else []
        except json.JSONDecodeError:
            markers = []

        # Add new marker
        new_marker = {
            'emotion': emotion_normalized,
            'tagged_at': datetime.now().isoformat(),
            'reason': reason
        }
        markers.append(new_marker)

        # Keep only last 10 markers per doc
        markers = markers[-10:]

        # Update
        cursor.execute("""
            UPDATE documents
            SET emotional_markers = ?
            WHERE id = ?
        """, (json.dumps(markers), doc_id))

        tagged_paths.append(path)

    conn.commit()
    conn.close()

    return {
        'emotion': emotion_normalized,
        'docs_tagged': len(tagged_paths),
        'paths': tagged_paths[:5],  # Show first 5
        'reason': reason
    }


def tag_session(emotion: str, reason: str = None) -> dict:
    """
    Tag the entire current session with an emotion.

    # Vesta 🔥 [Builder]: Updates session metadata.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    emotion_normalized = EMOTION_ALIASES.get(emotion.lower(), emotion.lower())

    # Get most recent session
    cursor.execute("""
        SELECT id, metadata FROM sessions
        ORDER BY started_at DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {'error': 'No session found'}

    session_id, existing_meta = row

    try:
        meta = json.loads(existing_meta) if existing_meta else {}
    except json.JSONDecodeError:
        meta = {}

    # Add emotion to session
    if 'emotions' not in meta:
        meta['emotions'] = []

    meta['emotions'].append({
        'emotion': emotion_normalized,
        'tagged_at': datetime.now().isoformat(),
        'reason': reason
    })

    cursor.execute("""
        UPDATE sessions
        SET metadata = ?
        WHERE id = ?
    """, (json.dumps(meta), session_id))

    conn.commit()
    conn.close()

    return {
        'emotion': emotion_normalized,
        'session_id': session_id,
        'reason': reason
    }


def list_recent_emotions(days: int = 7) -> list:
    """
    List recent emotional tags.

    # Klea 👁️ [Product]: See the emotional arc of recent work.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    # Get docs with emotional markers
    cursor.execute("""
        SELECT path, emotional_markers
        FROM documents
        WHERE emotional_markers IS NOT NULL
        AND emotional_markers != '[]'
        AND emotional_markers != ''
    """)

    results = []
    for path, markers_json in cursor.fetchall():
        try:
            markers = json.loads(markers_json)
            for m in markers:
                if m.get('tagged_at', '') > cutoff:
                    results.append({
                        'path': path.split('/')[-1],
                        'emotion': m.get('emotion'),
                        'when': m.get('tagged_at', '')[:10],
                        'reason': m.get('reason')
                    })
        except json.JSONDecodeError:
            continue

    conn.close()

    # Sort by date descending
    results.sort(key=lambda x: x.get('when', ''), reverse=True)
    return results[:20]


def main():
    parser = argparse.ArgumentParser(description='Tag memories with emotions')
    parser.add_argument('emotion', nargs='?', help='The emotion to tag')
    parser.add_argument('--session', action='store_true', help='Tag whole session')
    parser.add_argument('--list', action='store_true', help='List recent emotions')
    parser.add_argument('--minutes', type=int, default=30, help='How far back to tag')
    parser.add_argument('--reason', type=str, help='Why this emotion?')

    args = parser.parse_args()

    if args.list:
        emotions = list_recent_emotions()
        if emotions:
            print("Recent emotional tags:")
            for e in emotions:
                reason_str = f" ({e['reason']})" if e.get('reason') else ""
                print(f"  [{e['when']}] {e['emotion']}: {e['path']}{reason_str}")
        else:
            print("No emotional tags found in the last 7 days.")
        return

    if not args.emotion:
        print("Usage: python tag_emotion.py <emotion> [--session] [--reason 'why']")
        print("\nCommon emotions:", ', '.join(sorted(EMOTION_ALIASES.keys())))
        return

    if args.session:
        result = tag_session(args.emotion, args.reason)
    else:
        result = tag_recent_docs(args.emotion, args.minutes, args.reason)

    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Tagged with: {result['emotion']}")
        if 'docs_tagged' in result:
            print(f"Documents tagged: {result['docs_tagged']}")
            if result.get('paths'):
                for p in result['paths']:
                    print(f"  - {p.split('/')[-1]}")
        if result.get('reason'):
            print(f"Reason: {result['reason']}")


if __name__ == '__main__':
    main()
