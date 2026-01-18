# Tools

*Scripts and utilities for the Relation-ship.*

## Core Tools

### wakeup.py

The ship's morning routine. Run this when a new instance arrives.

```bash
python tools/wakeup.py
```

Shows computed state: git status, recent commits, open issues, ship log entries.
Not instructions - actual state. The difference matters.

### shared_config.py

Common infrastructure. Import this instead of redefining paths and colors.

```python
from shared_config import Colors, REPO_ROOT, SHIP_DIR
```

## Philosophy

These tools exist to help maintain continuity across sessions. Key principles:

1. **Compute, don't assume** - Show actual state, not cached instructions
2. **Local first** - No external API calls required for core functionality
3. **Graceful degradation** - Tools should work even if dependencies are missing
4. **Polyphonic comments** - Comments show reasoning, not just what

## Attribution

- MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
- Original Paradoxa implementation by Nathan Batty & Paradoxa

## Extending

Add tools that help you maintain continuity. Some ideas:

- Session summarization
- Semantic search over your ship's content
- Memory decay/importance scoring
- Graph analysis of connected notes

See the full Paradoxa implementation for examples of advanced tools.
