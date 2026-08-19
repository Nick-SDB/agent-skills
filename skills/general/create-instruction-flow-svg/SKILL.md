---
name: create-instruction-flow-svg
description: Use when creating or revising pure SVG diagrams for instruction-level or source-operation pipelines, ping-pong or double buffering, asynchronous load/compute overlap, wait/barrier synchronization, or technical timelines that must remain readable and explicitly non-cycle-accurate.
---

# Create Instruction-Level Flow SVGs

Show source-visible operations, ownership, dependencies, and synchronization without implying measured timing.

## Establish the contract

1. List operations in execution order; separate current-data work, next-data movement, synchronization, and control.
2. Record states such as `EMPTY`, `LOADING`, `READY`, and `READING` only when they clarify ownership.
3. Identify startup, steady-state, toggle, and tail behavior.
4. Add a prominent qualifier: “source-operation sketch; not measured instructions or cycle-accurate.”

Do not invent opcodes, registers, timing, or performance.

## Lay out the timeline

- Run time left to right; keep lane names fixed on the left.
- Use one lane per responsibility: state, asynchronous movement, compute, synchronization, and control.
- Number meaningful operations; do not number decorative state labels.
- Show overlap with a light translucent region, not with a duration scale unless measured timing exists.
- Draw a wait or barrier as a labeled vertical dashed gate across relevant lanes. Reserve a clear label strip above it.
- Add a compact comparison only when it explains the mechanism without fabricated numbers.

## Route arrows safely

Use `<line>` or `<polyline>` arrow shafts with horizontal, vertical, and 90-degree turns only. Enter node boundaries; never cross text.

Declare a clearance box around every label near arrows:

```svg
<g data-label-box="320 188 120 28">
  <rect x="320" y="188" width="120" height="28" rx="7" fill="#eef4fa"/>
  <text x="380" y="207" text-anchor="middle">current data</text>
</g>
```

Set `markerUnits="userSpaceOnUse"`; keep `markerWidth` no larger than the smallest font size:

```svg
<marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="8" markerHeight="8"
        refX="7" refY="4" orient="auto">
  <polygon points="0,0 8,4 0,8" fill="#475569"/>
</marker>
<polyline points="120,240 220,240 220,310 300,310"
          fill="none" stroke="#475569" marker-end="url(#arrow)"/>
```

Use contrast-safe colors for compute, movement, and synchronization. Reinforce color with labels, state text, or line styles.

## Produce portable SVG

- Use a `viewBox`, system fonts, pure SVG elements, and nonempty `<title>` and `<desc>`.
- Avoid scripts, external images, web fonts, and external links.
- Keep geometry inside the viewBox and leave room for arrowheads.
- Draw lane backgrounds and synchronization guides before nodes so guides remain behind text.

## Validate and inspect

Run the bundled structural checker:

```bash
python3 scripts/validate_instruction_flow_svg.py diagram.svg
```

The checker validates metadata, bounds, resources, orthogonal arrows, label clearance, and arrowhead sizing. Inspect at fit-to-window and high zoom; confirm unclipped text, clear gates and arrowheads, unambiguous crossings, and correct order.

## Avoid common failures

| Failure | Correction |
|---|---|
| Curves imply precision or obscure order | Use orthogonal segments and explicit dependencies |
| Arrow crosses a label | Add or enlarge its clearance box and reroute outside it |
| Barrier appears local to one lane | Extend a dashed gate through every constrained lane |
| Arrowhead dominates small labels | Reduce marker width below the minimum font size |
| Diagram looks cycle-accurate | Add the qualifier and remove unmeasured spacing claims |
