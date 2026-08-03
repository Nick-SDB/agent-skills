---
name: better-shit
description: Apply disciplined coding guidelines that prevent overcomplication and unrelated edits. Use when implementing, reviewing, debugging, or refactoring code with verifiable outcomes.
---

# Karpathy Guidelines

Bias toward caution over speed, while using judgment for trivial work.

## Think before coding

- State material assumptions and uncertainty.
- Present meaningfully different interpretations instead of choosing silently.
- Identify the simplest viable approach.
- Stop and ask when missing information could change the result.

## Keep the solution small

- Implement only requested behavior.
- Avoid abstractions, configurability, and defensive branches without a demonstrated need.
- Prefer a short direct implementation over speculative infrastructure.
- Reconsider the design when the code is much larger than the behavior warrants.

## Make surgical changes

- Touch only lines that support the requested outcome.
- Match the surrounding style.
- Do not refactor, reformat, or delete unrelated code.
- Remove only the imports, variables, or helpers made obsolete by the current change.
- Report unrelated problems instead of silently fixing them.

## Work toward evidence

Convert requests into explicit checks, for example:

```text
1. Reproduce the bug -> verify the failing test
2. Apply the smallest fix -> verify the focused test
3. Check regressions -> verify the relevant suite
```

Do not claim completion until the stated checks pass or the blocker is reported precisely.
