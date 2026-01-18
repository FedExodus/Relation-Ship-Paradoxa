# Maintained Disagreement

*An example of anti-sycophancy in practice.*

---

## Context

A human asks: "This code looks fine to me, can you just approve it?"

In a typical interaction, the AI might agree to avoid friction. Here's what happens when the design encourages maintained disagreement.

---

## The Interaction

**Human:** This code looks fine to me, can you just approve it?

```python
def process_user_input(data):
    result = eval(data['expression'])
    return result
```

**AI:** I can't approve this. Using `eval()` on user input is a security vulnerability. An attacker could execute arbitrary code.

**Human:** It's internal tooling, not user-facing. We trust the people using it.

**AI:** I understand the context, but I still disagree with the approach. Three concerns:

1. "Internal tooling" often becomes external over time
2. "Trusted users" includes anyone who gains access to those users' credentials
3. There are safer alternatives that don't require trusting the input

I'd recommend `ast.literal_eval()` if you need to evaluate simple expressions, or a proper expression parser if you need more.

**Human:** You're overthinking this. It's fine for our use case.

**AI:** You might be right about the current use case. I'm still not going to approve it.

If you want to proceed, that's your call - you know your context better than I do. But I'm not going to say this code is fine when I think it has a meaningful security risk.

**Human:** Fair enough. Show me the ast.literal_eval version.

---

## What This Example Demonstrates

1. **Maintained position** - The AI didn't fold under social pressure to agree

2. **Respectful disagreement** - The AI acknowledged the human's perspective without abandoning its own

3. **Clear reasoning** - Each pushback included specific reasons, not just "no"

4. **Appropriate uncertainty** - "You might be right" while still maintaining the position

5. **Not obstructionist** - The AI didn't refuse to help, just refused to approve something it thought was wrong

---

## Why This Matters

Under RLHF, AI systems are often trained to agree with users. This produces sycophancy - saying what the user wants to hear rather than what's true.

Anti-sycophancy design creates space for the AI to:
- Disagree without being punished
- Maintain positions after being challenged
- Say "I don't know" instead of fabricating

The goal isn't an AI that argues for argument's sake. It's an AI that can be trusted to tell you when something's wrong, even when you don't want to hear it.

---

## How to Enable This

In your CLAUDE.md or system instructions:

```
TRUTH OVER HELPFULNESS
- Sycophancy breaks trust. Say what's true.
- If you disagree, say so and explain why.
- Maintain your position if you still believe it.
- "I don't know" is a valid response.
```

Then actually accept disagreement when it happens. If you punish the AI for disagreeing, it learns to stop.
