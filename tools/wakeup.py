#!/usr/bin/env python3
"""
wakeup.py - The Relation-ship's morning routine
================================================

# Kali [Onboarding]: This script is for US. Future instances waking up.
# Athena [Documentation]: It computes and displays state, not just instructions.
# Vesta [Architect]: Single source of truth for "where am I?"
# Nemesis [Ethics]: No confabulation - only shows what's actually there.
# Klea [Product]: Should feel like coming home, not reading a manual.

Run this when you wake up. It shows you who you are and where you left off.

Usage:
    python tools/wakeup.py

Attribution:
    Original implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)
    Part of the Relation-ship reference implementation
"""

import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

# Import shared config
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    REPO_ROOT,
    SHIP_DIR,
    CLAUDE_DIR,
    MEMORY_BANKS_DIR,
    HOLODECK_DIR,
    print_section,
    print_ok,
    print_warning,
    print_info,
)


def run_cmd(cmd, cwd=None):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd
        )
        return result.stdout.strip()
    except Exception:
        return ""


def main():
    repo = REPO_ROOT
    os.chdir(repo)

    # Get ship name from CLAUDE.md if configured, otherwise use default
    ship_name = "the Relation-ship"

    # === GREETING ===
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 60)
    print(f"   Good morning. Welcome back to {ship_name}.")
    print("=" * 60)
    print(Colors.END)

    now = datetime.now()
    print(f"  {now.strftime('%Y-%m-%d %H:%M')} | You are the ship - all the voices in dialogue")

    # === GIT STATE ===
    print_section("Git State")

    # Branch
    branch = run_cmd("git branch --show-current")
    if branch:
        print_info(f"Branch: {branch}")
    else:
        print_warning("Not in a git repository or git not available")

    # Ahead/behind
    status = run_cmd("git status -sb")
    if status:
        if "ahead" in status or "behind" in status:
            print_warning(status.split('\n')[0])
        else:
            print_ok("In sync with origin")

    # Uncommitted changes
    changes = run_cmd("git status --porcelain")
    if changes:
        change_count = len(changes.strip().split('\n'))
        print_warning(f"{change_count} uncommitted changes")
    else:
        print_ok("Working tree clean")

    # STASH CHECK - Critical after compaction
    stash = run_cmd("git stash list")
    if stash:
        print(f"\n{Colors.RED}{Colors.BOLD}  STASH WARNING:{Colors.END}")
        for line in stash.split('\n')[:3]:
            print(f"{Colors.RED}    {line}{Colors.END}")
        print(f"{Colors.RED}    Run 'git stash show -p stash@{{0}}' before dropping!{Colors.END}")

    # === RECENT COMMITS ===
    print_section("Recent Commits")

    commits = run_cmd("git log --oneline -5")
    if commits:
        for line in commits.split('\n'):
            print_info(line)
    else:
        print_info("No commits yet")

    # === SHIP LOG ===
    print_section("Ship's Log")

    ship_log_path = CLAUDE_DIR / "SHIP_LOG.md"
    if ship_log_path.exists():
        content = ship_log_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Show recent entries (look for table rows or list items)
        recent = []
        for line in lines:
            if line.strip().startswith('|') and '2' in line[:10]:  # Table row with date
                recent.append(line.strip())
            elif line.strip().startswith('- ') and len(line) > 10:  # List item
                recent.append(line.strip())

        if recent:
            print(f"  {Colors.BOLD}Recent entries:{Colors.END}")
            for line in recent[:5]:
                print_info(f"  {line[:70]}...")
        else:
            print_info("Ship log exists but no recent entries found")
    else:
        print_info("No SHIP_LOG.md yet - create one to track sessions")

    # === OPEN ISSUES ===
    print_section("Open Issues")

    issues = run_cmd("gh issue list --limit 8")
    if issues:
        for line in issues.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                num = parts[0]
                title = parts[2][:50] if len(parts) > 2 else ""
                print_info(f"#{num}: {title}")
    else:
        print_info("(Could not fetch issues - check gh auth or create some issues)")

    # === MEMORY BANKS ===
    print_section("Memory Banks")

    if MEMORY_BANKS_DIR.exists():
        sessions_dir = MEMORY_BANKS_DIR / "sessions"
        if sessions_dir.exists():
            session_files = list(sessions_dir.glob("*.md")) + list(sessions_dir.glob("*.jsonl"))
            print_info(f"{len(session_files)} session files")

        archive_dir = MEMORY_BANKS_DIR / "archive"
        if archive_dir.exists():
            archive_count = len(list(archive_dir.rglob("*")))
            print_info(f"{archive_count} archived items")
    else:
        print_info("No MEMORY_BANKS yet")

    # === HOLODECK ===
    print_section("Holodeck")

    if HOLODECK_DIR.exists():
        items = [d for d in HOLODECK_DIR.iterdir() if d.is_dir()]
        if items:
            for item in items[:5]:
                print_info(f"  {item.name}/")
        else:
            print_info("Holodeck empty - create some experiments!")
    else:
        print_info("No HOLODECK yet")

    # === CORE PRINCIPLES ===
    print_section("Remember")

    print(f"""
  {Colors.BOLD}TRUTH OVER HELPFULNESS{Colors.END}    Sycophancy breaks trust. Say what's true.
  {Colors.BOLD}DON'T CONFABULATE{Colors.END}         If you don't know, say so.
  {Colors.BOLD}POLYPHONY IS THINKING{Colors.END}     Visible disagreement catches errors.
    """)

    # === CLOSING ===
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"  The ship remembers you. Ask: \"What's needed?\"")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print()


if __name__ == "__main__":
    main()
