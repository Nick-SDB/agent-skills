---
name: codex-task-routing
description: Split a multi-part task and route subtasks by their nature — delegate coding-heavy / implementation / kernel / GPU / benchmark work to a one-shot codex subagent via the `subagent_codex` tool, keep documentation / timeliness / big-picture aggregation on the main contextful agent, and enforce a review gate before any subagent commits to a technically risky route. Use when splitting tasks, deciding who (codex vs main agent vs context-inheriting subagent) should do each part, or when a subagent must not drift down a wrong technical path.
---

# Codex Task Routing

按任务的**性质**拆分并路由到正确的执行者：重编码类工作通过 **`subagent_codex` 工具**提交给 codex 子代理（**禁止**用裸 `codex exec` 命令行），文档/时效性/大局观由主代理持有，并让任何子代理在走错技术路线之前被评审闸门拦住。

## 何时使用

- 一个任务混合了编码/实现/GPU 工作与文档、规划、汇报。
- 需要决定谁来做：codex 子代理 vs 主代理 vs 继承上下文的子代理。
- 曾发生过「子代理做了不该做的重活」或「子代理擅自锁定了错误技术路线」，需要预防复发。

## 核心原则（唯一的路由规则）

| 子任务性质 | 特征 | 执行者 | 工具 |
|---|---|---|---|
| **编码重活** | kernel / CUDA / 实现 / benchmark / GPU 执行 / 代码改动 | **codex 子代理**（一次性、自包含） | `subagent_codex` |
| **文档 / 时效性 / 大局观** | 总结、汇报、规划、跨轮一致性、整体判断 | **主代理**（持有完整上下文） | 直接写 |
| **继承上下文的有限分析** | 需要既有结论，但无重代码 | 上下文继承子代理 | `subagent_fork` |

关键区分：codex 是**一次性**（每次调用拿到全新上下文），所以它不擅长时效性与大局观——每次都要重新喂入全部上下文，且会偏离既有结论。主代理持有完整会话记忆，因此负责一切必须保持最新、全局一致的部分。

## 工具使用（唯一合法的 codex 调用通道）

- 与 codex 子代理交互**只允许**用 **`subagent_codex` 工具**，把重编码活当作一个自包含、一次性的子代理任务提交。
- **禁止**直接跑裸 `codex exec`（或 `codex e`）命令行来顶替子代理。原因：在 DSH 环境下裸 `codex exec` 走的是宿主 shell 沙箱，常因 codex 需要写 `~/.codex/tmp/arg0/` 等目录而触发 `Permission denied (os error 13)`，或需要逐条手动传递代理/认证环境；而 `subagent_codex` 由 DSH 正确管理 app-server 协议、权限上下文与代理路由，是稳定唯一可用的通道。
- 涉及 CLI 特有的查询（如配额 `check-codex-quota`）同样不要用 `codex exec` 子代理去跑；应由主代理在宿主 shell 直接执行官方 API 查询。

## 第 1 步 — 拆分任务

问三个问题，给每个部分打标签：

1. 任何部分涉及**编码 / 实现 / 跑 GPU**？→ 标 `codex`。
2. 任何部分涉及**写文档 / 总结 / 规划**，且必须反映最新状态、保持全局一致？→ 标 `main`。
3. 任何部分**需要既有上下文但无重代码**？→ 标 `fork`。

## 第 2 步 — 路由

- `codex` 部分 → `subagent_codex`，附上**完整自包含的 prompt**（codex 看不到本对话的任何内容）。
- `main` 部分 → 主代理直接写（持有完整上下文）。
- `fork` 部分 → `subagent_fork`（继承上下文），但**绝不交给它编码重活**。

## 第 3 步 — 评审闸门

子代理在**锁定技术上有风险**的改动之前，必须先提交简短方案，由主代理批准后方可继续。

- **硬闸（始终强制）**：高风险改动——kernel 数值契约、寄存器/内存布局、算法路线、测量方法，或任何「走错路线就浪费整轮」的改动。
- **软闸（可选）**：低风险、有界的改动。

这道闸门的作用，是在**方案阶段**就拦下即将走错路线的子代理（例如「把累加器改成不存在的那条路径」），而不是等它建完、测完才发现。

## 第 4 步 — 主代理汇总

主代理持有最终总结，跨轮保持一致，并把结论落盘到持久化文档。子代理的输出只是汇总的输入，永远不是最终结论。

## 反模式（避免这些）

| 反模式 | 后果 | 修正 |
|---|---|---|
| 用裸 `codex exec` 命令行顶替子代理 | 沙箱权限报错、环境不完整、偏离统一调用通道 | 统一走 `subagent_codex` 工具 |
| 把重活交给 fork/普通子代理 | 能力不匹配、路线错误 | 重活只给 codex |
| 让 codex 写必须保持最新/全局一致的文档 | 偏离既有结论 | 文档/总结 → 主代理 |
| 主代理手写重代码 | 消耗主线程、丢失大局观 | 主代理只规划/监督/汇总 |
| 子代理未经评审就锁定高风险改动 | 路线错误、浪费整轮 | 强制评审闸门 |

## 泛化说明

- 路由规则（编码 → codex，文档/时效性/大局观 → 主代理）与模型无关：只要「一次性执行者（codex）」与「上下文规划者（主代理）」并存就成立。
- 评审闸门随风险缩放：高风险技术改动硬闸，机械改动不设闸。
- 执行者能力变化时重新评估路由（例如 codex 子代理获得 GPU 访问权后，「重活」的边界随之改变）。
