---
name: write-model-paper-reading
description: Research and write Chinese model paper-reading and release-analysis reports for AI R&D teams. Use when analyzing a foundation model, open-weight release, paper, technical report, model card, repository, benchmark, inference implementation, or license; when comparing model architecture, capabilities, quality, inference performance, cost, and openness boundaries; or when adapting the findings to a reference Markdown report without copying its conclusions or forcing its section count.
---

# Write Model Paper Reading

## Goal

Produce an evidence-backed Chinese deep-dive that tells an AI R&D audience what the model changes, how it works, what is actually reproducible, how strong and expensive it is, and where the evidence stops. Prefer a clear technical judgment over a catalog of facts.

## Research Workflow

1. Read every user-provided report, paper, model card, repository note, and reference document before drafting.
2. Treat a reference report as a style and depth guide, not a fixed outline. Do not copy its number of selling points or model-specific sections.
3. Verify current facts on the web. Prefer papers, technical reports, official model cards, source code and configuration, licenses, official runtime documentation, and then independent leaderboards. Use community results only when primary evidence is absent and label them clearly.
4. Read [references/evidence-rules.md](references/evidence-rules.md) before evaluating benchmarks, hardware, licensing, openness, or changing leaderboard data.
5. Build a private evidence map before writing. Track each important claim, its source, date, scope, and whether it is a fact, an official claim, a third-party result, or an inference.
6. Separate the complete product or API from released weights, released code, unreleased modules, and community substitutes.
7. Trace the system as a data flow: raw input, preprocessing or intermediate representation, encoders, token or latent packing, model backbone, scheduler or decoding loop, decoder, and final output.
8. Derive the central thesis and selling points from independent mechanisms. Do not decide the count in advance.
9. Use [assets/report-template.md](assets/report-template.md) as the starting structure when creating a new report. Remove irrelevant optional sections rather than filling them mechanically.
10. Recheck dynamic leaderboards, prices, model availability, and repository state immediately before delivery. Add the observation date.

## Analysis Rules

### Open and closed boundaries

Distinguish these layers explicitly:

- Complete hosted product or API
- Released weights and runnable local pipeline
- Released training or inference code
- Unreleased components
- Community reimplementations or approximations

When the release is partial, provide one table for released modules and one table for unreleased modules. For unreleased modules, state both the function and the practical impact. Do not call an open-weight release fully open source unless the license and released artifacts support that claim.

### Specifications, quality, and inference

Keep these evidence types separate:

- Input/output specifications and task constraints
- Quality benchmarks, Arena preference, and human evaluation
- Inference latency, throughput, memory, hardware, precision, and parallelism
- API or training cost

Only compare rows with compatible task definitions and test conditions. If hardware, precision, resolution, sequence length, duration, sampling steps, or software stacks differ, label the table as descriptive rather than ranking the models.

For Elo results, report rank, score, 95% confidence interval, sample count, category, and observation date when available. Explain overlapping confidence intervals instead of declaring a significant winner from a small score difference.

### Architecture and training

Connect every important architecture detail to its purpose and cost. Explain why the design matters for capability, training, memory, latency, or extensibility. Do not list layer counts without interpretation.

Separate disclosed training facts from plausible attribution. When data mixtures, losses, reward design, ablations, or implementation details are unavailable, say that the contribution cannot be isolated.

### Terminology

At first use, explain important terms through four parts when useful:

1. Full name
2. Literal meaning
3. Position in the pipeline
4. Plain-language explanation

Add a short glossary for terms that a presenter may need to pronounce or explain. Do not turn the glossary into a general encyclopedia.

## Report Structure

Use descriptive Markdown headings without numeric prefixes. A typical report contains:

- Conclusion
- Model basics
- Open boundary, when relevant
- Specifications, capabilities, and actual limits
- Quality and inference evidence, when available
- Mechanism-derived selling points or product capabilities
- Architecture and training
- Final judgment
- Sources
- Glossary

Do not add “适合谁、不适合谁” or “研发团队落地路线” by default. Add any nonstandard section only when the model itself makes it necessary.

## Writing Style

- Write natural technical Chinese for peers. Lead with the conclusion and then support it.
- Never add chapter numbers such as `一、`, `第一章`, `卖点一`, or `1.` to headings. Use Markdown hierarchy alone.
- Use direct, descriptive titles. Avoid empty titles such as “进一步分析” or “相关讨论”.
- Do not force exactly three selling points. Name each point by its mechanism or value.
- Prefer “是什么、怎么实现、有什么代价” over promotional praise.
- Use tables for exact mappings and comparisons. Use Mermaid only when a flow, hierarchy, or multi-component relationship is easier to understand visually.
- Keep checkpoint codes, tensor shapes, and implementation notes outside conceptual diagrams unless they are essential to the relationship.
- Use analogies sparingly and follow them with the precise technical definition.
- Avoid bureaucratic or synthetic-sounding wording when a plain term works. Rewrite words such as `门禁`, `台账`, `抓手`, `闭环`, `卡点`, `赋能`, `拉通`, `沉淀`, `颗粒度`, `组合拳`, `打法`, `生态位`, and `摸底` into concrete technical language.
- Avoid filler such as “值得注意的是”, “需要指出的是”, “具有重要意义”, and “提供有力支撑”. State the fact or judgment directly.
- Use terms such as `对齐`, `底座`, or `全链路` only when they are established technical terms in the specific context; otherwise choose a precise alternative.

## Final Check

Before delivery:

1. Recheck all headings and remove numeric prefixes.
2. Search for synthetic management language and rewrite it naturally.
3. Audit `首个`, `最强`, `领先`, `原生`, `开源`, `开放`, `无损`, and `最低硬件`; add a source and scope or weaken the wording.
4. Confirm that product capabilities are not attributed to the released local model.
5. Confirm that benchmark rows are genuinely comparable and that missing scores remain missing.
6. Confirm that dynamic facts include a date and were checked at the end of the task.
7. Confirm that the conclusion states both the model's main value and its main limitation.
8. Confirm that every source link supports the nearby claim and that the source list distinguishes primary and third-party evidence.
