# Evidence and Benchmark Rules

## Source priority

Use the strongest available source for each claim:

1. Paper or technical report
2. Official model card, repository code, configuration, or weights
3. Official license and product or API documentation
4. Official release blog
5. Official inference framework integration or benchmark
6. Independent benchmark or leaderboard
7. Reproducible community measurement
8. Informal discussion

Do not use a lower-priority source to override a more direct primary source without explaining the conflict.

## Evidence labels

Classify important statements internally as:

- **Verified fact**: directly supported by released artifacts or primary documentation
- **Official claim**: stated by the developer but not independently reproduced
- **Third-party result**: measured by an independent evaluator
- **Inference**: reasoned from disclosed facts; state the reasoning and uncertainty
- **Unknown**: evidence is absent or contradictory

Preserve these distinctions in the report wording.

## Open-release audit

Check separately:

- Weights
- Inference code
- Training code
- Tokenizer, processor, chat template, and configuration
- Encoders, decoders, VAE, vocoder, scheduler, or router
- Prompt rewriting, intermediate representation, safety, post-processing, and super-resolution stages
- License territory, commercial conditions, redistribution, attribution, and use restrictions

Repository download size is not the same as resident model size. A headline parameter count may cover only the backbone rather than the complete serving pipeline.

## Benchmark comparability

For quality results, record:

- Benchmark name and version
- Task and modality
- Prompt set or sample count
- Model mode, reasoning effort, tools, or generation settings
- Score direction and uncertainty
- Source and observation date

For inference results, record:

- Hardware model and GPU count
- Precision and quantization
- Parallelism and offloading
- Batch size and concurrency
- Input and output length, resolution, frames, duration, or sampling steps
- Warmup and whether latency is end-to-end or a model stage
- Peak memory and throughput definition
- Runtime and relevant optimization flags

Do not rank models across incompatible conditions. Normalize only when the metric scales linearly and the assumption is defensible; video generation and long-context attention often do not.

## Quality versus performance

Keep these conclusions distinct:

- Arena Elo measures relative human preference within a category.
- A confidence interval measures uncertainty; overlapping intervals weaken claims about ordering.
- SSIM or PSNR against a same-seed baseline measures trajectory deviation, not absolute perceptual quality.
- Faster inference does not imply better price-performance unless quality and output settings are held constant.
- Lower API price is not local inference speed.
- Quantization memory savings may be much larger than latency savings.

## Hardware wording

Distinguish:

- **Theoretical minimum**: can load with aggressive offloading or quantization
- **Practical minimum**: completes representative workloads with usable latency
- **Officially validated configuration**: supported by published measurements

Do not convert an unverified community success into an official minimum requirement.

## Dynamic data

Leaderboards, prices, model availability, documentation, and repository contents may change during report preparation. Check them once during research and again immediately before delivery. State the observation date and avoid wording that implies permanence.

## Claim audit

Require explicit scope for:

- 首个
- 最强
- 领先
- 原生
- 开源
- 开放权重
- 无损
- 最低硬件
- 商用级

Replace an unsupported superlative with the narrowest verified statement.
