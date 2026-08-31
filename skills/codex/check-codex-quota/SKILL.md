---
name: check-codex-quota
description: 查询 Codex 账号当前剩余的每周使用额度（weekly usage quota / limit）。通过官方 wham/usage API 读取已存储的认证 token 与账号 id，返回套餐、周窗口已用/剩余百分比与重置时间。Use when the user asks about codex 额度、配额、用量、剩余额度、周额度、quota、usage、limit，或想知道本周 Codex 还能用多少。
---

# Check Codex Weekly Quota

## 背景

Codex（ChatGPT 认证的 Pro 等套餐）在服务端按**周窗口（7 天 / 10080 分钟）**限额。额度信息不在本地，必须查询 ChatGPT 官方接口 `https://chatgpt.com/backend-api/wham/usage`。认证信息（access_token + account_id）存储在 `~/.codex/auth.json`。

## 完整查询命令（直接可用）

运行本 skill 自带的固定脚本 `scripts/check_codex_quota.py` 即可（读取 `~/.codex/auth.json`、带正确请求头调用 wham/usage、打印可读结果）：

```bash
python3 scripts/check_codex_quota.py
```

在**宿主 shell** 中执行（不要在 codex exec 沙箱里跑，其网络受限）。**保持当前环境的 HTTP(S)_PROXY 代理变量不变**：某些网络下直连 chatgpt.com 会超时（如 IPv6 被墙），走代理才可达；脚本会自动继承当前环境、不主动清除代理变量。

## 字段含义

| 字段 | 含义 |
| --- | --- |
| `plan_type` | 套餐（pro / plus / team ...） |
| `rate_limit.primary_window.used_percent` | **周窗口（10080 分钟 = 7 天）已用百分比**，剩余 = 100 - 该值 |
| `rate_limit.primary_window.reset_at` / `reset_after_seconds` | 窗口重置时间 / 距重置秒数 |
| `rate_limit.secondary_window` | 次级窗口（通常为 0 或不适用） |
| `credits` | 额外额度（has_credits / balance / unlimited），一般无 |

## 常见坑（实测经验）

1. **不要直连 chatgpt.com**：部分网络下直连会解析到 IPv6 导致连接超时；必须走代理（保留环境变量 `HTTPS_PROXY` / `HTTP_PROXY` 即可）。
2. **必须带 `ChatGPT-Account-Id` 头**：裸 curl 只有 `Authorization` 会 403（HTML 错误页），加上账号头 + `User-Agent: codex-cli/...` 才能 200。
3. **不要在 codex exec 沙箱里跑这个查询**：codex 沙箱网络受限（`codex doctor` 显示 network sandbox: restricted），其内部 curl 会 "Couldn't connect to server"。直接在宿主 shell 执行。
4. **token 过期**：auth.json 的 access_token 长期不刷新会失效（401/403）。此时先用 refresh_token 走 `POST https://chatgpt.com/backend-api/session`（body `{"refresh_token": ...}`）刷新，或让用户重新 `codex login`。

## 故障排查与兜底

- 若 `wham/usage` 非 200：优先检查（a）是否在沙箱内、（b）请求头是否完整、（c）token 是否过期。
- 兜底一：先重跑固定脚本 `python3 scripts/check_codex_quota.py`（可能只是瞬时失败）。**不要用 `codex exec` 顶替**——codex 沙箱网络受限，且其内部 curl 会 "Couldn't connect to server"。
- 兜底二：直接从本地日志读取最后一次已知用量（也是历史数据）：
  `strings ~/.codex/logs_2.sqlite | rg 'x-codex-primary-used-percent' | tail -n 1`，看响应头里的 `x-codex-primary-used-percent` / `x-codex-primary-reset-at` 等字段。
- 注意区分**实时值**（wham/usage 接口）与**历史值**（本地日志/响应头），汇报时说明数据时间。

## 验证

跑通后应输出类似：
```
Codex 周额度汇报
  套餐        : pro
  周窗口已用  : 24%
  周窗口剩余  : 76%
  下次重置    : 2026-09-01 22:15 +08 (约 6.2 天后)
```
