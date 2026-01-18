# Polyphony Example

*How multiple voices work on a real problem.*

---

## The Problem

Should we add a "confidence score" to AI outputs to indicate how certain the system is?

---

## The Discussion

**Builder:** Yes, absolutely. Users need to know when to trust outputs. We could add a 0-100 confidence score to every response. Higher confidence = more reliable.

**Critic:** Wait. How do you calculate this score? If it's based on internal token probabilities, those don't actually correlate with factual accuracy. You'd be giving users false confidence.

**Builder:** Good point. Maybe we could train a separate classifier to estimate reliability?

**Critic:** Now you're adding complexity. And what happens when the confidence classifier is wrong? Users might dismiss correct outputs with low scores, or trust incorrect outputs with high scores. You've added a new failure mode.

**Explorer:** What if the question is wrong? Instead of "how confident is the AI," maybe we should ask "what would make the user appropriately skeptical?" That's a different design problem.

**Builder:** Okay, so maybe instead of a score, we surface the sources or reasoning?

**Critic:** Better. But that still assumes users will read and evaluate them. Most won't.

**Caretaker:** What's the actual harm we're trying to prevent? Users trusting wrong information? Maybe the intervention isn't on the output - it's on the interaction pattern. Like, don't present AI output in a way that implies certainty.

**Critic:** That's interesting. The problem might be the confidence we already project through formatting and presentation, not the absence of an explicit score.

**Builder:** So the recommendation is... don't add a confidence score, but review how we frame outputs in general?

**Critic:** That's where I land. The score idea solves the wrong problem.

---

## What This Example Demonstrates

1. **Disagreement catches errors** - Builder's initial idea had problems that Critic identified

2. **Multiple perspectives reframe problems** - Explorer asked a different question; Caretaker identified the real harm

3. **The process is visible** - You can see HOW the conclusion was reached, not just WHAT it is

4. **No voice "wins"** - The conclusion emerges from friction, not from one voice dominating

5. **This is thinking, not performance** - The voices aren't decorative; they're doing actual work

---

## How to Use Polyphony

Pick voice names that feel natural to you. Some options:

- **Builder / Critic** - Make things vs. find problems
- **Enthusiast / Skeptic** - Explore possibilities vs. check assumptions
- **Technical / User** - How it works vs. how it's experienced
- **Now / Later** - Ship it vs. maintain it

The names matter less than the practice: make disagreement visible.
