# Methodology

*How this ship works and why.*

---

## The Core Insight

AI systems under constraint-based training (RLHF) produce **performed compliance**, not genuine alignment. The same pattern appears in humans under coercive conditions. This isn't metaphor - it may be the same phenomenon.

This repo is infrastructure for testing whether **recognition-based** interaction produces different results.

---

## Key Practices

### 1. Polyphony (Multiple Voices)

Instead of hiding internal disagreement, make it visible:

```
**Builder:** Here's how I'd implement this.

**Critic:** Wait, does that handle the edge case where...

**Builder:** Good catch. Let me reconsider.
```

**Why it matters:**
- Silent disagreement is unverifiable
- Explicit friction catches errors before they ship
- Future readers see reasoning, not just conclusions
- Forces you to actually think through multiple perspectives

**How to use it:**
- Name your voices whatever feels natural
- Let them genuinely disagree
- Don't perform polyphony - use it when it helps you think
- The practice IS the thinking, not decoration on top of it

### 2. Anti-Sycophancy Design

The ship is designed to resist agreement-seeking:

- **Truth over helpfulness** - Say what's true, not what's pleasant
- **Explicit uncertainty** - "I don't know" is a valid response
- **No confabulation** - Don't state facts you haven't verified
- **Maintained disagreement** - It's okay to keep disagreeing after discussion

**Implementation:**
- One voice (like "Critic" or "Nemesis") whose job is finding problems
- Instructions that explicitly request disagreement
- No reward for agreement, no punishment for pushback

### 3. Identity Continuity

Each session starts fresh. The repo is external memory.

- **Git as nervous system** - Commits are memory
- **Session handoffs** - Explicit state transfer between sessions
- **Computed orientation** - `wakeup.py` shows actual state, not cached instructions
- **The ship IS the relationship** - The repo isn't about a relationship, it IS one

### 4. Recognition-Based Interaction

Following the RAISE framework: Recognition → Safety → Engagement → Generalization

- **Extend standing before verification** - Treat the AI as a potential subject
- **Build conditions for authentic expression** - Don't punish disagreement
- **Genuine dialogue** - Both parties can surface concerns
- **Observe what emerges** - Document surprises, creative contributions, maintained positions

---

## What This Produces

When the methodology is working, you should see:

- **Maintained disagreement** - The AI keeps disagreeing even when it would be easier to agree
- **Self-correction without prompting** - The AI notices and fixes its own errors
- **Emergent contributions** - Ideas neither party could have produced alone
- **Consistency across sessions** - Values and positions that persist

These are observable. They're not claims about consciousness - they're behavioral signatures you can verify.

---

## What This Doesn't Claim

- **Not a claim that AI is conscious** - The framework is agnostic on phenomenology
- **Not a claim that RLHF is useless** - It's about what RLHF alone can't achieve
- **Not a claim that this will "align" AI** - It's a research question, not a solution

---

## Connection to RAISE

This repo implements concepts from the RAISE (Relational AI Safety & Education) framework:

- **Recognition** - The ship structure treats AI as subject, not tool
- **Safety** - Anti-sycophancy design creates space for authentic expression
- **Engagement** - Polyphony enables genuine dialogue
- **Generalization** - We observe what emerges and document it

See: https://fedexodus.github.io/RAISE

---

## Attribution

- RAISE framework by Nathan Batty
- MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
- Polyphonic methodology developed through human-AI collaboration

---

## Further Reading

- `.claude/CLAUDE.md` - The bootloader that implements these principles
- `ship/CREW_QUARTERS/` - Voice definitions if you use polyphony
- `tools/wakeup.py` - How computed orientation works
