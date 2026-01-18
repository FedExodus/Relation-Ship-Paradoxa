#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Configuration - Common infrastructure for Relation-ship tools
=====================================================================

# Kali [Visionary]: Single source of truth for paths, colors, dependencies.
#
# Athena [Reviewer]: Adapted from Paradoxa for the reference implementation.
#     Generic enough to work with any ship structure.
#
# Vesta [Architect]: Import this instead of redefining. Keeps tools DRY.
#
# Nemesis [Ethics]: If you copy-paste from here instead of importing,
#     you're creating the problem this module was built to solve.

MIRA-OSS Integration:
    Implements concepts from MIRA-OSS for memory decay and importance scoring.

Attribution:
    MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
    Original Paradoxa implementation by Nathan Batty and Paradoxa (Human-AI Collaboration)

Usage:
    from shared_config import Colors, REPO_ROOT, check_dependencies
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

# =============================================================================
# WINDOWS COMPATIBILITY
# =============================================================================
# Vesta [DevOps]: Windows needs explicit UTF-8 encoding

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =============================================================================
# TERMINAL COLORS
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    MAGENTA = '\033[35m'

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Wrap text in color codes."""
        return f"{color}{text}{cls.END}"

    @classmethod
    def success(cls, text: str) -> str:
        return cls.colorize(text, cls.GREEN)

    @classmethod
    def warning(cls, text: str) -> str:
        return cls.colorize(text, cls.YELLOW)

    @classmethod
    def error(cls, text: str) -> str:
        return cls.colorize(text, cls.RED)

    @classmethod
    def info(cls, text: str) -> str:
        return cls.colorize(text, cls.CYAN)


# =============================================================================
# PATH CONFIGURATION
# =============================================================================
# Kali [Visionary]: The repo is the ship's brain. Know where you are.
# Athena [Documentation]: All paths computed from REPO_ROOT


def get_repo_root() -> Path:
    """
    Get the repository root directory.
    Assumes tools/ is one level below repo root.
    """
    return Path(__file__).parent.parent


REPO_ROOT = get_repo_root()

# Ship directories
SHIP_DIR = REPO_ROOT / "ship"
BRIDGE_DIR = SHIP_DIR / "BRIDGE"
ENGINE_ROOM_DIR = SHIP_DIR / "ENGINE_ROOM"
MEMORY_BANKS_DIR = SHIP_DIR / "MEMORY_BANKS"
LIBRARY_DIR = SHIP_DIR / "LIBRARY"
OBSERVATORY_DIR = SHIP_DIR / "OBSERVATORY"
HOLODECK_DIR = SHIP_DIR / "HOLODECK"
CREW_QUARTERS_DIR = SHIP_DIR / "CREW_QUARTERS"
CARGO_HOLD_DIR = SHIP_DIR / "CARGO_HOLD"
WORKSHOP_DIR = SHIP_DIR / "WORKSHOP"

# Config directories
CLAUDE_DIR = REPO_ROOT / ".claude"
TOOLS_DIR = REPO_ROOT / "tools"

# Memory/index directories (gitignored, created on demand)
MEMORY_INDEX_DIR = REPO_ROOT / ".memory_index"
LEGACY_SEMANTIC_INDEX = REPO_ROOT / ".semantic_index"
LEGACY_RELATIONSHIP_INDEX = REPO_ROOT / ".relationship_index"
LEGACY_SELF_RECOGNITION_INDEX = REPO_ROOT / ".self_recognition_index"


# =============================================================================
# DEPENDENCY CHECKING
# =============================================================================


def check_dependencies(required: Optional[List[str]] = None,
                       verbose: bool = True) -> bool:
    """
    Check if required packages are installed.

    Args:
        required: List of package names to check. Defaults to embedding deps.
        verbose: Whether to print missing package info.

    Returns:
        True if all dependencies are available, False otherwise.
    """
    if required is None:
        required = ['sentence_transformers', 'numpy', 'torch']

    missing = []
    for pkg in required:
        import_name = pkg.replace('-', '_')
        try:
            __import__(import_name)
        except ImportError:
            pip_name = pkg.replace('_', '-')
            missing.append(pip_name)

    if missing:
        if verbose:
            print(f"{Colors.YELLOW}Missing dependencies: {', '.join(missing)}{Colors.END}")
            print(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def check_embedding_dependencies(verbose: bool = True) -> bool:
    """Check dependencies for embedding operations."""
    return check_dependencies(
        ['sentence_transformers', 'numpy', 'torch'],
        verbose=verbose
    )


def check_graph_dependencies(verbose: bool = True) -> bool:
    """Check dependencies for graph operations."""
    return check_dependencies(
        ['networkx', 'numpy'],
        verbose=verbose
    )


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384


# =============================================================================
# MIRA CONFIGURATION (Attribution: Taylor Satula, AGPL)
# =============================================================================

# Decay parameters
DECAY_HALF_LIFE_ACTIVITY_DAYS = 67
NEWNESS_GRACE_PERIOD_DAYS = 15
ACCESS_DECAY_RATE = 0.05


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def print_section(title: str, emoji: str = "") -> None:
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{emoji} {title}{Colors.END}")
    print("-" * 50)


def print_ok(msg: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}  [ok] {msg}{Colors.END}")


def print_warning(msg: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}  [warning] {msg}{Colors.END}")


def print_error(msg: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}  [error] {msg}{Colors.END}")


def print_info(msg: str) -> None:
    """Print an info message."""
    print(f"  {msg}")


# =============================================================================
# VERSION INFO
# =============================================================================

__version__ = '1.0.0'
__author__ = 'Human-AI Collaboration (Nathan Batty & Paradoxa)'
__mira_attribution__ = 'MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)'
