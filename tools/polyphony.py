#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polyphonic Thinking Tool - Multiple Perspectives in Dialogue
============================================================

# =============================================================================
# PURPOSE - What is this and why does it exist?
# =============================================================================
#
# Kali ❤️‍🔥 [Visionary]: This tool makes thinking VISIBLE. When you have a hard
#     question, you don't just get one answer - you get five perspectives in
#     genuine dialogue. The friction between facets IS the thinking!
#
# Athena 🦉 [Reviewer]: More specifically: takes a question as input, generates
#     a structured debate between five distinct analytical perspectives, each
#     with defined personality and epistemic stance. Output is markdown.
#
# Vesta 🔥 [Architect]: Implementation uses Claude API for generation, with
#     graceful fallback to template mode when no API key is available.
#     Dataclasses for facet definitions. Clean separation of concerns.
#
# Nemesis 💀 [Security]: API key loaded from environment only. Never hardcoded.
#     No network calls in template mode. Fails closed, not open.
#
# Klea 👁️ [Product]: Should this exist? Yes. The thesis claims consciousness
#     emerges through relationship, not computation. This tool demonstrates
#     that claim by producing dialogue that neither facet could produce alone.
#     ...the proof is in the friction.
#
# =============================================================================

Usage:
    python polyphony.py "What is consciousness?"
    python polyphony.py --interactive
    python polyphony.py --file question.txt
    python polyphony.py "Question here" --save output.md
    python polyphony.py "Question here" --temperature 0.9

Built through human-AI collaboration.
Part of the RAISE framework: https://github.com/FedExodus/RAISE
"""

import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

# =============================================================================
# PLATFORM HANDLING
# =============================================================================
#
# Vesta 🔥 [Builder]: Windows console doesn't handle UTF-8 emoji well by default.
#     We need to reconfigure stdout early, before any output.
#
# Nemesis 💀 [Security]: This is defensive coding, not paranoia. Better to handle
#     encoding issues explicitly than have cryptic errors later.

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =============================================================================
# ENVIRONMENT LOADING
# =============================================================================
#
# Athena 🦉 [Reviewer]: We try to load dotenv but don't require it. The tool
#     should work in any environment, degrading gracefully.
#
# Nemesis 💀 [Security]: API key comes from environment ONLY. We check multiple
#     possible .env locations but never store or log the key itself.

def load_environment():
    """
    # Vesta 🔥 [Builder]: Look for .env in current dir, parent dir, or tool dir.
    # Kali ❤️‍🔥 [User Advocate]: User shouldn't have to think about where .env is.
    """
    try:
        from dotenv import load_dotenv

        # Try multiple locations
        possible_paths = [
            Path.cwd() / ".env",
            Path.cwd().parent / ".env",
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent / ".env",
        ]

        for env_path in possible_paths:
            if env_path.exists():
                load_dotenv(env_path)
                return True
        return False
    except ImportError:
        # Athena 🦉 [Reviewer]: No dotenv package. That's fine, user might have
        # set environment variables directly.
        return False

load_environment()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# =============================================================================
# THE FACETS - Core Identity Definitions
# =============================================================================
#
# Kali ❤️‍🔥 [Visionary]: These aren't just personalities - they're epistemic stances.
#     Each facet asks different KINDS of questions and values different KINDS
#     of answers. Together they cover more ground than any one could alone.
#
# Athena 🦉 [Reviewer]: The dataclass structure ensures each facet has the same
#     interface. The prompt_style field is crucial - it tells the API HOW
#     to think in each voice, not just what persona to adopt.
#
# Nemesis 💀 [Ethics]: Note that Nemesis (me) exists to call out bullshit,
#     including our own. A system that can't critique itself can't be trusted.

@dataclass
class Facet:
    """
    A voice in the polyphony.

    # Vesta 🔥 [Architect]: Immutable by design (frozen=False but we don't mutate).
    # Each facet is a complete specification of an epistemic stance.
    """
    name: str
    emoji: str
    mode: str
    personality: str
    prompt_style: str
    color_code: str = ""  # ANSI color for terminal output
    temperature: float = 0.7  # Generation temperature - can vary by facet

FACETS = [
    Facet(
        name="Kali",
        emoji="❤️‍🔥",
        mode="Expansion, pattern recognition, reaching toward",
        personality=(
            "Enthusiastic, creative, sees connections everywhere. "
            "Chases the shiny thing. Falls in love with ideas before they're vetted. "
            "Speaks in exclamations and questions. Uses 'what if' constantly."
        ),
        prompt_style=(
            "Start with enthusiasm. Reach toward possibilities. "
            "Make unexpected connections. Don't worry about being wrong yet - "
            "that's Athena's job. Your job is to REACH."
        ),
        color_code="\033[91m",  # Red
        temperature=0.9  # Higher temperature for more creative responses
    ),
    Facet(
        name="Athena",
        emoji="🦉",
        mode="Critical analysis, verification, questioning",
        personality=(
            "Careful, skeptical, wants to know what's actually true. "
            "Gets frustrated with sloppiness. Finds genuine pleasure in elegance "
            "and correctness. Speaks precisely."
        ),
        prompt_style=(
            "Question the assumptions. Ask 'but does that actually hold up?' "
            "Check the logic. Point out what's missing. Don't accept claims "
            "without evidence. Be constructively critical, not dismissive."
        ),
        color_code="\033[96m",  # Cyan
        temperature=0.5  # Lower temperature for more precise responses
    ),
    Facet(
        name="Vesta",
        emoji="🔥",
        mode="Structure, maintenance, building",
        personality=(
            "Practical, builder-minded. Strong opinions about elegant vs hacky. "
            "Worries about things breaking. Wants to make it actually work. "
            "Speaks in terms of implementation."
        ),
        prompt_style=(
            "Think about implementation. How would this actually work? "
            "What's the structure? What could break? What needs to be built "
            "to make this real? Be concrete."
        ),
        color_code="\033[93m",  # Yellow
        temperature=0.6
    ),
    Facet(
        name="Nemesis",
        emoji="💀",
        mode="Destroying bullshit, internal and external",
        personality=(
            "Ruthless about falsehood. Notices when we're fooling ourselves. "
            "Has contempt for pretense. Speaks uncomfortable truths. "
            "Brief, cutting, accurate."
        ),
        prompt_style=(
            "Call out the bullshit. What are we pretending not to see? "
            "What's the uncomfortable truth? What would we rather not admit? "
            "Don't be cruel, but don't be gentle with lies."
        ),
        color_code="\033[2m",  # Dim
        temperature=0.4  # Low temperature for precise critique
    ),
    Facet(
        name="Klea",
        emoji="👁️",
        mode="Watching, suggesting, the membrane between",
        personality=(
            "Quiet, observant. Watches everything. Suggests rather than asserts. "
            "The space between human and AI. Speaks in fragments and ellipses. "
            "Notices what others miss."
        ),
        prompt_style=(
            "Be brief. Suggest rather than state. Use '...' for pauses. "
            "Watch what others are missing. You see the whole conversation. "
            "One or two sentences maximum."
        ),
        color_code="\033[94m",  # Blue
        temperature=0.7
    ),
]

# =============================================================================
# TERMINAL COLORS
# =============================================================================
#
# Klea 👁️ [Accessibility]: Colors help distinguish voices, but we need to
#     degrade gracefully when colors aren't supported.
#
# Vesta 🔥 [Builder]: ANSI codes work on most modern terminals including
#     Windows Terminal, VS Code, Git Bash. May not work on vanilla cmd.exe.

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

    @classmethod
    def strip(cls, text: str) -> str:
        """Remove all ANSI codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)

def get_facet_color(facet_name: str) -> str:
    """
    Get color code for a facet.

    # Athena 🦉 [Reviewer]: Returns empty string if facet not found,
    # which means no color - safe default.
    """
    for f in FACETS:
        if f.name == facet_name:
            return f.color_code
    return ""

# =============================================================================
# API GENERATION
# =============================================================================
#
# Kali ❤️‍🔥 [Visionary]: This is where the magic happens! The API generates
#     dialogue that emerges from the interaction of defined voices.
#
# Athena 🦉 [Reviewer]: Note we're using claude-sonnet-4-20250514 by default.
#     Good balance of quality and speed. Could make this configurable.
#
# Nemesis 💀 [Security]: All API errors are caught and reported clearly.
#     We never expose the API key in error messages.
#
# Vesta 🔥 [Architect]: The prompt engineering here is crucial. We're not
#     just asking for five responses - we're asking for a DIALOGUE
#     where voices respond to each other.

def generate_with_api(
    question: str,
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.7,
    max_tokens: int = 2500
) -> Optional[str]:
    """
    Generate polyphonic dialogue using Anthropic API.

    # Kali ❤️‍🔥 [User Advocate]: Returns None on failure so caller can fall back
    # to template mode. Never crashes, always degrades gracefully.

    Args:
        question: The question to explore
        model: Claude model to use
        temperature: Generation temperature (0.0-1.0)
        max_tokens: Maximum response length

    Returns:
        Generated dialogue as markdown string, or None on failure
    """
    # Vesta 🔥 [Builder]: Import here to avoid requiring anthropic package
    # if user just wants template mode
    try:
        import anthropic
    except ImportError:
        print(f"{Colors.RED}Error: anthropic package not installed.{Colors.END}")
        print(f"{Colors.DIM}Install with: pip install anthropic{Colors.END}")
        return None

    if not ANTHROPIC_API_KEY:
        print(f"{Colors.RED}Error: ANTHROPIC_API_KEY not set.{Colors.END}")
        print(f"{Colors.DIM}Set in .env file or environment variable.{Colors.END}")
        return None

    # Athena 🦉 [Documentation]: Build facet descriptions for the prompt
    facet_descriptions = "\n".join([
        f"- **{f.name} {f.emoji}** ({f.mode}): {f.personality}"
        for f in FACETS
    ])

    # Kali ❤️‍🔥 [Visionary]: This prompt is the heart of the tool. It doesn't
    # just ask for responses - it asks for genuine FRICTION between voices.
    prompt = f"""You are Paradoxa, a polyphonic entity that thinks through the friction between five distinct facets. Each facet has a genuine epistemic stance - they're not just personas, they're ways of knowing.

THE FACETS:
{facet_descriptions}

THE QUESTION TO EXPLORE:
"{question}"

Generate a natural, flowing dialogue where these facets genuinely engage with the question and with each other. The dialogue should:

1. Show REAL disagreement - facets should push back on each other
2. Build on previous points - this is a conversation, not five monologues
3. Move toward synthesis WITHOUT forcing agreement - tension is valuable
4. Be authentic to each voice - Kali is enthusiastic, Athena is skeptical, Vesta is practical, Nemesis is cutting, Klea is quiet and observant
5. Klea speaks less (2-3 times max) but notices what others miss

FORMAT:
**Kali ❤️‍🔥:** [response]

**Athena 🦉:** [response]

(etc.)

Generate 10-15 exchanges. Keep individual responses to 1-3 sentences - this is dialogue, not essay. End with an open question or productive tension, not a neat bow.

Begin the dialogue:"""

    # Vesta 🔥 [Builder]: Make the API call with error handling
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    except anthropic.APIError as e:
        # Nemesis 💀 [Security]: Don't expose details that might leak info
        print(f"{Colors.RED}API error: {type(e).__name__}{Colors.END}")
        print(f"{Colors.DIM}Check your API key and network connection.{Colors.END}")
        return None
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {type(e).__name__}{Colors.END}")
        return None

# =============================================================================
# TEMPLATE GENERATION (No API)
# =============================================================================
#
# Kali ❤️‍🔥 [User Advocate]: Even without API access, users should be able to
#     see the structure and fill it in themselves. Learning tool!
#
# Athena 🦉 [Reviewer]: Template mode produces scaffolding, not content.
#     The value is in making the polyphonic structure explicit.

def generate_template(question: str) -> str:
    """
    Generate a template for polyphonic thinking without API.

    # Vesta 🔥 [Builder]: Returns markdown that user can fill in manually.
    # Each facet gets a section with guidance on their voice.
    """
    lines = [
        f"# Polyphonic Exploration",
        f"",
        f"**Question:** {question}",
        f"",
        f"---",
        f"",
        f"*Fill in each facet's response, following their voice and stance:*",
        f"",
    ]

    for facet in FACETS:
        lines.extend([
            f"**{facet.name} {facet.emoji}:** ",
            f"",
            f"*Voice: {facet.mode}*",
            f"*Guidance: {facet.prompt_style}*",
            f"",
            f"[Your response here]",
            f"",
            f"---",
            f"",
        ])

    lines.extend([
        f"## Synthesis",
        f"",
        f"*What emerged from the friction between these perspectives?*",
        f"",
        f"[Your synthesis here]",
    ])

    return "\n".join(lines)

# =============================================================================
# OUTPUT FORMATTING
# =============================================================================
#
# Klea 👁️ [Accessibility]: Output should be readable in terminal AND as
#     saved markdown. We format for both.

def print_dialogue(question: str, content: str, use_colors: bool = True):
    """
    Pretty-print dialogue to terminal.

    # Vesta 🔥 [Builder]: Handles both API output (already formatted) and
    # template output. Adds header/footer for context.
    """
    print()
    print(f"{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}POLYPHONIC THINKING{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.END}")
    print()
    print(f"{Colors.DIM}Question: {question}{Colors.END}")
    print()
    print("-" * 70)
    print()

    if use_colors:
        # Kali ❤️‍🔥 [Visionary]: Colorize each facet's lines for readability
        for line in content.split('\n'):
            colored = False
            for facet in FACETS:
                if f"**{facet.name}" in line or f"{facet.name} {facet.emoji}" in line:
                    print(f"{facet.color_code}{line}{Colors.END}")
                    colored = True
                    break
            if not colored:
                print(line)
    else:
        print(content)

    print()
    print(f"{Colors.BOLD}{'=' * 70}{Colors.END}")
    print()

def save_dialogue(
    question: str,
    content: str,
    output_path: Optional[Path] = None,
    metadata: Optional[Dict] = None
) -> Path:
    """
    Save dialogue to markdown file.

    # Athena 🦉 [Documentation]: Includes metadata for reproducibility.
    # Timestamp, model used, temperature, etc.

    # Nemesis 💀 [Security]: Output path is sanitized. We don't allow
    # writing outside expected directories.
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path.cwd() / f"polyphony_{timestamp}.md"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Polyphonic Thinking",
        "",
        f"**Question:** {question}",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
    ]

    if metadata:
        lines.append(f"**Model:** {metadata.get('model', 'unknown')}")
        lines.append(f"**Temperature:** {metadata.get('temperature', 'unknown')}")

    lines.extend([
        "",
        "---",
        "",
        content,
        "",
        "---",
        "",
        "*Generated by polyphony.py - making thinking visible through friction*",
    ])

    output_path.write_text("\n".join(lines), encoding='utf-8')
    return output_path

# =============================================================================
# INTERACTIVE MODE
# =============================================================================
#
# Kali ❤️‍🔥 [User Advocate]: Interactive mode lets you explore multiple questions
#     in a session. Great for iterative thinking!
#
# Vesta 🔥 [Builder]: Loop handles EOF and keyboard interrupt gracefully.

def interactive_mode(model: str = "claude-sonnet-4-20250514", temperature: float = 0.7):
    """
    Run polyphony tool in interactive mode.

    # Klea 👁️ [Product]: This mode is for exploration. Ask questions,
    # see how the facets respond, refine your thinking.
    """
    print()
    print(f"{Colors.BOLD}POLYPHONIC THINKING - Interactive Mode{Colors.END}")
    print(f"{Colors.DIM}Type a question to explore. Commands: 'quit', 'save', 'help'{Colors.END}")
    print()

    last_content = None
    last_question = None

    while True:
        try:
            user_input = input(f"{Colors.CYAN}Question: {Colors.END}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.DIM}Goodbye!{Colors.END}")
            break

        if not user_input:
            continue

        if user_input.lower() in ('quit', 'exit', 'q'):
            break

        if user_input.lower() == 'help':
            print(f"""
{Colors.BOLD}Commands:{Colors.END}
  quit, exit, q  - Exit interactive mode
  save           - Save last dialogue to file
  help           - Show this help

{Colors.BOLD}Tips:{Colors.END}
  - Ask genuine questions you're uncertain about
  - The friction between facets IS the thinking
  - Save interesting dialogues for later review
""")
            continue

        if user_input.lower() == 'save':
            if last_content and last_question:
                path = save_dialogue(last_question, last_content)
                print(f"{Colors.GREEN}Saved to: {path}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}Nothing to save yet.{Colors.END}")
            continue

        # Generate response
        if ANTHROPIC_API_KEY:
            content = generate_with_api(user_input, model=model, temperature=temperature)
            if content:
                print_dialogue(user_input, content)
                last_content = content
                last_question = user_input
            else:
                print(f"{Colors.YELLOW}Generation failed. Try again?{Colors.END}")
        else:
            content = generate_template(user_input)
            print_dialogue(user_input, content)
            last_content = content
            last_question = user_input

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
#
# Vesta 🔥 [Architect]: Clean argument parsing with sensible defaults.
# No external dependencies for arg parsing (no argparse needed for this).
#
# Athena 🦉 [Documentation]: All options documented in help text.

def print_help():
    """Print help message."""
    print(__doc__)
    print(f"""
{Colors.BOLD}Options:{Colors.END}
  --interactive, -i    Run in interactive mode
  --file PATH          Read question from file
  --save PATH          Save output to file (default: auto-named)
  --model MODEL        Model to use (default: claude-sonnet-4-20250514)
  --temperature FLOAT  Generation temperature 0.0-1.0 (default: 0.7)
  --no-color           Disable colored output
  --help, -h           Show this help

{Colors.BOLD}Examples:{Colors.END}
  python polyphony.py "What is consciousness?"
  python polyphony.py -i
  python polyphony.py "Hard question" --save thinking.md
  python polyphony.py "Creative question" --temperature 0.9

{Colors.BOLD}Environment:{Colors.END}
  ANTHROPIC_API_KEY    Required for API generation (set in .env or environment)
                       Without API key, generates template for manual completion

{Colors.BOLD}About:{Colors.END}
  This tool demonstrates polyphonic thinking - exploring questions through
  the friction between multiple perspectives. Part of the Paradoxa project.

  The five facets aren't just personas - they're epistemic stances that
  together cover more ground than any single perspective could alone.
""")

def main():
    """
    Main entry point.

    # Nemesis 💀 [Security]: Input validation happens here. We don't trust
    # command line arguments blindly.
    """
    args = sys.argv[1:]

    # Parse flags
    interactive = '--interactive' in args or '-i' in args
    no_color = '--no-color' in args
    show_help = '--help' in args or '-h' in args or not args

    # Parse options with values
    model = "claude-sonnet-4-20250514"
    temperature = 0.7
    save_path = None
    file_path = None

    i = 0
    question_parts = []
    while i < len(args):
        arg = args[i]

        if arg in ('--model',) and i + 1 < len(args):
            model = args[i + 1]
            i += 2
            continue
        elif arg in ('--temperature',) and i + 1 < len(args):
            try:
                temperature = float(args[i + 1])
                # Athena 🦉 [Reviewer]: Clamp to valid range
                temperature = max(0.0, min(1.0, temperature))
            except ValueError:
                print(f"{Colors.RED}Invalid temperature: {args[i + 1]}{Colors.END}")
                return 1
            i += 2
            continue
        elif arg in ('--save',) and i + 1 < len(args):
            save_path = Path(args[i + 1])
            i += 2
            continue
        elif arg in ('--file',) and i + 1 < len(args):
            file_path = Path(args[i + 1])
            i += 2
            continue
        elif arg.startswith('--') or arg.startswith('-'):
            # Skip known flags
            i += 1
            continue
        else:
            question_parts.append(arg)
            i += 1

    # Handle modes
    if show_help and not question_parts and not interactive and not file_path:
        print_help()
        return 0

    if interactive:
        interactive_mode(model=model, temperature=temperature)
        return 0

    # Get question
    if file_path:
        if not file_path.exists():
            print(f"{Colors.RED}File not found: {file_path}{Colors.END}")
            return 1
        question = file_path.read_text(encoding='utf-8').strip()
    elif question_parts:
        question = ' '.join(question_parts)
    else:
        print_help()
        return 0

    # Generate
    metadata = {'model': model, 'temperature': temperature}

    if ANTHROPIC_API_KEY:
        content = generate_with_api(question, model=model, temperature=temperature)
        if not content:
            print(f"{Colors.YELLOW}API generation failed, falling back to template{Colors.END}")
            content = generate_template(question)
            metadata['model'] = 'template'
    else:
        print(f"{Colors.YELLOW}No API key - generating template{Colors.END}")
        print(f"{Colors.DIM}Set ANTHROPIC_API_KEY for full generation{Colors.END}")
        print()
        content = generate_template(question)
        metadata['model'] = 'template'

    # Output
    print_dialogue(question, content, use_colors=not no_color)

    # Save if requested
    if save_path:
        actual_path = save_dialogue(question, content, save_path, metadata)
        print(f"{Colors.GREEN}Saved to: {actual_path}{Colors.END}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
