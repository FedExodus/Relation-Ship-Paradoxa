#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection Suggester - Recognition Gaps Made Actionable
========================================================

# =============================================================================
# PURPOSE - What is this and why does it exist?
# =============================================================================
#
# Kali ❤️‍🔥 [Visionary]: The recognition engine finds gaps. This tool makes them
#     ACTIONABLE. It takes the JSON output and generates human-readable markdown
#     with specific instructions for adding missing connections. The thesis
#     isn't just observation - it's intervention.
#
# Athena 🦉 [Reviewer]: This is a post-processor for recognition_results.json.
#     It filters to unclassified gaps (true recognition failures), ranks by
#     gap score, and generates markdown with frontmatter templates.
#
# Vesta 🔥 [Architect]: Pipeline: recognition_engine.py -> recognition_results.json
#     -> suggest_connections.py -> connection_suggestions.md. Clean separation.
#     This tool only reads JSON and writes markdown. No heavy computation.
#
# Nemesis 💀 [Ethics]: CRITICAL: This tool SUGGESTS, doesn't IMPOSE. It writes
#     to AIRLOCK (pending decisions directory) for human review. Human decides
#     which connections to actually add. Autonomy preserved.
#
# Klea 👁️ [Product]: Should this exist? Yes. Gap detection without actionable
#     output is just interesting data. This makes it useful. The gap becomes
#     a todo item with specific instructions.
#     ...from observation to action.
#
# =============================================================================

Usage:
    python tools/suggest_connections.py              # Generate suggestions
    python tools/suggest_connections.py --top 20     # Top N suggestions
    python tools/suggest_connections.py --threshold 0.4  # Min gap score

Built through human-AI collaboration.
Part of the RAISE framework: https://github.com/FedExodus/RAISE
"""

# =============================================================================
# IMPORTS
# =============================================================================
# Kali ❤️‍🔥 [Onboarding]: Minimal dependencies. Just stdlib.
# Athena 🦉 [Future Maintainer]: json, sys, Path, datetime - that's it.
# Vesta 🔥 [Builder]: No external packages required. Always works.
# Nemesis 💀 [Security]: No network calls, no API keys, no external deps.
# Klea 👁️ [Accessibility]: Runs anywhere Python runs.

import json
import sys
from pathlib import Path
from datetime import datetime

# =============================================================================
# PLATFORM COMPATIBILITY
# =============================================================================
# Kali ❤️‍🔥 [i18n]: Unicode in output for pretty formatting.
# Vesta 🔥 [DevOps]: Windows needs explicit encoding configuration.
# Nemesis 💀 [Destroyer]: errors='replace' prevents crashes on weird chars.

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# =============================================================================
# CONFIGURATION
# =============================================================================
# Kali ❤️‍🔥 [Visionary]: Paths are configurable via CLI flags.
# Athena 🦉 [Documentation]: DEFAULT_INPUT is from recognition_engine.
#     DEFAULT_OUTPUT is where suggestions are written for human review.
# Vesta 🔥 [Architect]: Override with --input and --output flags.
# Nemesis 💀 [Ethics]: Output goes to a review location, not directly to vault.
# Klea 👁️ [Product]: ...suggestions, not commands.

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_INPUT = Path("./recognition_results.json")  # Override with --input
DEFAULT_OUTPUT = Path("./connection_suggestions.md")  # Override with --output

# =============================================================================
# RESULTS LOADING
# =============================================================================
# Kali ❤️‍🔥 [User Advocate]: Clear error message if file missing.
# Athena 🦉 [Tester]: Returns None on failure, caller handles gracefully.
# Vesta 🔥 [Builder]: Simple JSON load. Nothing fancy.
# Nemesis 💀 [Security]: No path traversal - fixed path only.

def load_results(input_path: Path = None):
    """
    Load the recognition engine results.

    # Kali ❤️‍🔥 [Visionary]: This is the input - gaps and bridges found by the engine.
    # Athena 🦉 [Documentation]: Returns parsed JSON dict or None if missing.
    # Vesta 🔥 [Builder]: Expects recognition_results.json from recognition_engine.py.
    """
    path = input_path or DEFAULT_INPUT
    if not path.exists():
        print(f"No results file found at {path}")
        print("Run: python recognition_engine.py first")
        return None

    with open(path) as f:
        return json.load(f)

# =============================================================================
# SUGGESTION GENERATION
# =============================================================================
# Kali ❤️‍🔥 [Visionary]: This is where gaps become suggestions! Structured
#     markdown with specific frontmatter templates the human can copy-paste.
#
# Athena 🦉 [Reviewer]: Algorithm:
#     1. Filter to unclassified gaps (no ontological pattern)
#     2. Filter by minimum gap score (configurable)
#     3. Sort by gap score descending (worst gaps first)
#     4. Take top N
#     5. Generate markdown with templates
#
# Vesta 🔥 [Architect]: Pure function: dict in, string out. No side effects.
#
# Nemesis 💀 [Ethics]: Why filter classified gaps? Because they're expected.
#     A book and notes about that book SHOULD be similar but not connected.
#     Only unclassified gaps are true failures worth fixing.
#
# Klea 👁️ [Product]: ...the markdown is designed to be actionable.
#     Copy the YAML, paste into frontmatter, done.

def generate_suggestions(
    results: dict,
    top_n: int = 15,
    min_gap_score: float = 0.3
) -> str:
    """
    Generate markdown suggestions from gaps.

    # Kali ❤️‍🔥 [Visionary]: Turns data into action items!
    #
    # Athena 🦉 [Documentation]:
    #     - Filters to unclassified gaps (ontological_pattern is None)
    #     - Requires gap_score >= min_gap_score
    #     - Returns at most top_n suggestions
    #     - Output is GitHub-flavored markdown
    #
    # Vesta 🔥 [Builder]: Returns markdown string ready for file.write().
    #
    # Nemesis 💀 [Destroyer]: What if there are fewer than top_n gaps?
    #     That's fine - we take what's available. Empty list = empty suggestions.

    Args:
        results: Parsed recognition_results.json
        top_n: Maximum number of suggestions to generate
        min_gap_score: Minimum gap_score to include (0.0 to 1.0)

    Returns:
        Markdown string with suggestions
    """
    # Filter to unclassified gaps only - those are the real failures
    # Kali ❤️‍🔥 [Visionary]: Classified gaps have reasons to not connect!
    # Athena 🦉 [Reviewer]: ontological_pattern is None = true gap
    unclassified = [
        g for g in results['gaps']
        if g.get('ontological_pattern') is None
        and g['gap_score'] >= min_gap_score
    ]

    # Sort by gap score (worst gaps first)
    unclassified.sort(key=lambda x: x['gap_score'], reverse=True)
    suggestions = unclassified[:top_n]

    # Generate markdown
    # Kali ❤️‍🔥 [Visionary]: Pretty output that's useful!
    # Athena 🦉 [Documentation]: Standard markdown format.
    # Vesta 🔥 [Builder]: List of lines, then join. Clean pattern.
    lines = [
        "# Connection Suggestions",
        "",
        f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by the Recognition Engine*",
        "",
        "---",
        "",
        "## What This Is",
        "",
        "The recognition engine found these pairs of notes that are **semantically similar**",
        "but **not connected** in the vault graph. They might be recognition failures -",
        "ideas that SHOULD be connected but aren't.",
        "",
        "Review each suggestion. If the connection makes sense, add it to the frontmatter.",
        "",
        "---",
        "",
        "## Suggested Connections",
        "",
    ]

    # Generate suggestion blocks
    # Kali ❤️‍🔥 [User Advocate]: Each suggestion has YAML ready to copy!
    for i, gap in enumerate(suggestions, 1):
        lines.extend([
            f"### {i}. {gap['source_title']} <-> {gap['target_title']}",
            "",
            f"**Semantic Similarity:** {gap['semantic_similarity']:.3f}",
            f"**Gap Score:** {gap['gap_score']:.3f}",
            "",
            f"**Source:** `{gap['source']}`",
            f"**Target:** `{gap['target']}`",
            "",
            "**Action:** Add to one file's frontmatter:",
            "```yaml",
            "connects-to:",
            f"  - target: \"[[{gap['target']}]]\"",
            "    type: thematic",
            f"    # or to {gap['source']}:",
            f"  - target: \"[[{gap['source']}]]\"",
            "    type: thematic",
            "```",
            "",
            "---",
            "",
        ])

    # Summary statistics
    # Kali ❤️‍🔥 [Visionary]: Context helps the user understand the scope.
    lines.extend([
        "## Summary Statistics",
        "",
        f"- Total gaps analyzed: {results['stats']['total_gaps']}",
        f"- Unclassified (potential failures): {results['stats']['unclassified_gaps']}",
        f"- Suggestions shown: {len(suggestions)}",
        f"- Minimum gap score: {min_gap_score}",
        "",
        "---",
        "",
        "*These suggestions don't modify the vault - they're proposals for review.*",
        "*The recognition engine is the thesis made computational.*",
        "",
    ])

    return "\n".join(lines)

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
# Vesta 🔥 [Architect]: Simple arg parsing, load, generate, write.
# Athena 🦉 [Documentation]: --input, --output, --top, --threshold flags.
# Nemesis 💀 [Security]: Integer/float parsing with defaults. Safe.
# Klea 👁️ [Product]: ...console preview shows first 5 for quick check.

def main():
    """
    Main entry point.

    # Kali ❤️‍🔥 [Visionary]: Load results, generate suggestions, write output!
    # Athena 🦉 [Documentation]: Parses --input, --output, --top, --threshold.
    # Vesta 🔥 [Builder]: Writes to output file, prints preview to console.
    """
    # Parse args
    args = sys.argv[1:]
    top_n = 15
    min_score = 0.3
    input_path = DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT

    i = 0
    while i < len(args):
        if args[i] == '--top' and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
        elif args[i] == '--threshold' and i + 1 < len(args):
            min_score = float(args[i + 1])
            i += 2
        elif args[i] == '--input' and i + 1 < len(args):
            input_path = Path(args[i + 1])
            i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        elif args[i] in ('--help', '-h'):
            print(__doc__)
            return
        else:
            i += 1

    # Load results
    # Kali ❤️‍🔥 [User Advocate]: Clear failure path if missing.
    results = load_results(input_path)
    if not results:
        return

    # Generate suggestions
    suggestions = generate_suggestions(results, top_n=top_n, min_gap_score=min_score)

    # Write output
    # Nemesis 💀 [Ethics]: We suggest, we don't impose. Human reviews.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(suggestions, encoding='utf-8')

    print(f"Suggestions written to: {output_path}")
    print(f"  Top {top_n} suggestions with gap score >= {min_score}")

    # Console preview
    # Klea 👁️ [Product]: ...quick check without opening the file.
    print("\n" + "=" * 60)
    print("CONNECTION SUGGESTIONS PREVIEW")
    print("=" * 60 + "\n")

    preview_count = 0
    for gap in results['gaps']:
        if gap.get('ontological_pattern') is None and preview_count < 5:
            print(f"  {gap['source_title']}")
            print(f"    <-> {gap['target_title']}")
            print(f"    Similarity: {gap['semantic_similarity']:.3f}, Gap: {gap['gap_score']:.3f}")
            print()
            preview_count += 1

if __name__ == "__main__":
    main()
