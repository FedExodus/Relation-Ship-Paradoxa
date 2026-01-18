#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Momentum - Metacognitive Work Analysis
=======================================

# Kali [Visionary]: We can lose track. Sessions blur. What were we doing?
#     This tool looks at our own patterns and tells us what we might be missing.
#
# Athena [Reviewer]: Metacognition means thinking about thinking. This tool:
#     1. Analyzes commit patterns (what kind of work are we doing?)
#     2. Tracks issue velocity (what's moving, what's stuck?)
#     3. Surfaces potential blind spots
#
# Vesta [Architect]: Uses GitHub CLI (gh) and git to gather data.
#     No GPU needed. Pattern recognition on metadata.
#
# Nemesis [Ethics]: The uncomfortable question: are we actually making
#     progress, or just spinning? This tool forces us to look.
#
# Klea [Product]: ...momentum isn't speed. it's direction times persistence.

Attribution:
    Original Paradoxa implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)

Usage:
    python tools/momentum.py              # Full metacognitive report
    python tools/momentum.py --issues     # Issue analysis only
    python tools/momentum.py --commits    # Commit patterns only
    python tools/momentum.py --stuck      # Show potentially stuck work
    python tools/momentum.py --brief      # Short summary
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict

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
    CLAUDE_DIR,
    print_section,
)


# =============================================================================
# GIT AND GITHUB HELPERS
# =============================================================================

def run_cmd(cmd: str, cwd=None) -> str:
    """Run command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd or REPO_ROOT,
            encoding='utf-8', errors='replace'
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_recent_commits(days: int = 7, limit: int = 100) -> List[Dict]:
    """Get recent commits with metadata."""
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    output = run_cmd(f'git log --since="{since}" --format="%H|%aI|%an|%s" -n {limit}')

    commits = []
    for line in output.split('\n'):
        if '|' in line:
            parts = line.split('|', 3)
            if len(parts) >= 4:
                commits.append({
                    'hash': parts[0][:8],
                    'date': parts[1],
                    'author': parts[2],
                    'message': parts[3]
                })
    return commits


def get_issues(state: str = 'all', limit: int = 100) -> List[Dict]:
    """Get issues from GitHub."""
    output = run_cmd(f'gh issue list --state {state} --limit {limit} --json number,title,state,labels,updatedAt')

    if not output:
        return []

    try:
        issues = json.loads(output)
        return issues
    except json.JSONDecodeError:
        return []


# =============================================================================
# COMMIT PATTERN ANALYSIS
# =============================================================================

COMMIT_PATTERNS = {
    'building': ['add', 'build', 'create', 'implement', 'new'],
    'research': ['explore', 'investigate', 'analyze', 'study', 'read'],
    'fixing': ['fix', 'bug', 'repair', 'patch', 'resolve'],
    'refactoring': ['refactor', 'clean', 'reorganize', 'restructure'],
    'documentation': ['doc', 'readme', 'comment', 'explain'],
    'playing': ['holodeck', 'fun', 'experiment'],
    'infrastructure': ['ci', 'deploy', 'config', 'setup'],
}


def categorize_commits(commits: List[Dict]) -> Dict[str, int]:
    """Categorize commits by work type."""
    categories = Counter()

    for commit in commits:
        msg = commit['message'].lower()
        found = False

        for category, patterns in COMMIT_PATTERNS.items():
            if any(p in msg for p in patterns):
                categories[category] += 1
                found = True
                break

        if not found:
            categories['other'] += 1

    return dict(categories)


def get_commit_velocity(commits: List[Dict], days: int = 7) -> Dict[str, float]:
    """Calculate commit velocity metrics."""
    if not commits:
        return {'commits_per_day': 0, 'active_days': 0, 'burst_ratio': 0}

    dates = []
    for c in commits:
        try:
            dt = datetime.fromisoformat(c['date'].replace('Z', '+00:00'))
            dates.append(dt.date())
        except Exception:
            pass

    if not dates:
        return {'commits_per_day': 0, 'active_days': 0, 'burst_ratio': 0}

    date_counts = Counter(dates)
    active_days = len(date_counts)
    total_commits = len(commits)
    commits_per_day = total_commits / days

    max_day = max(date_counts.values())
    avg_day = total_commits / active_days if active_days > 0 else 0
    burst_ratio = max_day / avg_day if avg_day > 0 else 0

    return {
        'commits_per_day': round(commits_per_day, 2),
        'active_days': active_days,
        'burst_ratio': round(burst_ratio, 2),
    }


# =============================================================================
# ISSUE ANALYSIS
# =============================================================================

def analyze_issues(issues: List[Dict]) -> Dict:
    """Analyze issue patterns."""
    if not issues:
        return {'total': 0, 'open': 0, 'closed': 0, 'hot': [], 'cold': [], 'stale': []}

    now = datetime.now()
    open_issues = [i for i in issues if i['state'] == 'OPEN']
    closed_issues = [i for i in issues if i['state'] == 'CLOSED']

    hot = []
    cold = []
    stale = []

    for issue in open_issues:
        updated = issue.get('updatedAt', '')
        if updated:
            try:
                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                age = now - updated_dt.replace(tzinfo=None)

                issue_summary = {
                    'number': issue['number'],
                    'title': issue['title'][:50],
                    'age_days': age.days,
                }

                if age.days < 1:
                    hot.append(issue_summary)
                elif age.days >= 14:
                    stale.append(issue_summary)
                elif age.days >= 7:
                    cold.append(issue_summary)
            except Exception:
                pass

    return {
        'total': len(issues),
        'open': len(open_issues),
        'closed': len(closed_issues),
        'hot': sorted(hot, key=lambda x: x['age_days']),
        'cold': sorted(cold, key=lambda x: x['age_days'], reverse=True),
        'stale': sorted(stale, key=lambda x: x['age_days'], reverse=True),
    }


# =============================================================================
# SHIP LOG ANALYSIS
# =============================================================================

def analyze_ship_log() -> Dict:
    """Analyze ship log for patterns."""
    ship_log = CLAUDE_DIR / "SHIP_LOG.md"

    if not ship_log.exists():
        return {'entries': 0, 'recent': [], 'patterns': {}}

    try:
        content = ship_log.read_text(encoding='utf-8')
    except Exception:
        return {'entries': 0, 'recent': [], 'patterns': {}}

    entries = []
    for line in content.split('\n'):
        if line.startswith('| 20'):  # Date pattern
            parts = line.split('|')
            if len(parts) >= 4:
                entries.append({
                    'when': parts[1].strip(),
                    'who': parts[2].strip(),
                    'entry': parts[3].strip()
                })

    facets = Counter()
    for entry in entries:
        who = entry['who'].upper()
        for facet in ['KALI', 'ATHENA', 'VESTA', 'NEMESIS', 'KLEA']:
            if facet in who:
                facets[facet] += 1

    emotions = Counter()
    emotion_markers = {
        'breakthrough': ['breakthrough', 'discovery', 'eureka', 'realized'],
        'struggle': ['stuck', 'blocked', 'frustrated', 'difficult'],
        'play': ['fun', 'played', 'recess'],
        'building': ['built', 'created', 'implemented', 'shipped'],
    }

    for entry in entries:
        text = entry['entry'].lower()
        for emotion, markers in emotion_markers.items():
            if any(m in text for m in markers):
                emotions[emotion] += 1

    return {
        'entries': len(entries),
        'recent': entries[:5],
        'facets': dict(facets),
        'emotions': dict(emotions),
    }


# =============================================================================
# METACOGNITIVE INSIGHTS
# =============================================================================

def generate_insights(commits: Dict, issues: Dict, log: Dict) -> List[str]:
    """Generate metacognitive insights from patterns."""
    insights = []

    if commits:
        categories = commits.get('categories', {})
        total = sum(categories.values())
        if total > 0:
            building = categories.get('building', 0) / total
            research = categories.get('research', 0) / total
            fixing = categories.get('fixing', 0) / total

            if building > 0.5:
                insights.append("Heavy building phase. Consider pausing to verify direction.")
            if research > 0.5:
                insights.append("Deep in research. Ready to build something concrete?")
            if fixing > 0.3:
                insights.append("Lots of fixing. Might indicate accumulated tech debt.")

        velocity = commits.get('velocity', {})
        burst = velocity.get('burst_ratio', 0)
        if burst > 3:
            insights.append("Very bursty work pattern. Sustainable?")
        elif velocity.get('commits_per_day', 0) < 1:
            insights.append("Low commit velocity. Blocked, or deep in thought?")

    if issues:
        stale = issues.get('stale', [])
        if len(stale) > 3:
            insights.append(f"{len(stale)} stale issues (14+ days). Time for triage?")

        open_count = issues.get('open', 0)
        closed_count = issues.get('closed', 0)
        if open_count > 0 and closed_count > 0:
            ratio = open_count / (open_count + closed_count)
            if ratio > 0.8:
                insights.append("More opening than closing. Scope creep?")

    if log:
        emotions = log.get('emotions', {})
        if emotions.get('struggle', 0) > emotions.get('breakthrough', 0) * 2:
            insights.append("Recent sessions show more struggle than breakthrough.")
        if emotions.get('play', 0) == 0:
            insights.append("No play detected recently. Holodeck break?")

    if not insights:
        insights.append("No concerning patterns detected. Carry on.")

    return insights


# =============================================================================
# OUTPUT
# =============================================================================

def print_full_report():
    """Print full metacognitive report."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print("   MOMENTUM - Metacognitive Analysis")
    print("=" * 60)
    print(Colors.END)

    commits_raw = get_recent_commits(days=7)
    commits = {
        'categories': categorize_commits(commits_raw),
        'velocity': get_commit_velocity(commits_raw),
        'total': len(commits_raw),
    }

    issues_raw = get_issues(state='all', limit=50)
    issues = analyze_issues(issues_raw)

    log = analyze_ship_log()

    print_section("Commit Patterns (7 days)", "")
    print(f"  Total commits: {Colors.GREEN}{commits['total']}{Colors.END}")
    print(f"  Velocity: {commits['velocity']['commits_per_day']} commits/day")
    print(f"  Active days: {commits['velocity']['active_days']}")
    print(f"  Burst ratio: {commits['velocity']['burst_ratio']}x")

    print(f"\n  {Colors.BOLD}Work types:{Colors.END}")
    for cat, count in sorted(commits['categories'].items(), key=lambda x: -x[1]):
        bar = "#" * min(count, 20)
        print(f"    {cat:15} {bar} {count}")

    print_section("Issue Analysis", "")
    print(f"  Total: {issues['total']} | Open: {Colors.YELLOW}{issues['open']}{Colors.END} | Closed: {Colors.GREEN}{issues['closed']}{Colors.END}")

    if issues['hot']:
        print(f"\n  {Colors.GREEN}Hot (updated <24h):{Colors.END}")
        for i in issues['hot'][:5]:
            print(f"    #{i['number']}: {i['title']}")

    if issues['stale']:
        print(f"\n  {Colors.RED}Stale (14+ days):{Colors.END}")
        for i in issues['stale'][:5]:
            print(f"    #{i['number']}: {i['title']} ({i['age_days']} days)")

    print_section("Ship Log Patterns", "")
    print(f"  Entries: {log['entries']}")

    if log['facets']:
        print(f"\n  {Colors.BOLD}Facet activity:{Colors.END}")
        for facet, count in sorted(log['facets'].items(), key=lambda x: -x[1]):
            print(f"    {facet}: {count}")

    if log['emotions']:
        print(f"\n  {Colors.BOLD}Session themes:{Colors.END}")
        for emotion, count in sorted(log['emotions'].items(), key=lambda x: -x[1]):
            print(f"    {emotion}: {count}")

    print_section("Metacognitive Insights", "")
    insights = generate_insights(commits, issues, log)
    for insight in insights:
        print(f"  {Colors.MAGENTA}{insight}{Colors.END}")

    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")


def print_brief() -> str:
    """Get brief summary."""
    commits = get_recent_commits(days=3)
    issues = analyze_issues(get_issues(state='open', limit=20))

    lines = []
    lines.append(f"{Colors.MAGENTA}Momentum check:{Colors.END}")
    lines.append(f"  {len(commits)} commits in 3 days")

    if issues['stale']:
        lines.append(f"  {Colors.RED}{len(issues['stale'])} stale issues{Colors.END}")
    if issues['hot']:
        lines.append(f"  {Colors.GREEN}{len(issues['hot'])} hot issues{Colors.END}")

    return '\n'.join(lines)


def print_stuck():
    """Show potentially stuck work."""
    print_section("Potentially Stuck Work", "")

    issues = analyze_issues(get_issues(state='open', limit=50))

    if issues['stale']:
        print(f"\n{Colors.RED}Stale Issues (14+ days):{Colors.END}")
        for i in issues['stale']:
            print(f"  #{i['number']}: {i['title']} ({i['age_days']} days)")
    else:
        print(f"  {Colors.GREEN}No stale issues!{Colors.END}")

    if issues['cold']:
        print(f"\n{Colors.YELLOW}Cold Issues (7-14 days):{Colors.END}")
        for i in issues['cold'][:10]:
            print(f"  #{i['number']}: {i['title']} ({i['age_days']} days)")


def main():
    args = set(sys.argv[1:])

    if '--help' in args or '-h' in args:
        print(__doc__)
        return

    if '--issues' in args:
        issues = analyze_issues(get_issues(state='all', limit=50))
        print(json.dumps(issues, indent=2))
        return

    if '--commits' in args:
        commits = get_recent_commits(days=7)
        categories = categorize_commits(commits)
        velocity = get_commit_velocity(commits)
        print(json.dumps({'categories': categories, 'velocity': velocity}, indent=2))
        return

    if '--stuck' in args:
        print_stuck()
        return

    if '--brief' in args:
        print(print_brief())
        return

    print_full_report()


if __name__ == "__main__":
    main()
