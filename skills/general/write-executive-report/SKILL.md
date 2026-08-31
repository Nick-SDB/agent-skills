---
name: write-executive-report
description: Create or rewrite a concise, conclusion-focused executive report from project progress, experiment results, technical notes, or status material. Use when the user asks for a 汇报版文档、实验汇报、项目进展报告、executive report, leadership-ready report, or stakeholder-facing progress summary that should emphasize progress and conclusions rather than implementation details.
---

# Write Executive Report

## Writing Rules

1. Focus the report on progress and conclusions. Do not include specific files or file paths.
2. Do not use bold formatting for values inside Markdown tables.
3. Keep one blank line after each Markdown table and remove other unnecessary blank lines.
4. Keep each sentence on one logical source line; do not insert manual line breaks within a sentence.
5. Use descriptive section headings without numeric prefixes.
6. Write GPU and hardware terms (MMA, TMA, tensor core, TMEM, tcgen05, warp specialization, softmax, double buffering, ping-pong) in their authoritative form; do not translate them into descriptive Chinese phrases.
7. Append each metric's change ratio in parentheses right after the value, for example 18.84 ms（−41%）or 25%（2×）.

## Quality Check

Before delivering the report, verify that every section supports a progress update or conclusion, no file details remain, table values are not bold, table spacing is correct, sentences are not manually wrapped, section headings are unnumbered, hardware terms use their authoritative form, and each changed value carries its ratio in parentheses.
