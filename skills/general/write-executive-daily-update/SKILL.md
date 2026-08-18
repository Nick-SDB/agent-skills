---
name: write-executive-daily-update
description: Convert technical work logs, experiment progress, engineering notes, or raw status updates into a concise leadership-ready daily report. Use when the user asks for a 日报、今日进展、领导汇报、管理层摘要、executive update, or wants technical progress rewritten as plain-language unordered bullets with conclusions.
---

# Write Executive Daily Update

## Workflow

1. Extract only material work completed or meaningfully advanced today.
2. Pair each work item with its result, conclusion, impact, or verified limitation.
3. Remove routine housekeeping unless it affected delivery, risk, cost, or a decision.
4. Translate internal codes and implementation terms into plain business-readable language.
5. Detect repeated comparisons across alternatives, versions, time points, or metrics and put them
   in a compact Markdown table.
6. Order remaining bullets by importance: completed outcomes, comparative findings, failures or
   risks, then enabling work.
7. Return an unordered list by default. Add a heading, date, next steps, or document edit only
   when requested.

## Writing Rules

- Write one compact sentence per bullet when practical.
- Combine action and conclusion naturally with punctuation; do not prefix text with
  “工作内容：” or “结论：”.
- Preserve concrete product names, counts, durations, pass/fail results, and other decision-useful
  evidence.
- Prefer a Markdown table when comparing two or more items across repeated dimensions such as
  parameters, samples, latency, quality, progress, or pass/fail status.
- Keep one comparable item per table row, use consistent units and metric direction, and reserve
  surrounding bullets for the decision or conclusion that the table supports.
- Keep a comparison in prose only when it is a single fact that fits clearly in one sentence.
- Say explicitly when a run produced no valid result; never present partial progress as completion.
- Prefer 3–7 high-value bullets. Merge related implementation details into the outcome they enable.
- Use direct, neutral language suitable for a leader who has not followed the implementation.
- Do not mention paths, driver names, checkpoint IDs, process IDs, internal commands, or tool names
  unless they are themselves the finding.
- Exclude report formatting work, file locations, routine cleanup, available disk space, and similar
  operational trivia unless they caused or removed a material blocker.
- Do not invent business impact or certainty beyond the supplied evidence.

## Output Format

- Render the report as ordinary Markdown by default. Do not add a code fence when the user wants
  normal rendered output.
- When the user wants paste-ready Markdown source that stays unrendered in chat but renders after
  copying into a `.md` file, wrap the complete report in one fenced code block with `text` as the
  language label. Tell the user to copy only the content inside the fence.
- Keep the report title as plain text without a Markdown heading marker when requested.
- Preserve standard Markdown pipe-table syntax inside the fence.
- Avoid unnecessary blank lines. Add exactly one blank line after each table before any subsequent
  content so the copied Markdown parses correctly.

## Translate Internal Language

Replace internal shorthand with a short descriptive name on first use:

- `L2` → “跨团队需求变更测试”
- `L4` → “故障恢复测试”
- `L5` → “长时间连续运行测试”
- `L6` → “安全隔离测试”
- `H48` → “48 Agent 高负载测试”
- `H128` → “128 Agent 极限压力测试”
- `checkpoint` → “关键步骤” or the actual completed action
- “原生通信验证” → “产品能否把变更自动传达给原责任角色”

Keep a code only when the audience already uses it or the user explicitly requests it.

## Quality Check

Before answering, verify:

- Every bullet states both what changed and what it means.
- A leader can understand every bullet without experiment documentation.
- The list contains no item whose removal would leave management understanding unchanged.
- Failures identify the observed limitation without speculative root-cause claims.

## Example

Prefer:

- 完成 Houmao 第二轮跨团队需求变更测试；后端修改、前端同步、追加需求和最终验收
  均在 485 秒内完成，两轮测试全部通过。

Avoid:

- 工作内容：完成 Houmao L2 run2；结论：4/4 checkpoint PASS。
- 检查磁盘，当前还有 4.5 TB。
