---
name: codex-route
description: User-explicit manual switch that routes the whole current task to codex. Load it ONLY when the user explicitly names this skill (for example "/codex-route") or explicitly says the task must be handed to codex in this session — never auto-load it because a task merely looks like coding, analysis, or evaluation work, and never load it on the agent's own initiative. Once triggered, assemble one self-contained prompt and run the task through codex; if codex fails, stop that subtask and report to the user instead of doing the work yourself. Use when the user wants to force codex execution for a specific task.
---

# Codex Route

**仅手动触发**：本 skill 只能由用户**显式点名**加载。agent 不得因为任务看起来像编码、分析、评估而自行加载它；觉得合适时只能**建议**用户触发，不得代替用户触发。

## 触发判定（加载后第一件事）

在最近一条用户消息中寻找**显式点名**，只有这两种算数：

1. 直接写出本 skill 的名字（`codex-route` / `/codex-route`）；或
2. 明确要求把当前任务交给 codex 执行（例如「这个任务用 codex 跑」「交给 codex 做」）。

找不到显式点名 → **立即停止**：说明本 skill 需要用户显式触发，不要执行任何路由，也不要按本 skill 的后续步骤行事。

触发一次即对**当前任务**持续有效：本次任务的后续步骤继续按本 skill 路由，直到用户改口。

## 触发后做什么

1. **组装一个自包含 prompt**：目标、输入与位置、约束、验收标准、回报格式。任务需要的全部上下文都要写进 prompt——codex 看不到本对话，也看不到本 skill。
2. **用 `codex exec` 提交执行**：这是本 skill 唯一的执行通道。
3. **整体交给 codex**：分析、评估、代码改动等任务主体全部由 codex 产出；主代理只保留拆解、按序下发、审阅交付与向用户汇报，**不亲自代跑任务本身**。
4. **长程任务先拆清单**：多步骤或跨多轮的任务，先拆成有依赖顺序的步骤清单并逐项标状态，再按序下发，而不是一次性全量甩给 codex。
5. **高风险路线先过闸**：涉及关键数值契约、寄存器 / 内存布局、算法路线、测量方法的改动，先让 codex 只输出方案、不落盘，经主代理批准后再下发实施阶段。
6. **失败即终止**：`codex exec` 报错时，终止该子任务，向用户汇报错误原文与已得到的中间结果，**不做 fallback**——不换执行者、不换调用通道、不由主代理代跑。环境故障必须暴露，不能被掩盖成一次看似成功的交付。

## 与自动路由的关系

- 默认路由规则由 `codex-task-routing` 描述：按任务性质自动决定谁来做。
- 本 skill 是**用户手里的强制开关**：显式触发后，当前任务整体走 codex，不再逐条判断哪些部分「更像文档工作」而留给主代理。
- 用户未触发时，一切按 `codex-task-routing` 的默认规则走，不要用本 skill 的判定去覆盖它。

## 反模式（避免这些）

| 反模式 | 后果 | 修正 |
|---|---|---|
| agent 自行判断「这活像重活」就加载本 skill | 用户的手动开关失效 | 只有用户显式点名才加载，否则最多建议 |
| 用户点名后主代理仍自己写分析或代码 | 违背用户意图 | 任务主体整体交 codex |
| `codex exec` 报错后由主代理代跑或换通道 | 掩盖环境故障、结论不可信 | 终止该子任务并如实汇报 |
| 只甩一句「做这个」给 codex | 一次性执行者无法补全上下文 | prompt 必须自包含 |
| 触发判定失败后仍「顺手」按本 skill 执行 | 越权触发 | 停下并说明需要用户显式触发 |
