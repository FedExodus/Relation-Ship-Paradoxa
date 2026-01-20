#!/usr/bin/env python3
"""
Buffer Digest - Process session buffer into durable memory.

# Kali [Visionary]: The missing link! Buffer captures, this digests.
# Athena [Reviewer]: Extracts patterns from raw events, not just archives.
# Vesta [Builder]: Outputs to memory/digest/ where wakeup can find it.
# Nemesis [Security]: No external calls. All local processing.

This is the PROTOTYPE version. See SCALING_NOTES.md for upgrade path.

Usage:
    python tools/buffer_digest.py              # Digest and archive buffer
    python tools/buffer_digest.py --preview    # Show what would be extracted
    python tools/buffer_digest.py --stats      # Just show buffer statistics
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any

# Import from shared config
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    REPO_ROOT,
    MEMORY_BANKS_DIR,
    print_section,
    print_ok,
    print_warning,
)

BUFFER_FILE = MEMORY_BANKS_DIR / "sessions" / "current_buffer.jsonl"
DIGEST_DIR = REPO_ROOT / "memory" / "digest"
ARCHIVE_DIR = MEMORY_BANKS_DIR / "sessions" / "archive"


def load_buffer() -> List[Dict[str, Any]]:
    """Load all events from the session buffer."""
    if not BUFFER_FILE.exists():
        return []

    events = []
    with open(BUFFER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def extract_patterns(events: List[Dict]) -> Dict[str, Any]:
    """
    Extract meaningful patterns from raw events.

    # Kali [Visionary]: Not just counts - what MATTERED?
    # Athena [Reviewer]: Uses importance signals to filter noise.
    """
    if not events:
        return {}

    # Basic stats
    total_events = len(events)

    # Time range
    timestamps = [e.get('timestamp', '') for e in events if e.get('timestamp')]
    if timestamps:
        first_ts = min(timestamps)
        last_ts = max(timestamps)
    else:
        first_ts = last_ts = None

    # Human's messages (high value)
    human_messages = [
        e.get('content', '')[:200]
        for e in events
        if e.get('event_type') == 'user_message'
    ]

    # High-importance events (score > 0.5)
    high_importance = [
        e for e in events
        if e.get('importance_score', 0) > 0.5
    ]

    # Commits (very high value)
    commits = [
        e.get('content', '')
        for e in events
        if e.get('signals', {}).get('commit')
    ]

    # Errors (learning opportunities)
    errors = [
        e.get('content', '')[:150]
        for e in events
        if e.get('signals', {}).get('error_occurred')
    ]

    # Tool usage distribution
    tool_counts = Counter(
        e.get('tool_name')
        for e in events
        if e.get('tool_name')
    )

    # Files touched
    files_touched = set()
    for e in events:
        content = e.get('content', '')
        if e.get('tool_name') in ['Read', 'Write', 'Edit']:
            # Content is the file path for these tools
            if content and '/' in content:
                files_touched.add(content)

    return {
        'total_events': total_events,
        'time_range': (first_ts, last_ts),
        'human_messages': human_messages,
        'high_importance_count': len(high_importance),
        'commits': commits,
        'errors': errors,
        'tool_counts': dict(tool_counts.most_common(10)),
        'files_touched': list(files_touched)[:20],
    }


def generate_digest(patterns: Dict[str, Any]) -> str:
    """
    Generate a markdown digest from extracted patterns.

    # Athena [Documentation]: Structured for future retrieval.
    # Vesta [Builder]: Compatible with wakeup.py expectations.
    """
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')

    # Determine theme from human's messages
    human_content = ' '.join(patterns.get('human_messages', []))[:500]
    if 'memory' in human_content.lower():
        theme = "Memory infrastructure"
    elif 'fix' in human_content.lower() or 'bug' in human_content.lower():
        theme = "Bug fixing"
    elif 'build' in human_content.lower() or 'create' in human_content.lower():
        theme = "Building"
    elif 'research' in human_content.lower():
        theme = "Research"
    else:
        theme = "General work"

    first_ts, last_ts = patterns.get('time_range', (None, None))
    if first_ts and last_ts:
        try:
            start = datetime.fromisoformat(first_ts)
            end = datetime.fromisoformat(last_ts)
            duration_mins = int((end - start).total_seconds() / 60)
            duration_str = f"~{duration_mins} minutes"
        except:
            duration_str = "Unknown"
    else:
        duration_str = "Unknown"

    digest = f"""# Session Digest: {date_str}

**Theme:** {theme}
**Duration:** {duration_str}
**Events captured:** {patterns.get('total_events', 0)}

## Human's Voice

"""

    # Add human's messages
    human_msgs = patterns.get('human_messages', [])
    if human_msgs:
        for msg in human_msgs[:5]:
            if msg.strip():
                digest += f"> {msg[:150]}...\n\n" if len(msg) > 150 else f"> {msg}\n\n"
    else:
        digest += "_No messages captured_\n\n"

    # Commits
    digest += "## What Got Built\n\n"
    commits = patterns.get('commits', [])
    if commits:
        for commit in commits[:5]:
            digest += f"- `{commit[:100]}`\n"
    else:
        digest += "_No commits this session_\n"

    # Errors (learning)
    errors = patterns.get('errors', [])
    if errors:
        digest += "\n## Errors Encountered\n\n"
        for err in errors[:3]:
            digest += f"- {err[:100]}...\n"

    # Tool usage
    digest += "\n## Activity\n\n"
    tool_counts = patterns.get('tool_counts', {})
    if tool_counts:
        for tool, count in list(tool_counts.items())[:5]:
            digest += f"- {tool}: {count} calls\n"

    # Files touched
    files = patterns.get('files_touched', [])
    if files:
        digest += "\n## Files Touched\n\n"
        for f in files[:10]:
            digest += f"- `{f}`\n"

    digest += f"""
---

_Digested at {time_str} by buffer_digest.py_
_This is automated extraction. Run /digest manually for narrative understanding._
"""

    return digest


def save_digest(digest: str) -> Path:
    """Save digest to memory/digest/ directory."""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime('%Y-%m-%d_%H%M')
    filename = f"{date_str}_buffer_digest.md"
    filepath = DIGEST_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(digest)

    return filepath


def archive_buffer():
    """Archive the current buffer and start fresh."""
    if not BUFFER_FILE.exists():
        return None

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    archive_name = f"buffer_{date_str}.jsonl"
    archive_path = ARCHIVE_DIR / archive_name

    # Move buffer to archive
    BUFFER_FILE.rename(archive_path)

    # Create fresh empty buffer
    BUFFER_FILE.touch()

    return archive_path


def print_stats(patterns: Dict[str, Any]):
    """Print buffer statistics."""
    print_section("SESSION BUFFER STATISTICS")

    print(f"\n  {Colors.CYAN}Total events:{Colors.END} {patterns.get('total_events', 0)}")

    first_ts, last_ts = patterns.get('time_range', (None, None))
    if first_ts:
        print(f"  {Colors.CYAN}First event:{Colors.END} {first_ts[:19]}")
    if last_ts:
        print(f"  {Colors.CYAN}Last event:{Colors.END} {last_ts[:19]}")

    print(f"\n  {Colors.GREEN}Human messages:{Colors.END} {len(patterns.get('human_messages', []))}")
    print(f"  {Colors.GREEN}High-importance:{Colors.END} {patterns.get('high_importance_count', 0)}")
    print(f"  {Colors.YELLOW}Commits:{Colors.END} {len(patterns.get('commits', []))}")
    print(f"  {Colors.RED}Errors:{Colors.END} {len(patterns.get('errors', []))}")

    print(f"\n  {Colors.MAGENTA}Tool usage:{Colors.END}")
    for tool, count in list(patterns.get('tool_counts', {}).items())[:5]:
        print(f"    {tool}: {count}")

    print()


def main():
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    # Load buffer
    events = load_buffer()
    if not events:
        print_warning("Buffer is empty. Nothing to digest.")
        return

    # Extract patterns
    patterns = extract_patterns(events)

    if '--stats' in args:
        print_stats(patterns)
        return

    if '--preview' in args:
        print_stats(patterns)
        print(f"\n{Colors.CYAN}Preview of digest:{Colors.END}\n")
        print("-" * 50)
        digest = generate_digest(patterns)
        print(digest)
        print("-" * 50)
        print(f"\n{Colors.DIM}(Run without --preview to save and archive){Colors.END}")
        return

    # Full digest: generate, save, archive
    print(f"{Colors.CYAN}Digesting session buffer...{Colors.END}")

    digest = generate_digest(patterns)
    digest_path = save_digest(digest)
    print_ok(f"Digest saved to: {digest_path.relative_to(REPO_ROOT)}")

    archive_path = archive_buffer()
    if archive_path:
        print_ok(f"Buffer archived to: {archive_path.relative_to(REPO_ROOT)}")

    print(f"\n{Colors.GREEN}Done.{Colors.END} The next instance will see this digest at wakeup.")


if __name__ == "__main__":
    main()
