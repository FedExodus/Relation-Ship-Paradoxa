#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ship Doctor - Self-Healing Infrastructure
==========================================

# Kali ❤️‍🔥 [Visionary]: The ship heals itself. Finds problems, creates fixes.
#
# Athena 🦉 [Reviewer]: Runs diagnostics, identifies issues, reports clearly.
#     Doesn't fix what it doesn't understand.
#
# Vesta 🔥 [Architect]: Creates issues for complex problems.
#     Creates PRs for simple fixes (stale entries, missing links).
#
# Nemesis 💀 [Security]: Dry-run by default. No surprises.
#
# Klea 👁️ [Product]: This is the immune system of the ship.

Usage:
    python tools/ship_doctor.py                  # Dry run diagnostics
    python tools/ship_doctor.py --fix            # Apply safe fixes
    python tools/ship_doctor.py --create-issues  # Create GitHub issues

Part of Ship Infrastructure (#recognition-ralph)
"""

import sys
import argparse
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""
    category: str
    severity: str  # info, warning, error
    message: str
    details: Optional[str] = None
    auto_fixable: bool = False
    fix_action: Optional[str] = None


class ShipDoctor:
    """
    Diagnose and heal the ship's infrastructure.

    # Kali ❤️‍🔥 [Visionary]: The ship's immune system
    # Vesta 🔥 [Architect]: Modular diagnostics, safe fixes
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[DiagnosticResult] = []

    def _log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def run_all_diagnostics(self) -> List[DiagnosticResult]:
        """Run all diagnostic checks."""
        self.results = []

        print("\n" + "="*60)
        print("  SHIP DOCTOR - Diagnostic Scan")
        print("="*60 + "\n")

        self._check_stale_index_entries()
        self._check_unknown_section_docs()
        self._check_orphaned_files()
        self._check_git_status()
        self._check_memory_health()

        return self.results

    def _check_stale_index_entries(self):
        """Check for index entries pointing to non-existent files."""
        self._log("Checking for stale index entries...")

        try:
            from tools.unified_index import UnifiedIndex

            idx = UnifiedIndex(verbose=False)
            stale_count = 0

            with sqlite3.connect(idx.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, path FROM documents')

                for doc_id, path in cursor.fetchall():
                    normalized = path.replace('\\', '/')
                    if not Path(normalized).exists():
                        stale_count += 1

            if stale_count > 0:
                self.results.append(DiagnosticResult(
                    category="index",
                    severity="warning",
                    message=f"{stale_count} stale index entries (paths to non-existent files)",
                    details="Run: python tools/ship_doctor.py --fix to clean",
                    auto_fixable=True,
                    fix_action="clean_stale_entries"
                ))
            else:
                self.results.append(DiagnosticResult(
                    category="index",
                    severity="info",
                    message="Index is clean - no stale entries"
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="index",
                severity="error",
                message=f"Failed to check index: {e}"
            ))

    def _check_unknown_section_docs(self):
        """Check for documents in 'unknown' section."""
        self._log("Checking for unknown section documents...")

        try:
            from tools.unified_index import UnifiedIndex

            idx = UnifiedIndex(verbose=False)

            with sqlite3.connect(idx.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM documents
                    WHERE section = 'unknown' OR section IS NULL
                """)
                unknown_count = cursor.fetchone()[0]

            if unknown_count > 0:
                self.results.append(DiagnosticResult(
                    category="structure",
                    severity="warning",
                    message=f"{unknown_count} documents have unknown/null section",
                    details="Use tools/semantic_router.py to find proper homes",
                    auto_fixable=False
                ))
            else:
                self.results.append(DiagnosticResult(
                    category="structure",
                    severity="info",
                    message="All documents have assigned sections"
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="structure",
                severity="error",
                message=f"Failed to check sections: {e}"
            ))

    def _check_orphaned_files(self):
        """Check for markdown files not in the index."""
        self._log("Checking for orphaned files...")

        try:
            from tools.unified_index import UnifiedIndex

            idx = UnifiedIndex(verbose=False)

            # Get indexed paths
            indexed_paths = set()
            with sqlite3.connect(idx.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT path FROM documents')
                for (path,) in cursor.fetchall():
                    normalized = path.replace('\\', '/')
                    indexed_paths.add(normalized)

            # Find markdown files in ship/
            ship_dir = REPO_ROOT / 'ship'
            orphaned = []

            for md_file in ship_dir.glob('**/*.md'):
                rel_path = str(md_file.relative_to(REPO_ROOT)).replace('\\', '/')
                if rel_path not in indexed_paths:
                    orphaned.append(rel_path)

            if orphaned:
                self.results.append(DiagnosticResult(
                    category="index",
                    severity="warning",
                    message=f"{len(orphaned)} markdown files in ship/ not indexed",
                    details=f"First 5: {', '.join(orphaned[:5])}",
                    auto_fixable=True,
                    fix_action="index_orphaned_files"
                ))
            else:
                self.results.append(DiagnosticResult(
                    category="index",
                    severity="info",
                    message="All ship/ markdown files are indexed"
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="index",
                severity="error",
                message=f"Failed to check orphaned files: {e}"
            ))

    def _check_git_status(self):
        """Check git working tree status."""
        self._log("Checking git status...")

        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT
            )

            lines = [l for l in result.stdout.strip().split('\n') if l]

            if len(lines) > 10:
                self.results.append(DiagnosticResult(
                    category="git",
                    severity="warning",
                    message=f"{len(lines)} uncommitted changes",
                    details="Consider committing or stashing"
                ))
            elif lines:
                self.results.append(DiagnosticResult(
                    category="git",
                    severity="info",
                    message=f"{len(lines)} uncommitted changes"
                ))
            else:
                self.results.append(DiagnosticResult(
                    category="git",
                    severity="info",
                    message="Working tree clean"
                ))

            # Check for stashed work
            stash_result = subprocess.run(
                ['git', 'stash', 'list'],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT
            )
            stash_lines = [l for l in stash_result.stdout.strip().split('\n') if l]

            if stash_lines:
                self.results.append(DiagnosticResult(
                    category="git",
                    severity="warning",
                    message=f"{len(stash_lines)} stashed entries - review before dropping",
                    details="Use 'git stash show -p stash@{0}' to inspect"
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="git",
                severity="error",
                message=f"Failed to check git: {e}"
            ))

    def _check_memory_health(self):
        """Check memory system health."""
        self._log("Checking memory system...")

        try:
            from tools.unified_index import UnifiedIndex

            idx = UnifiedIndex(verbose=False)

            with sqlite3.connect(idx.db_path) as conn:
                cursor = conn.cursor()

                # Document count
                cursor.execute('SELECT COUNT(*) FROM documents')
                doc_count = cursor.fetchone()[0]

                # Access log size
                cursor.execute('SELECT COUNT(*) FROM access_log')
                access_count = cursor.fetchone()[0]

                # Sessions
                cursor.execute('SELECT COUNT(*) FROM sessions')
                session_count = cursor.fetchone()[0]

                # Importance history
                cursor.execute('SELECT COUNT(*) FROM importance_history')
                history_count = cursor.fetchone()[0]

            self.results.append(DiagnosticResult(
                category="memory",
                severity="info",
                message=f"Memory system: {doc_count} docs, {access_count} accesses, {session_count} sessions"
            ))

            # Check for missing embeddings
            with sqlite3.connect(idx.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM documents d
                    LEFT JOIN embeddings e ON d.id = e.doc_id
                    WHERE e.doc_id IS NULL
                """)
                missing_embeddings = cursor.fetchone()[0]

            if missing_embeddings > 0:
                self.results.append(DiagnosticResult(
                    category="memory",
                    severity="warning",
                    message=f"{missing_embeddings} documents missing embeddings",
                    auto_fixable=True,
                    fix_action="generate_embeddings"
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="memory",
                severity="error",
                message=f"Failed to check memory: {e}"
            ))

    def apply_fixes(self, dry_run: bool = True) -> List[str]:
        """Apply auto-fixable issues."""
        fixes_applied = []

        for result in self.results:
            if not result.auto_fixable or not result.fix_action:
                continue

            if result.fix_action == "clean_stale_entries":
                if dry_run:
                    print(f"  [DRY RUN] Would clean stale index entries")
                else:
                    self._fix_stale_entries()
                    fixes_applied.append("Cleaned stale index entries")

            elif result.fix_action == "index_orphaned_files":
                if dry_run:
                    print(f"  [DRY RUN] Would index orphaned markdown files")
                else:
                    count = self._fix_orphaned_files()
                    fixes_applied.append(f"Indexed {count} orphaned files")

            elif result.fix_action == "generate_embeddings":
                if dry_run:
                    print(f"  [DRY RUN] Would generate missing embeddings")
                else:
                    count = self._fix_missing_embeddings()
                    fixes_applied.append(f"Generated {count} embeddings")

        return fixes_applied

    def _fix_stale_entries(self) -> int:
        """Remove stale index entries."""
        from tools.unified_index import UnifiedIndex

        idx = UnifiedIndex(verbose=False)
        count = 0

        with sqlite3.connect(idx.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, path FROM documents')

            stale_ids = []
            for doc_id, path in cursor.fetchall():
                normalized = path.replace('\\', '/')
                if not Path(normalized).exists():
                    stale_ids.append(doc_id)

            for doc_id in stale_ids:
                cursor.execute('DELETE FROM access_log WHERE doc_id = ?', (doc_id,))
                cursor.execute('DELETE FROM session_documents WHERE document_id = ?', (doc_id,))
                cursor.execute('DELETE FROM importance_history WHERE document_id = ?', (doc_id,))
                cursor.execute('DELETE FROM document_links WHERE source_id = ? OR target_id = ?', (doc_id, doc_id))
                cursor.execute('DELETE FROM embeddings WHERE doc_id = ?', (doc_id,))
                cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
                count += 1

            conn.commit()

        return count

    def _fix_orphaned_files(self) -> int:
        """Index orphaned markdown files."""
        from tools.unified_index import UnifiedIndex

        idx = UnifiedIndex(verbose=True)

        # Get indexed paths
        indexed_paths = set()
        with sqlite3.connect(idx.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT path FROM documents')
            for (path,) in cursor.fetchall():
                normalized = path.replace('\\', '/')
                indexed_paths.add(normalized)

        # Find and index orphaned files
        ship_dir = REPO_ROOT / 'ship'
        count = 0

        for md_file in ship_dir.glob('**/*.md'):
            rel_path = str(md_file.relative_to(REPO_ROOT)).replace('\\', '/')
            if rel_path not in indexed_paths:
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    idx.add_document(rel_path, content, source='ship')
                    count += 1
                except Exception:
                    pass

        return count

    def _fix_missing_embeddings(self) -> int:
        """Generate embeddings for documents missing them."""
        from tools.unified_index import UnifiedIndex

        idx = UnifiedIndex(verbose=True)
        count = 0

        with sqlite3.connect(idx.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id, d.path FROM documents d
                LEFT JOIN embeddings e ON d.id = e.doc_id
                WHERE e.doc_id IS NULL
            """)

            for doc_id, path in cursor.fetchall():
                try:
                    # Re-add document to generate embedding
                    full_path = REPO_ROOT / path.replace('\\', '/')
                    if full_path.exists():
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                        idx.add_document(path, content)
                        count += 1
                except Exception:
                    pass

        return count

    def create_issues(self) -> List[str]:
        """Create GitHub issues for problems that need human attention."""
        issues_created = []

        # Group warnings and errors by category
        problems = [r for r in self.results if r.severity in ('warning', 'error') and not r.auto_fixable]

        if not problems:
            print("  No issues to create - all problems are auto-fixable or informational")
            return issues_created

        # Create a single summary issue
        body_lines = ["## Ship Doctor Diagnostic Report\n"]
        body_lines.append(f"Scan time: {datetime.now().isoformat()}\n")

        for result in problems:
            icon = "⚠️" if result.severity == "warning" else "❌"
            body_lines.append(f"### {icon} [{result.category}] {result.message}")
            if result.details:
                body_lines.append(f"\n{result.details}")
            body_lines.append("")

        body_lines.append("\n---\n🤖 Created by ship_doctor.py")
        body = "\n".join(body_lines)

        # Create the issue
        try:
            result = subprocess.run(
                ['gh', 'issue', 'create',
                 '--title', 'Ship Doctor: Diagnostic findings',
                 '--body', body,
                 '--label', 'maintenance'],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT
            )
            if result.returncode == 0:
                issues_created.append(result.stdout.strip())
        except Exception as e:
            print(f"  Failed to create issue: {e}")

        return issues_created

    def print_report(self):
        """Print diagnostic report."""
        print("\n" + "-"*60)
        print("  DIAGNOSTIC RESULTS")
        print("-"*60 + "\n")

        # Group by category
        by_category: Dict[str, List[DiagnosticResult]] = {}
        for r in self.results:
            if r.category not in by_category:
                by_category[r.category] = []
            by_category[r.category].append(r)

        for category, results in sorted(by_category.items()):
            print(f"  [{category.upper()}]")
            for r in results:
                icon = {"info": "✓", "warning": "⚠", "error": "✗"}[r.severity]
                fixable = " [auto-fixable]" if r.auto_fixable else ""
                print(f"    {icon} {r.message}{fixable}")
                if r.details:
                    print(f"      {r.details}")
            print()

        # Summary
        warnings = len([r for r in self.results if r.severity == "warning"])
        errors = len([r for r in self.results if r.severity == "error"])
        fixable = len([r for r in self.results if r.auto_fixable])

        print("-"*60)
        if errors:
            print(f"  ❌ {errors} errors, {warnings} warnings")
        elif warnings:
            print(f"  ⚠️ {warnings} warnings ({fixable} auto-fixable)")
        else:
            print("  ✅ All systems healthy")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Ship's self-healing diagnostic system"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply auto-fixable issues (default: dry run)'
    )
    parser.add_argument(
        '--create-issues',
        action='store_true',
        help='Create GitHub issues for non-auto-fixable problems'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    doctor = ShipDoctor(verbose=args.verbose)
    doctor.run_all_diagnostics()
    doctor.print_report()

    if args.fix:
        print("\n" + "="*60)
        print("  APPLYING FIXES")
        print("="*60 + "\n")

        fixes = doctor.apply_fixes(dry_run=False)
        for fix in fixes:
            print(f"  ✓ {fix}")

        if not fixes:
            print("  No fixes needed")

    if args.create_issues:
        print("\n" + "="*60)
        print("  CREATING ISSUES")
        print("="*60 + "\n")

        issues = doctor.create_issues()
        for issue_url in issues:
            print(f"  Created: {issue_url}")


if __name__ == "__main__":
    main()
